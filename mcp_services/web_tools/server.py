from mcp.server.fastmcp import FastMCP
import httpx
from bs4 import BeautifulSoup
import traceback
from playwright.async_api import async_playwright
import asyncio

# Initialize FastMCP server
mcp = FastMCP("Web Tools")

@mcp.tool()
async def fetch_headless_content(url: str, wait_for_selector: str = None) -> str:
    """
    Fetches the text content of a webpage using a headless browser (Playwright).
    Handles dynamic JS content and tries to bypass basic bot detection.
    
    Args:
        url: The URL to fetch.
        wait_for_selector: Optional CSS selector to wait for before extracting text.
        
    Returns:
        The text content of the webpage, or an error message.
    """
    try:
        async with async_playwright() as p:
            # Launch browser with arguments to mimic real user
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Create context with custom user agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            # Add init script to mask webdriver
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Go to URL with timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Initial wait for hydration/rendering
            await asyncio.sleep(3)

            # Auto-scroll to load more content
            # Scroll down multiple times with longer pauses
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2) # Give it time to load more items

            # Wait for specific selector if provided, otherwise wait a bit for hydration
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                except:
                    pass # Continue if selector not found
            else:
                # Generic wait for dynamic content
                # Relaxed wait condition to avoid timeout on stubborn assets
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await asyncio.sleep(3) # Give it a moment for JS to render
                except:
                    pass # Proceed even if timeout occurs
            
            # Extract content
            content = await page.content()
            
            # Use BeautifulSoup to clean up text
            soup = BeautifulSoup(content, 'html.parser')
            for script in soup(["script", "style", "noscript", "iframe"]):
                script.decompose()
                
            text = soup.get_text()
            
            # Format text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            await browser.close()
            return text
            
    except Exception as e:
        return f"Error fetching URL with headless browser: {str(e)}\n{traceback.format_exc()}"

@mcp.tool()
async def fetch_url_content(url: str) -> str:
    """
    Fetches the text content of a webpage.
    
    Args:
        url: The URL to fetch.
        
    Returns:
        The text content of the webpage, or an error message.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, headers=headers) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # Use BeautifulSoup to extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
    except Exception as e:
        return f"Error fetching URL: {str(e)}\n{traceback.format_exc()}"

@mcp.tool()
async def fetch_url_html(url: str) -> str:
    """
    Fetches the raw HTML content of a webpage.
    
    Args:
        url: The URL to fetch.
        
    Returns:
        The HTML content of the webpage, or an error message.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, headers=headers) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

if __name__ == "__main__":
    # Run via stdio by default when executed
    mcp.run(transport='stdio')
