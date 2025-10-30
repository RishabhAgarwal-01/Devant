import sys
import os
from tree_sitter import Language

def build():
    # Create build directory if it doesn't exist
    os.makedirs('build', exist_ok=True)
    
    # Windows-specific paths
    parser_paths = [
        os.path.join('vendor', 'tree-sitter-python'),
        os.path.join('vendor', 'tree-sitter-javascript'),
        # os.path.join('vendor', 'tree-sitter-typescript')
    ]
    
    # Verify all parser directories exist
    for path in parser_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Parser directory not found: {path}")
    
    # Build the library
    Language.build_library(
        # Windows needs .dll
        os.path.join('build', 'my-languages.dll'),
        parser_paths
    )
    print("Successfully built parsers!")

if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)