from docx2pdf import convert
import os
import sys
from contextlib import redirect_stdout
import io

def convert_docx_to_pdf(docx_path, pdf_path):
    if os.path.exists(docx_path):
        # sys.stderr.write(f"Converting {docx_path} to PDF...\n")
        try:
            # Capture any stdout from docx2pdf to avoid corrupting MCP JSON-RPC
            with redirect_stdout(io.StringIO()):
                convert(docx_path, pdf_path)
            # print(f"Successfully created {pdf_path}")
            return True, f"Successfully created {pdf_path}"
        except Exception as e:
            error_msg = f"Error converting to PDF: {e}"
            sys.stderr.write(error_msg + "\n")
            return False, error_msg
    else:
        error_msg = f"File not found: {docx_path}"
        sys.stderr.write(error_msg + "\n")
        return False, error_msg

if __name__ == '__main__':
    docx_path = r"e:\workspace_seerlord\test\attachment_approval_plan.docx"
    pdf_path = r"e:\workspace_seerlord\test\attachment_approval_plan.pdf"
    convert_docx_to_pdf(docx_path, pdf_path)
