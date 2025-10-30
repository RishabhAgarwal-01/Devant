import asyncio
from core.code_analyzer import CodeAnalyzer
from adapters.llm_adapter import LLMAdapter
from config.settings import load_config
import os

async def test_analyzer():
    # Setup
    config = load_config("config/default.json")
    llm = LLMAdapter(config["llm"])
    analyzer = CodeAnalyzer(llm)
    
    # Test 1: Language detection
    test_code = "import os\ndef foo():\n    pass"
    analysis = await analyzer.analyze(test_code, "test.py")
    assert analysis.language == "python", f"Expected python, got {analysis.language}"
    
    # Test 2: Import detection (with more obvious syntax)
    test_code = """
    import os
    import sys
    from typing import List
    """
    analysis = await analyzer.analyze(test_code, "test_imports.py")
    assert "os" in analysis.imports, f"Missing 'os' in {analysis.imports}"
    assert "sys" in analysis.imports, f"Missing 'sys' in {analysis.imports}"
    assert "typing.List" in analysis.imports, f"Missing 'typing.List' in {analysis.imports}"
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_analyzer())