
import re
from typing import List
from langchain_core.messages import HumanMessage

# Mock logger
class Logger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")

logger = Logger()

def extract_file_path_debug(content: str) -> str | None:
    logger.info(f"Analyzing content (repr): {repr(content)}")
    
    # 0. Normalize content
    # Replace weird hyphens
    content = content.replace('−', '-')
    # Remove zero-width spaces if any (u200b)
    content = content.replace('\u200b', '')
    content = content.replace('\\\\', '\\')

    logger.info(f"Normalized content (repr): {repr(content)}")

    # 1. Try to match explicit [附件: path] format
    # Note: added re.DOTALL just in case, though not strictly needed for single line
    attachment_match = re.search(r'\[?附件:\s*(.*?)(\]|[\r\n]|$)', content)
    if attachment_match:
        path = attachment_match.group(1).strip()
        if path.endswith(']'):
            path = path[:-1].strip()
        
        logger.info(f"Match group 1: {repr(path)}")
        
        if path and (':' in path or '/' in path or '\\' in path):
            path = path.strip('"').strip("'")
            logger.info(f"Found path via attachment prefix: {path}")
            return path
        else:
            logger.warning("Path found but failed basic validation (needs : / or \\)")

    # 2. Aggressive Regex
    path_pattern = r'([a-zA-Z]:[\\/][^"\n\r<>|?*]+?\.(docx|pdf|md|txt))|(/[^"\n\r<>|?*]+?\.(docx|pdf|md|txt))'
    match = re.search(path_pattern, content, re.IGNORECASE)
    if match:
        path = match.group(0).strip()
        logger.info(f"Found path via regex: {path}")
        return path

    logger.warning("No file path found.")
    return None

# The user input string copied exactly from the prompt
# "附件:E:\workspaces​eerlord\seerlorda​i\server\data\uploads\e398cad2−c4d4−4668−ace4−2fc3380dc966.docx"
# Note: I am pasting it as is.
raw_input = "附件:E:\workspaces​eerlord\seerlorda​i\server\data\uploads\e398cad2−c4d4−4668−ace4−2fc3380dc966.docx"

print("--- Debug Run ---")
extract_file_path_debug(raw_input)
