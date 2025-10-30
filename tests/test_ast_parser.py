# tests/test_ast_parser.py
import pytest
from utils.ast_parser import ASTParser

def test_parser_initialization():
    """Basic initialization test"""
    parser = ASTParser()
    assert hasattr(parser, 'parsers')
    assert isinstance(parser.parsers, dict)

def test_at_least_one_parser_loaded():
    """Verify at least one language parser loaded"""
    parser = ASTParser()
    assert len(parser.parsers) > 0, "No language parsers were loaded"

def test_python_parser_available():
    """Test Python parser availability"""
    parser = ASTParser()
    if "python" not in parser.parsers:
        pytest.skip("Python parser not available (check build/my-languages.dll)")
    assert parser.parsers["python"] is not None

def test_unsupported_language():
    """Test error for unsupported languages"""
    parser = ASTParser()
    with pytest.raises(ValueError, match="Unsupported language"):
        parser.parse_code("code", "typescript")

def test_javascript_parser_available():
    parser = ASTParser()
    assert "javascript" in parser.parsers
    assert parser.parsers["javascript"] is not None

def test_python_code_parsing():
    parser = ASTParser()
    result = parser.parse_code("def hello(): pass", "python")
    assert isinstance(result, dict)
    assert "children" in result

# Add these to your test file
def test_parser_with_missing_library():
    """Test behavior when parser library is missing"""
    with pytest.raises(FileNotFoundError):
        ASTParser("nonexistent.dll")

def test_parser_error_handling():
    """Test error handling for malformed code"""
    parser = ASTParser()
    if "python" not in parser.parsers:
        pytest.skip("Python parser not available")
    
    # Test with invalid Python code
    with pytest.raises(ValueError, match="Failed to parse python code"):
        parser.parse_code("def hello(:", "python")

def test_parser_error_handling():
    """Test error handling for malformed code"""
    parser = ASTParser()
    if "python" not in parser.parsers:
        pytest.skip("Python parser not available")
    
    # Test with invalid Python code
    with pytest.raises(ValueError) as excinfo:
        parser.parse_code("def hello(:", "python")
    assert "Failed to parse python code" in str(excinfo.value)

def test_function_extraction():
    """Test function extraction capabilities"""
    parser = ASTParser()
    if "python" not in parser.parsers:
        pytest.skip("Python parser not available")
    
    code = """
    def greet(name: str) -> str:
        return f"Hello {name}"
    """
    functions = parser.extract_functions(code, "python")
    assert len(functions) == 1
    assert functions[0]['name'] == 'greet'
    assert 'name: str' in functions[0]['parameters']
    assert 'return f"Hello {name}"' in functions[0]['body']