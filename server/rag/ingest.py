from markitdown import MarkItDown
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
import os

class IngestionService:
    def __init__(self):
        """
        初始化文档解析与分块器。
        """
        self.md = MarkItDown()
        # 针对中文与技术文档优化分块策略
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )

    def parse_file(self, file_path: str) -> str:
        """
        将文件解析为 Markdown 文本。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            # MarkItDown 可将 PDF、DOCX 等多种格式转换为 Markdown
            result = self.md.convert(file_path)
            # 转换结果通常通过 .text_content 提供主体文本
            return result.text_content
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            raise

    def chunk_text(self, text: str) -> list[str]:
        """
        将长文本切分为多个 chunk。
        """
        if not text:
            return []
        return self.splitter.split_text(text)
