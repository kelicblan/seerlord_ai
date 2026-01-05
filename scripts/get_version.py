import re
import os
import sys

def get_version():
    pyproject_path = os.path.join(os.getcwd(), 'pyproject.toml')
    if not os.path.exists(pyproject_path):
        return None
        
    with open(pyproject_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Search for version = "X.Y.Z"
    # Note: This simple regex assumes the first occurrence is the correct one (usually in [tool.poetry] or [project])
    pattern = r'version\s*=\s*"([^"]+)"'
    match = re.search(pattern, content)
    
    if match:
        return match.group(1)
    return None

if __name__ == "__main__":
    v = get_version()
    if v:
        print(v)
    else:
        sys.exit(1)
