import os
import sys

# 确保可以导入同级目录的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback for when mcp is not installed or FastMCP is not available
    # This allows the script to fail gracefully or prompt for installation
    sys.stderr.write("Error: 'mcp' library not found. Please install it using: pip install mcp\n")
    sys.exit(1)

from md_to_docx import create_docx_from_md
from docx_to_pdf import convert_docx_to_pdf
from create_ppt import create_ppt_from_md_file

# 初始化 MCP Server
mcp = FastMCP("mdtofiles")

@mcp.tool()
def md_to_ppt_tool(md_path: str, ppt_path: str) -> str:
    """
    将 Markdown 文件转换为 PPTX 文件。
    Markdown 规则：
    # 标题 -> 封面页 (标题 - 副标题)
    ## 标题 -> 内容页标题
    - 列表 -> 内容页正文
    
    Args:
        md_path: 源 Markdown 文件的绝对路径。
        ppt_path: 目标 PPTX 文件的保存路径。
    """
    try:
        success, msg = create_ppt_from_md_file(md_path, ppt_path)
        if success:
            return f"成功: {msg}"
        else:
            return f"失败: {msg}"
    except Exception as e:
        sys.stderr.write(f"执行出错: {str(e)}\n")
        return f"执行出错: {str(e)}"

@mcp.tool()
def md_to_docx_tool(md_path: str, docx_path: str) -> str:
    """
    将 Markdown 文件转换为 DOCX 文件。
    
    Args:
        md_path: 源 Markdown 文件的绝对路径。
        docx_path: 目标 DOCX 文件的保存路径。
    """
    try:
        success, msg = create_docx_from_md(md_path, docx_path)
        if success:
            return f"成功: {msg}"
        else:
            return f"失败: {msg}"
    except Exception as e:
        return f"执行出错: {str(e)}"

@mcp.tool()
def docx_to_pdf_tool(docx_path: str, pdf_path: str) -> str:
    """
    将 DOCX 文件转换为 PDF 文件。
    
    Args:
        docx_path: 源 DOCX 文件的绝对路径。
        pdf_path: 目标 PDF 文件的保存路径。
    """
    try:
        success, msg = convert_docx_to_pdf(docx_path, pdf_path)
        if success:
            return f"成功: {msg}"
        else:
            return f"失败: {msg}"
    except Exception as e:
        return f"执行出错: {str(e)}"

@mcp.tool()
def md_to_pdf_tool(md_path: str, pdf_path: str) -> str:
    """
    将 Markdown 文件直接转换为 PDF 文件 (中间生成临时的 DOCX)。
    
    Args:
        md_path: 源 Markdown 文件的绝对路径。
        pdf_path: 目标 PDF 文件的保存路径。
    """
    # 临时 DOCX 路径
    temp_docx_path = pdf_path.replace(".pdf", "_temp.docx")
    if temp_docx_path == pdf_path:
        temp_docx_path += ".docx"
        
    # 第一步：MD -> DOCX
    try:
        success_step1, msg_step1 = create_docx_from_md(md_path, temp_docx_path)
        if not success_step1:
            return f"步骤1失败 (MD->DOCX): {msg_step1}"
    except Exception as e:
        return f"步骤1异常 (MD->DOCX): {str(e)}"
        
    # 第二步：DOCX -> PDF
    try:
        success_step2, msg_step2 = convert_docx_to_pdf(temp_docx_path, pdf_path)
    except Exception as e:
        # 尝试清理临时文件
        if os.path.exists(temp_docx_path):
            try:
                os.remove(temp_docx_path)
            except:
                pass
        return f"步骤2异常 (DOCX->PDF): {str(e)}"
    
    # 清理临时文件
    try:
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
    except Exception as e:
        sys.stderr.write(f"Warning: 无法删除临时文件 {temp_docx_path}: {e}\n")
        
    if success_step2:
        return f"成功转换 {md_path} 为 {pdf_path}"
    else:
        return f"步骤2失败 (DOCX->PDF): {msg_step2}"

if __name__ == "__main__":
    mcp.run()
