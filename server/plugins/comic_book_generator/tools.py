from typing import Optional, Dict, List, Tuple
import os
import base64
import uuid
import httpx
import asyncio
from pathlib import Path
from loguru import logger
from langchain_core.tools import tool
from server.core.llm import get_active_model_config
from server.kernel.mcp_manager import mcp_manager
from .schema import ComicBook, ComicPage

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    logger.error("Pillow library not found. Please install it: pip install Pillow")
    Image = None
    ImageDraw = None
    ImageFont = None

@tool
async def generate_image_base64(prompt: str) -> Optional[str]:
    """
    根据提示词生成图片，返回 Base64 字符串。
    使用系统配置的文生图模型 (TEXT_TO_IMAGE_MODEL_ID)。
    支持 OpenAI 兼容接口和阿里云 DashScope 原生接口。
    """
    try:
        # 1. 获取模型配置
        model_config = get_active_model_config("TEXT_TO_IMAGE_MODEL_ID")
        
        if not model_config:
            logger.error("No active image generation model configured (TEXT_TO_IMAGE_MODEL_ID). Cannot generate image.")
            raise ValueError("No active image generation model configured. Please configure TEXT_TO_IMAGE_MODEL_ID in settings.")

        logger.info(f"Generating image with model: {model_config.name} (model_name={model_config.model_name}, base_url={model_config.base_url})")

        api_key = model_config.api_key or "sk-dummy"
        base_url = model_config.base_url.rstrip("/") if model_config.base_url else "https://api.openai.com/v1"

        # === 2. DashScope Native Logic ===
        is_dashscope_native = "dashscope.aliyuncs.com" in base_url and "compatible-mode" not in base_url
        
        if is_dashscope_native:
            return await _generate_dashscope_native(api_key, base_url, model_config.model_name, prompt)

        # === 3. OpenAI Compatible Logic ===
        if base_url.endswith("/generation") or base_url.endswith("/generations"):
             url = base_url
        else:
             if not base_url.endswith("/v1"):
                 if "/v1" not in base_url:
                     base_url += "/v1"
             url = f"{base_url}/images/generations"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_config.model_name,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"OpenAI Image Gen failed: {response.status_code} - {response.text}")
                try:
                    err_msg = response.json().get("error", {}).get("message", response.text)
                except:
                    err_msg = response.text
                raise RuntimeError(f"Image generation API failed: {err_msg}")
            
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                b64_str = data["data"][0].get("b64_json")
                if b64_str:
                    logger.info("Image generated successfully (OpenAI Mode).")
                    return b64_str
            
            logger.error(f"Unexpected response format: {data}")
            raise RuntimeError("Unexpected response format from image generation API")

    except Exception as e:
        logger.error(f"Error during image generation: {e}")
        raise e

async def _generate_dashscope_native(api_key: str, base_url: str, model_name: str, prompt: str) -> Optional[str]:
    """
    处理阿里云 DashScope 原生异步调用逻辑
    """
    logger.info("Using DashScope Native Mode")
    
    if base_url.endswith("/generation"):
        url = base_url
    else:
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        if "multimodal-generation" in base_url:
             if not base_url.endswith("/generation"):
                  url = f"{base_url}/generation"
             else:
                  url = base_url
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable"
    }
    
    payload = {
        "model": model_name if model_name.startswith("wanx") else "wanx-v1", 
        "input": {
            "prompt": prompt
        },
        "parameters": {
            "style": "<auto>",
            "size": "1024*1024",
            "n": 1
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        
        if resp.status_code in [400, 404]:
             logger.warning(f"DashScope submit failed with URL {url} (Status: {resp.status_code}). Trying standard endpoint.")
             url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
             resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(f"DashScope submit failed: {resp.status_code} - {resp.text}")
            raise RuntimeError(f"DashScope submit failed: {resp.text}")
        
        task_data = resp.json()
        task_id = task_data.get("output", {}).get("task_id")
        if not task_id:
            logger.error(f"No task_id in DashScope response: {task_data}")
            raise RuntimeError("No task_id in DashScope response")
            
        logger.info(f"DashScope task submitted: {task_id}")
        
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for _ in range(30):
            await asyncio.sleep(2)
            task_resp = await client.get(task_url, headers={"Authorization": f"Bearer {api_key}"})
            
            if task_resp.status_code != 200:
                logger.error(f"DashScope poll failed: {task_resp.status_code}")
                continue
                
            task_res = task_resp.json()
            status = task_res.get("output", {}).get("task_status")
            
            if status == "SUCCEEDED":
                results = task_res.get("output", {}).get("results", [])
                if results and "url" in results[0]:
                    img_url = results[0]["url"]
                    logger.info(f"Downloading image from {img_url}")
                    img_resp = await client.get(img_url)
                    if img_resp.status_code == 200:
                        b64_str = base64.b64encode(img_resp.content).decode("utf-8")
                        logger.info("Image downloaded and converted to base64")
                        return b64_str
                logger.error("No image URL in succeeded task")
                raise RuntimeError("No image URL in succeeded task")
                
            elif status in ["FAILED", "CANCELED"]:
                logger.error(f"DashScope task failed: {task_res}")
                raise RuntimeError(f"DashScope task failed: {task_res}")
                
        logger.error("DashScope task timed out")
        raise RuntimeError("DashScope task timed out")

def save_local_image(base64_str: str, user_id: str, suffix: str = "") -> str:
    """
    Save base64 image to local disk and return absolute path.
    """
    safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
    directory = Path.cwd() / "server" / "data" / "user_files" / safe_user_id / "images"
    directory.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    filename = f"img_{file_id}{suffix}.png"
    file_path = directory / filename
    
    # Clean Base64 string if it contains data URI scheme
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    
    try:
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_str))
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        raise RuntimeError(f"Failed to save image to {file_path}: {e}")
        
    return str(file_path.resolve())

def _get_font(size: int):
    """
    Try to load a Chinese font.
    """
    font_names = [
        "msyh.ttc", # Microsoft YaHei (Windows)
        "simhei.ttf", # SimHei (Windows)
        "Arial Unicode.ttf",
        "PingFang.ttc", # Mac
        "NotoSansCJK-Regular.ttc", # Linux
    ]
    
    # Try system paths
    system_font_dirs = [
        "C:/Windows/Fonts",
        "/usr/share/fonts",
        "/System/Library/Fonts",
        os.path.expanduser("~/Library/Fonts")
    ]
    
    for name in font_names:
        # 1. Try direct loading (if in path)
        try:
            return ImageFont.truetype(name, size)
        except:
            pass
            
        # 2. Try system paths
        for d in system_font_dirs:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
    
    # Fallback to default
    logger.warning("No Chinese font found, using default.")
    return ImageFont.load_default()

def compose_comic_page(page: ComicPage, panel_images: Dict[int, str], user_id: str) -> str:
    """
    Compose a single comic page with 4 panels (2x2 grid) using Pillow.
    Returns the path to the saved page image.
    """
    if not Image:
        raise RuntimeError("Pillow is not installed.")

    # A4 size at 150 DPI (approx) -> 1240 x 1754
    PAGE_WIDTH = 1240
    PAGE_HEIGHT = 1754
    MARGIN = 60
    HEADER_HEIGHT = 200
    
    # Create canvas (White background)
    canvas = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)
    
    # Fonts
    title_font = _get_font(60)
    desc_font = _get_font(30)
    text_font = _get_font(24)
    
    # 1. Draw Header
    # Title centered
    draw.text((PAGE_WIDTH//2, MARGIN), f"Page {page.page_number}: {page.title}", font=title_font, fill="black", anchor="mt")
    
    # Description below title
    if page.description:
        # Simple wrap for description
        desc_lines = _wrap_text(page.description, desc_font, PAGE_WIDTH - 2*MARGIN)
        y_text = MARGIN + 80
        for line in desc_lines:
            draw.text((PAGE_WIDTH//2, y_text), line, font=desc_font, fill="#333333", anchor="mt")
            y_text += 40
            
    # 2. Draw 2x2 Grid
    # Calculate grid area
    grid_top = HEADER_HEIGHT + MARGIN
    grid_bottom = PAGE_HEIGHT - MARGIN
    grid_width = PAGE_WIDTH - 2*MARGIN
    grid_height = grid_bottom - grid_top
    
    cell_width = (grid_width - MARGIN) // 2
    cell_height = (grid_height - MARGIN) // 2
    
    # Coordinates for 4 panels
    # (x, y) top-left corners
    positions = [
        (MARGIN, grid_top),
        (MARGIN + cell_width + MARGIN, grid_top),
        (MARGIN, grid_top + cell_height + MARGIN),
        (MARGIN + cell_width + MARGIN, grid_top + cell_height + MARGIN)
    ]
    
    for i, panel in enumerate(page.panels):
        if i >= 4: break # Only support 4 panels for now
        
        x, y = positions[i]
        
        # Draw Panel Border
        draw.rectangle([x, y, x + cell_width, y + cell_height], outline="black", width=3)
        
        # Load Panel Image
        img_path = panel_images.get(panel.panel_number)
        if img_path and os.path.exists(img_path):
            try:
                p_img = Image.open(img_path)
                # Resize image to fit top part of the cell (leaving space for text)
                # Let's say image takes 70% height
                img_h_target = int(cell_height * 0.75)
                img_w_target = int(cell_width - 6) # minimal padding
                
                # Resize keeping aspect ratio, crop if needed
                p_img = _resize_and_crop(p_img, img_w_target, img_h_target)
                
                canvas.paste(p_img, (x + 3, y + 3))
            except Exception as e:
                logger.error(f"Failed to load image {img_path}: {e}")
                draw.text((x + 20, y + 20), "Image Error", fill="red", font=text_font)
        else:
            draw.text((x + 20, y + 20), "Image Generation Failed", fill="red", font=text_font)
            
        # Draw Dialogue/Text Box at bottom of cell
        text_area_y = y + int(cell_height * 0.75) + 5
        text_area_h = cell_height - int(cell_height * 0.75) - 5
        
        # Draw Text
        # Wrap text
        lines = _wrap_text(panel.dialogue, text_font, cell_width - 20)
        ty = text_area_y + 10
        for line in lines:
            if ty > y + cell_height - 10: break
            draw.text((x + 10, ty), line, font=text_font, fill="black")
            ty += 30
            
        # Draw Panel Number Badge
        draw.ellipse([x-15, y-15, x+25, y+25], fill="#2563eb", outline="white", width=2)
        draw.text((x+5, y+5), str(panel.panel_number), font=desc_font, fill="white", anchor="mm")

    # Save Page
    safe_user_id = "".join(ch for ch in (user_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
    comic_dir = Path.cwd() / "server" / "data" / "user_files" / safe_user_id / "comics"
    comic_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    filename = f"comic_page_{page.page_number}_{file_id}.png"
    file_path = comic_dir / filename
    
    canvas.save(file_path)
    return str(file_path.resolve())

def _resize_and_crop(img, target_width, target_height):
    """
    Resize image to fill target size, cropping excess.
    """
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        # Image is wider -> scale by height
        new_height = target_height
        new_width = int(new_height * img_ratio)
    else:
        # Image is taller -> scale by width
        new_width = target_width
        new_height = int(new_width / img_ratio)
        
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Center Crop
    left = (new_width - target_width) / 2
    top = (new_height - target_height) / 2
    right = (new_width + target_width) / 2
    bottom = (new_height + target_height) / 2
    
    return img.crop((left, top, right, bottom))

def _wrap_text(text, font, max_width):
    """
    Simple text wrapping.
    """
    lines = []
    if not text: return lines
    
    # Very basic character based wrapping for Chinese support
    # (Pillow's textlength is accurate)
    current_line = ""
    for char in text:
        if char == '\n':
            lines.append(current_line)
            current_line = ""
            continue
            
        test_line = current_line + char
        # Check width
        if font.getlength(test_line) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
            
    if current_line:
        lines.append(current_line)
        
    return lines

def create_pdf_from_images(image_paths: List[str], output_path: str) -> str:
    """
    Combine multiple images into a single PDF file using Pillow.
    """
    if not image_paths:
        raise ValueError("No images provided for PDF creation")
        
    try:
        # Open first image
        img1 = Image.open(image_paths[0])
        img1 = img1.convert("RGB")
        
        other_images = []
        for p in image_paths[1:]:
            img = Image.open(p)
            img = img.convert("RGB")
            other_images.append(img)
            
        img1.save(output_path, save_all=True, append_images=other_images)
        logger.info(f"PDF created successfully at: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create PDF from images: {e}")
        raise e
