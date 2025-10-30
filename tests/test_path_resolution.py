import os
import sys
from core.file_manager import FileManager

def test_path_resolution():
    # Initialize file manager with your workspace path
    workspace_path = os.path.abspath("./workspace")
    fm = FileManager(workspace_path)
    
    test_paths = [
        "app/main.py",
        "/app/main.py",
        "./app/main.py",
        "C:/Users/hp/OneDrive/Desktop/Devant/workspace/app/main.py",
        "../outside_file.py",
        "C:\\Users\\hp\\OneDrive\\Desktop\\Devant\\workspace\\app\\main.py"  # Windows style
    ]
    
    print(f"Working Directory: {workspace_path}")
    print("="*50)
    
    for path in test_paths:
        try:
            resolved = fm._resolve_path(path)
            print(f"Original: {path}")
            print(f"Resolved: {resolved}")
            print(f"Exists: {os.path.exists(resolved)}")
            print("-"*50)
        except Exception as e:
            print(f"Error with path '{path}': {str(e)}")
            print("-"*50)

if __name__ == "__main__":
    # Ensure the core module can be imported
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_path_resolution()