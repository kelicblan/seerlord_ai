import re
import os
import sys

def bump_version(version_str):
    """
    Bumps the minor version by 1 and resets patch to 0.
    e.g., 0.1.0 -> 0.2.0
    """
    parts = version_str.split('.')
    if len(parts) >= 2:
        try:
            major = int(parts[0])
            minor = int(parts[1])
            # Keep patch if exists, but usually bumping minor resets patch.
            # User asked for "add 0.1", which implies 0.1 -> 0.2
            new_minor = minor + 1
            new_patch = 0
            
            # Construct new version
            # If original was X.Y.Z, return X.Y+1.0
            # If original was X.Y, return X.Y+1
            if len(parts) > 2:
                return f"{major}.{new_minor}.{new_patch}"
            else:
                return f"{major}.{new_minor}"
        except ValueError:
            return version_str
    return version_str

def update_pyproject(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex for version = "X.Y.Z"
    # pyproject.toml usually has version = "..." under [tool.poetry] or [project]
    pattern = r'(version\s*=\s*")([^"]+)(")'
    match = re.search(pattern, content)
    
    new_version = None
    if match:
        current_version = match.group(2)
        new_version = bump_version(current_version)
        print(f"Bumping pyproject.toml: {current_version} -> {new_version}")
        
        new_content = content[:match.start(2)] + new_version + content[match.end(2):]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
    return new_version

def update_package_json(file_path, specific_version=None):
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex for "version": "X.Y.Z"
    pattern = r'("version"\s*:\s*")([^"]+)(")'
    match = re.search(pattern, content)
    
    if match:
        current_version = match.group(2)
        # If specific_version provided, use it, otherwise bump existing
        new_version = specific_version if specific_version else bump_version(current_version)
        
        print(f"Updating {file_path}: {current_version} -> {new_version}")
        
        new_content = content[:match.start(2)] + new_version + content[match.end(2):]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

def main():
    root_dir = os.getcwd()
    pyproject_path = os.path.join(root_dir, 'pyproject.toml')
    admin_pkg_path = os.path.join(root_dir, 'admin', 'package.json')
    
    # 1. Update pyproject.toml (Primary Source of Truth)
    if os.path.exists(pyproject_path):
        new_version = update_pyproject(pyproject_path)
        
        # 2. Sync admin/package.json
        if new_version and os.path.exists(admin_pkg_path):
            update_package_json(admin_pkg_path, specific_version=new_version)
    else:
        print("Error: pyproject.toml not found!")
        sys.exit(1)

if __name__ == "__main__":
    main()
