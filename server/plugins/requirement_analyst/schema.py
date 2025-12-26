from pydantic import BaseModel, Field

class ParseDocumentInput(BaseModel):
    file_path: str = Field(description="Uploaded file path (docx/pdf)")

class GenerateDocxInput(BaseModel):
    content: str = Field(description="Markdown content")
    filename_prefix: str = Field(description="Prefix for the output filename")
