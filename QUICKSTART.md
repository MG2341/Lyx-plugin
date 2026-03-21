# LyX Autocomplete Plugin - Quick Start Guide

## Installation (Windows)

### Step 1: Run Setup
Double-click **`setup.bat`** in the plugin folder. This will:
- Create a Python virtual environment
- Install required dependencies
- Run tests to verify installation
- Offer to start the service

### Step 2: Basic Configuration
The plugin auto-detects your LyX installation. If needed, edit `lyx_server_client.py` and change:
```python
lyx_home = os.path.join(os.environ.get('APPDATA', ''), 'LyX2.5')
```

Update `LyX2.5` to your LyX version (e.g., `LyX2.4`, `LyX2.3`).

## Quick Usage

### Test Mode (First Time)
```bash
python autocomplete_service.py --interactive
```
Type test prefixes like:
- `sum` → $\sum$ 
- `teh` → the
- `alpha` → α

### Normal Mode
```bash
python autocomplete_service.py
```
Or simply double-click **`run.bat`**

## File Overview

| File | Purpose |
|------|---------|
| `autocomplete_engine.py` | Core suggestion engine - math and text completions |
| `lyx_server_client.py` | Communicates with LyX via named pipes |
| `autocomplete_service.py` | Main service - monitors and applies suggestions |
| `setup.bat` | Windows setup script |
| `run.bat` | Quick launcher for the service |
| `test.py` | Automated tests for all components |
| `requirements.txt` | Python dependencies |

## Key Features

### Math Completions
- Greek letters: `alp` → $\alpha$, `bet` → $\beta$, etc.
- Operators: `sum` → $\sum$, `int` → $∫$, `frac` → \frac{}{}
- Relations: `leq` → $\leq$, `neq` → $\neq$, `approx` → $\approx$

### Text Completions  
- Typo fixes: `teh` → the, `recieve` → receive
- Word completions: `the` → they, then, them, these
- 100+ common English words available

### LaTeX Environments
- `eq` → equation environment template
- `align` → align environment
- `itemize`, `enumerate` → list templates

## Troubleshooting

### "LyX is not running"
1. Make sure LyX is open
2. Check that pipes are enabled: Tools > Preferences > Paths
3. Verify the config path matches your LyX installation

### "pynput" error
Run: `pip install pynput`

### No suggestions appearing
1. Type at least 2 characters
2. Use interactive mode to verify: `python autocomplete_service.py --interactive`
3. Check that your input matches the suggestion keywords

## Customization

Edit `autocomplete_engine.py` to add your own:

### Add a Math Symbol
```python
MATH_COMPLETIONS = {
    # ... existing entries ...
    'myvar': r'\mathbf{x}',  # Type 'myvar' to insert \mathbf{x}
}
```

### Add a Typo Correction
```python
TEXT_COMPLETIONS = {
    # ... existing entries ...
    'miserablle': 'miserable',
}
```

### Add a Common Word
```python
COMMON_WORDS = {
    # ... existing entries ...
    'myspecialword',
}
```

## Next Steps

1. **Test the Engine**: Run `python test.py` to verify everything works
2. **Interactive Testing**: Use `python autocomplete_service.py --interactive` 
3. **Enable Service**: Run `python autocomplete_service.py` to start the autocomplete daemon
4. **Create Shortcuts**: Add `run.bat` to your Windows startup folder for auto-launch

## API Example

Use in your own Python scripts:

```python
from autocomplete_engine import AutocompleteEngine
from lyx_server_client import LyXServerClient

# Get suggestions
engine = AutocompleteEngine()
suggestions = engine.get_suggestions('alp', in_math_mode=True)
# Returns: [('$alpha$ => \\alpha', '\\alpha'), ...]

# Apply suggestion to LyX  
client = LyXServerClient()
if client.is_lyx_running():
    client.insert_math(r'\alpha')
```

## Getting Help

1. Check [LyX Server Documentation](https://wiki.lyx.org/LyX/LyXServer)
2. Read the detailed README.md
3. Review inline code comments in the Python files
4. Run test suite: `python test.py`

## License

MIT License - Free to use and modify

---

**Enjoy intelligent autocomplete in LyX!** 📝✨
