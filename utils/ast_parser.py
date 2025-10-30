"""
AST parsing using Tree-sitter for code analysis
"""
import os
from pathlib import Path
from tree_sitter import Language, Parser
from typing import Dict, List, Optional, Any, Union
from utils.logger import get_logger

class ASTParser:
    SUPPORTED_LANGUAGES = ['python', 'javascript']  # Add this class variable

    def __init__(self, library_path: str = None):
        self.logger = get_logger(__name__)
        self.parsers = {}
        self.library_path = Path(library_path) if library_path else self._get_default_library_path()
        self._load_languages()

    def _get_default_library_path(self) -> Path:
        """Get platform-specific default library path"""
        lib_name = "my-languages.dll" if os.name == "nt" else "my-languages.so"
        return Path("build") / lib_name
        
    def _load_languages(self):
        """Load Tree-sitter languages with version checking"""
        if not self.library_path.exists():
            self.logger.error(f"Parser library not found at {self.library_path}")
            raise FileNotFoundError(f"Parser library not found at {self.library_path}")

        try:
            # Load Python parser
            try:
                python_lang = Language(self.library_path, 'python')
                self.parsers['python'] = Parser()
                self.parsers['python'].set_language(python_lang)
            except Exception as e:
                self.logger.error(f"Failed to load Python parser: {str(e)}")
                raise

            # Load JavaScript parser
            try:
                js_lang = Language(self.library_path, 'javascript')
                self.parsers['javascript'] = Parser()
                self.parsers['javascript'].set_language(js_lang)
            except Exception as e:
                self.logger.error(f"Failed to load JavaScript parser: {str(e)}")
                # Don't raise here since Python might be the only required parser

        except Exception as e:
            self.logger.error(f"Critical parser loading error: {str(e)}")
            raise

    def _extract_parameters(self, node: Dict) -> str:
        """Extract function parameters from AST node"""
        for child in node['children']:
            if child['type'] == 'parameters':
                return child['text']
        return ''

    def _extract_body(self, node: Dict) -> str:
        """Extract function body from AST node"""
        for child in node['children']:
            if child['type'] == 'block':
                return child['text']
        return ''

    def parse_code(self, code: str, language: str) -> Dict[str, Any]:
        """Parse code and return AST with improved error handling"""
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}. Supported: {self.SUPPORTED_LANGUAGES}")

        if language not in self.parsers or not self.parsers.get(language):
            raise ValueError(f"Parser not available for language: {language}")

        try:
            tree = self.parsers[language].parse(bytes(code, "utf8"))
            if not tree or not tree.root_node:
                raise ValueError("Parsing failed - empty tree returned")
            
            # Additional check for syntax errors
            if tree.root_node.has_error:
                raise ValueError("Code contains syntax errors")
                
            return self._walk_tree(tree.root_node)
        except Exception as e:
            self.logger.error(f"Error parsing {language} code: {str(e)}")
            raise ValueError(f"Failed to parse {language} code: {str(e)}") from e

    def _walk_tree(self, node) -> Dict[str, Any]:
        """Recursively walk the AST with accurate text extraction"""
        return {
            'type': node.type,
            'text': node.text.decode('utf8') if hasattr(node, 'text') else None,
            'start_point': node.start_point,
            'end_point': node.end_point,
            'children': [self._walk_tree(child) for child in node.children]
        }

    def extract_functions(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Improved function extraction with precise text handling"""
        ast = self.parse_code(code, language)
        functions = []
        
        def _find_functions(node):
            if node['type'] in ['function_definition', 'method_definition']:
                func_node = {
                    'name': self._extract_identifier(node),
                    'parameters': self._extract_parameters(node),
                    'body': self._extract_body(node)
                }
                functions.append(func_node)
            
            for child in node['children']:
                _find_functions(child)
        
        _find_functions(ast)
        return functions

    def _extract_identifier(self, node: Dict) -> Optional[str]:
        """Extract identifier with proper whitespace handling"""
        for child in node['children']:
            if child['type'] == 'identifier':
                return child['text'].strip()
        return None
        
    def find_dependencies(self, code: str, language: str) -> List[str]:
        """Find dependencies (imports/requires) in code"""
        ast = self.parse_code(code, language)
        dependencies = []
        
        def _find_dependencies(node):
            if node['type'] in ['import_statement', 'import_from_statement', 'require_statement']:
                dep = code[node['start_point'][1]:node['end_point'][1]]
                dependencies.append(dep)
                
            for child in node['children']:
                _find_dependencies(child)
                
        _find_dependencies(ast)
        return dependencies