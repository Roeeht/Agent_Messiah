"""Test language separation - ensure Hebrew only in approved files."""

import re
from pathlib import Path

# Hebrew Unicode range
HEBREW_PATTERN = re.compile(r'[\u0590-\u05FF]+')

# Files allowed to contain Hebrew
ALLOWED_HEBREW_FILES = [
    'app/language/caller_he.py',
    'app/language/translator.py',  # Has Hebrew in docstring examples
    'demo_llm.py',  # Demo file - can have Hebrew examples
    'app/leads_store.py',  # Lead names can be Hebrew (real data)
    'app/calendar_store.py',  # Display text for caller (will be refactored)
]


def test_no_hebrew_in_unauthorized_files():
    """Verify Hebrew only appears in approved caller_he.py file."""
    project_root = Path(__file__).parent.parent
    violations = []
    
    # Check all Python files
    for py_file in project_root.rglob('*.py'):
        # Skip test files and virtual environments
        if 'test' in str(py_file) or 'venv' in str(py_file) or '.venv' in str(py_file):
            continue
            
        rel_path = str(py_file.relative_to(project_root))
        
        # Skip if in allowed list
        if rel_path in ALLOWED_HEBREW_FILES:
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8')
            if HEBREW_PATTERN.search(content):
                # Find lines with Hebrew
                lines_with_hebrew = []
                for i, line in enumerate(content.split('\n'), 1):
                    if HEBREW_PATTERN.search(line):
                        lines_with_hebrew.append(f"  Line {i}: {line[:60]}...")
                
                violations.append({
                    'file': rel_path,
                    'lines': lines_with_hebrew[:5]  # First 5 occurrences
                })
        except Exception as e:
            # Skip files that can't be read
            continue
    
    if violations:
        error_msg = "Hebrew found in unauthorized files:\n"
        for v in violations:
            error_msg += f"\n{v['file']}:\n" + "\n".join(v['lines'])
        raise AssertionError(error_msg)


def test_caller_he_has_hebrew():
    """Verify caller_he.py actually contains Hebrew text."""
    caller_he_file = Path(__file__).parent.parent / 'app' / 'language' / 'caller_he.py'
    
    assert caller_he_file.exists(), "caller_he.py must exist"
    
    content = caller_he_file.read_text(encoding='utf-8')
    assert HEBREW_PATTERN.search(content), "caller_he.py must contain Hebrew text"


def test_twiml_builder_no_empty_say():
    """Ensure TwiML builders don't create empty Say tags."""
    from app.twiml_builder import build_voice_twiml, build_error_twiml
    from app.language.caller_he import get_caller_text
    
    # Test voice TwiML
    greeting = get_caller_text("greeting_default")
    twiml = build_voice_twiml(greeting, "CALL123", 1)
    
    # Check no empty Say tags
    assert '<Say language="he-IL"></Say>' not in twiml
    assert '<Say language="he-IL"/>' not in twiml
    assert '<Say' in twiml and '</Say>' in twiml
    
    # Test error TwiML
    error_msg = get_caller_text("technical_error")
    error_twiml = build_error_twiml(error_msg)
    
    assert '<Say language="he-IL"></Say>' not in error_twiml
    assert '<Say' in error_twiml


if __name__ == "__main__":
    # Run tests manually
    try:
        test_no_hebrew_in_unauthorized_files()
        print("✓ No Hebrew in unauthorized files")
    except AssertionError as e:
        print(f"✗ Hebrew found in unauthorized files:\n{e}")
        exit(1)
    
    try:
        test_caller_he_has_hebrew()
        print("✓ caller_he.py contains Hebrew")
    except AssertionError as e:
        print(f"✗ caller_he.py issue:\n{e}")
        exit(1)
    
    try:
        test_twiml_builder_no_empty_say()
        print("✓ TwiML builders produce valid content")
    except AssertionError as e:
        print(f"✗ TwiML builder issue:\n{e}")
        exit(1)
    
    print("\n✅ All language separation tests passed!")
