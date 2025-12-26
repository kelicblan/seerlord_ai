# MD to Files MCP Server

这是一个 MCP (Model Context Protocol) Server，提供 Markdown 文件转换功能。

## 功能

- **md_to_docx_tool**: 将 Markdown 文件转换为 DOCX 文件。
- **docx_to_pdf_tool**: 将 DOCX 文件转换为 PDF 文件。
- **md_to_pdf_tool**: 将 Markdown 文件转换为 PDF 文件（自动处理中间步骤）。

## 依赖

- Python 3.10+
- Microsoft Word (用于 docx 转 pdf)
- 依赖包: `mcp`, `python-docx`, `docx2pdf`

## 安装

```bash
pip install -r requirements.txt
```

## 使用

可以直接运行 server:

```bash
python server.py
```

或者在 Claude Desktop 配置中添加:

```json
{
  "mcpServers": {
    "mdtofiles": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```
