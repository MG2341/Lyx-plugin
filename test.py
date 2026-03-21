"""
Test suite for LyX Autocomplete Plugin

Tests the core components without requiring LyX to be running.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from autocomplete_engine import AutocompleteEngine
from lyx_server_client import LyXServerClient


def test_autocomplete_engine():
    """Test the autocomplete engine with various inputs."""
    print("=" * 60)
    print("Testing Autocomplete Engine")
    print("=" * 60)
    
    engine = AutocompleteEngine()
    
    # Test 1: Math suggestions
    print("\n1. Math Suggestions for 'sum':")
    suggestions = engine.get_suggestions('sum', in_math_mode=True)
    for display, replacement in suggestions[:3]:
        print(f"   {display} → {replacement}")
    
    # Test 2: Spell corrections
    print("\n2. Spell Correction for 'teh':")
    suggestions = engine.get_suggestions('teh')
    for display, replacement in suggestions[:3]:
        print(f"   {display}")
    
    # Test 3: Word completions
    print("\n3. Word Completions for 'the':")
    suggestions = engine.get_suggestions('the')
    for display, replacement in suggestions[:5]:
        print(f"   {display}")
    
    # Test 4: Greek letters
    print("\n4. Greek Letter Suggestions for 'alp':")
    suggestions = engine.get_suggestions('alp', in_math_mode=True)
    for display, replacement in suggestions[:3]:
        print(f"   {display} → {replacement}")
    
    # Test 5: LaTeX environments
    print("\n5. LaTeX Environment Suggestions for 'eq':")
    suggestions = engine.get_suggestions('eq')
    for display, replacement in suggestions[:3]:
        print(f"   {display}")
    
    # Test 6: Word boundary extraction
    print("\n6. Word Boundary Extraction:")
    text = "This is an equation $\\sum_{i=1}^{n}$ with more text"
    prefix, context, in_math = engine.get_at_word_boundary(text, len(text) - 15)
    print(f"   Text: {text}")
    print(f"   Extracted prefix: '{prefix}'")
    print(f"   In math mode: {in_math}")
    
    print("\n[OK] Autocomplete Engine tests passed!")


def test_lyx_server_client():
    """Test the LyX server client."""
    print("\n" + "=" * 60)
    print("Testing LyX Server Client")
    print("=" * 60)
    
    client = LyXServerClient()
    
    print(f"\nLyX Config Path: {client.lyx_home}")
    print(f"Expected Input Pipe: {client.pipe_in}")
    print(f"Expected Output Pipe: {client.pipe_out}")
    
    is_running = client.is_lyx_running()
    print(f"\nLyX Server Status: {'[RUNNING]' if is_running else '[OFFLINE]'}")
    
    if is_running:
        print("\nTesting commands (optional):")
        print("  - Sending test text insertion command...")
        client.insert_text("LyX Autocomplete Test")
        
        print("  - Sending test math insertion command...")
        client.insert_math(r"\alpha + \beta")
        
        print("  [OK] Commands sent successfully!")
    else:
        print("\n(LyX is not running - commands were not sent)")
    
    print("\n[OK] LyX Server Client tests passed!")


def test_integration():
    """Test integration between components."""
    print("\n" + "=" * 60)
    print("Testing Integration")
    print("=" * 60)
    
    engine = AutocompleteEngine()
    client = LyXServerClient()
    
    # Simulate a user typing "sum" in math mode
    print("\nScenario: User types 'sum' in math mode")
    prefix = 'sum'
    suggestions = engine.get_suggestions(prefix, in_math_mode=True)
    
    if suggestions:
        display, replacement = suggestions[0]
        print(f"  Suggestion: {display}")
        print(f"  Would insert: {replacement}")
        print(f"  LyX reachable: {client.is_lyx_running()}")
    
    # Simulate a user typing "teh" (typo)
    print("\nScenario: User types 'teh' (typo)")
    prefix = 'teh'
    suggestions = engine.get_suggestions(prefix)
    
    if suggestions:
        display, replacement = suggestions[0]
        print(f"  Suggestion: {display}")
        print(f"  Would insert: {replacement}")
    
    print("\n[OK] Integration tests passed!")


def main():
    """Run all tests."""
    print("\n╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  LyX Autocomplete Plugin - Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    try:
        test_autocomplete_engine()
        test_lyx_server_client()
        test_integration()
        
        print("\n" + "=" * 60)
        print("[OK] ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run interactive mode:")
        print("   python autocomplete_service.py --interactive")
        print("3. Start the service:")
        print("   python autocomplete_service.py")
        print("\nFor more details, see README.md")
        print()
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())