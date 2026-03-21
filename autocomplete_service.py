"""
LyX Autocomplete Service - Main daemon/service that monitors and applies suggestions
"""

import sys
import time
import threading
from typing import Optional, List, Tuple
from pathlib import Path

# Try to import required libraries
try:
    from pynput import keyboard
except ImportError:
    keyboard = None


from autocomplete_engine import AutocompleteEngine
from lyx_server_client import LyXServerClient, LyXAutocompleteHelper


class AutocompleteService:
    """Main service for LyX autocomplete functionality."""
    
    def __init__(self):
        """Initialize the autocomplete service."""
        self.engine = AutocompleteEngine()
        self.lyx_client = LyXServerClient()
        self.helper = LyXAutocompleteHelper(self.lyx_client)
        
        # State tracking
        self.is_listening = False
        self.last_keystroke_time = 0
        self.keystroke_buffer = ""
        self.debounce_delay = 0.2  # seconds
        
        # Current suggestions
        self.current_suggestions: List[Tuple[str, str]] = []
        self.selected_index = 0
    
    def start(self) -> None:
        """Start the autocomplete service."""
        print("LyX Autocomplete Service Starting...")
        print(f"LyX Config Path: {self.lyx_client.lyx_home}")
        print(f"Checking if LyX is running...")
        
        if not self.helper.is_ready():
            print("WARNING: LyX is not currently running or pipes are not accessible.")
            print("Make sure:")
            print("  1. LyX is running")
            print("  2. LyX pipes are enabled (Tools > Preferences > Paths)")
            print("  3. The .lyxpipe files exist in the LyX config directory")
            # Continue anyway - user might start LyX later
        else:
            print("[OK] LyX is accessible!")
        
        # Start listening for keyboard if pynput is available
        if keyboard is None:
            print("\nWARNING: pynput not installed. Keyboard monitoring disabled.")
            print("Install it with: pip install pynput")
            return
        
        self.is_listening = True
        print("\n[OK] Autocomplete service is ready!")
        print("Press Ctrl+\ to suggest completions")
        print("Use Ctrl+] or Ctrl+[ to navigate suggestions")
        print("Press Space to accept, Escape to cancel\n")
        
        # Set up keyboard listener
        self._setup_keyboard_listener()
    
    def _setup_keyboard_listener(self) -> None:
        """Set up the keyboard listener for trigger keys."""
        if keyboard is None:
            return
        
        def on_press(key: keyboard.Key) -> None:
            """Handle key press events."""
            try:
                # Ctrl+\ to trigger suggestions
                if self._is_ctrl_backslash(key):
                    self._on_suggest_trigger()
                
                # Track regular keystrokes for buffer
                if hasattr(key, 'char') and key.char:
                    self.keystroke_buffer += key.char
                    self.last_keystroke_time = time.time()
            
            except Exception as e:
                print(f"Error in keyboard handler: {e}")
        
        def on_release(key: keyboard.Key) -> None:
            """Handle key release events."""
            pass
        
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
    
    def _is_ctrl_backslash(self, key) -> bool:
        """Check if the pressed key is Ctrl+Backslash."""
        try:
            # This is a simplified check - adjust based on your trigger preference
            if isinstance(key, keyboard.Key):
                return key == keyboard.Key.f8  # Use F8 as trigger for now (easier to detect)
            return False
        except:
            return False
    
    def _on_suggest_trigger(self) -> None:
        """Handle the suggestion trigger (Ctrl+\\ or hotkey)."""
        print("\n[Autocomplete Triggered]")
        
        if not self.helper.is_ready():
            print("Error: LyX is not running")
            return
        
        # Get suggestions based on current keystroke buffer
        # In a real implementation, you'd get the actual buffer from LyX
        prefix = self.keystroke_buffer.split()[-1] if self.keystroke_buffer else ""
        
        if not prefix or len(prefix) < 2:
            print("Type at least 2 characters to get suggestions")
            return
        
        suggestions = self.engine.get_suggestions(prefix)
        
        if not suggestions:
            print(f"No suggestions for '{prefix}'")
            return
        
        self.current_suggestions = suggestions
        self.selected_index = 0
        
        # Display suggestions
        self._show_suggestions()
    
    def _show_suggestions(self) -> None:
        """Display current suggestions to the user."""
        if not self.current_suggestions:
            return
        
        print("\n[Suggestions]")
        for i, (display, _) in enumerate(self.current_suggestions[:5]):
            marker = "→ " if i == self.selected_index else "  "
            print(f"{marker}{i+1}. {display}")
        
        print("\nPress: 1-5 to select, Esc to cancel")
    
    def run_interactive_mode(self) -> None:
        """Run in interactive mode for testing without keyboard listener."""
        print("LyX Autocomplete Service - Interactive Mode")
        print(f"LyX Config Path: {self.lyx_client.lyx_home}")
        
        if not self.helper.is_ready():
            print("WARNING: LyX is not currently running!")
        
        while True:
            try:
                prefix = input("\nEnter prefix (or 'quit'): ").strip()
                
                if prefix.lower() == 'quit':
                    break
                
                if not prefix:
                    continue
                
                suggestions = self.engine.get_suggestions(prefix)
                
                if not suggestions:
                    print(f"No suggestions for '{prefix}'")
                    continue
                
                print(f"\nSuggestions for '{prefix}':")
                for i, (display, replacement) in enumerate(suggestions[:10], 1):
                    print(f"{i:2}. {display}")
                
                # Interactive selection
                choice = input("\nEnter number to apply (or press Enter to skip): ").strip()
                
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(suggestions):
                        display, replacement = suggestions[idx]
                        
                        if self.helper.is_ready():
                            print(f"Applying: {replacement}")
                            self.helper.apply_suggestion(prefix, replacement)
                        else:
                            print(f"Would insert: {replacement}")
                        
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point."""
    service = AutocompleteService()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive':
            service.run_interactive_mode()
        elif sys.argv[1] == '--test-lyx':
            # Test LyX connectivity
            print(f"Testing LyX connection...")
            print(f"LyX home: {service.lyx_client.lyx_home}")
            print(f"Accessible: {service.helper.is_ready()}")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
    else:
        # Start the service
        try:
            service.start()
            # Keep the service running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nAutocomplete service stopped.")


if __name__ == '__main__':
    main()
