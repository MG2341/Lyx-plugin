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
        
        # Selection mode - NEW
        self.is_selection_mode = False
        self.current_prefix = ""
        
        # Current suggestions
        self.current_suggestions: List[Tuple[str, str]] = []
        self.selected_index = 0

        # AI prediction state (background Hugging Face model suggestions)
        self.ai_thread: Optional[threading.Thread] = None
        self.ai_cancel_event = threading.Event()

        # Special function key to clear the keystroke buffer when pressed
        # Default: F9
        self.clear_buffer_key = keyboard.Key.f9 if keyboard is not None else None
    
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
        print(r"Press Ctrl+\ to suggest completions")
        print(r"Use Ctrl+] or Ctrl+[ to navigate suggestions")
        print("Press Space to accept, Escape to cancel\n")
        
        # Set up keyboard listener
        self._setup_keyboard_listener()
    
    def _setup_keyboard_listener(self) -> None:
        """Set up the keyboard listener for trigger keys."""
        if keyboard is None:
            return
        
        def on_press(key) -> None:
            """Handle key press events."""
            try:
                # F8 to trigger suggestions
                if self._is_ctrl_backslash(key):
                    if self.is_selection_mode:
                        # If already in selection mode, cancel it
                        self.is_selection_mode = False
                        self.current_suggestions = []
                        print("[Selection Mode Cancelled]")
                    else:
                        self._on_suggest_trigger()
                
                # Handle numeric key selection in selection mode
                elif self.is_selection_mode and self._is_numeric_key(key):
                    num = self._get_numeric_key_value(key)
                    if 1 <= num <= len(self.current_suggestions):
                        self.apply_selected_suggestion(num - 1)
                        self.is_selection_mode = False
                        self.current_suggestions = []
                
                # Handle Escape to cancel selection mode
                elif self.is_selection_mode and self._is_escape_key(key):
                    self.is_selection_mode = False
                    self.current_suggestions = []
                    print("[Selection Mode Cancelled]")
                
                # Track regular keystrokes for buffer (only if NOT in selection mode)
                elif not self.is_selection_mode:
                    # Clear-buffer key (function key, e.g. F9)
                    if (
                        keyboard is not None
                        and isinstance(key, keyboard.Key)
                        and key == self.clear_buffer_key
                    ):
                        self.keystroke_buffer = ""
                        print("[DEBUG] Buffer cleared via F9")
                    # Normal character input goes into the buffer
                    elif hasattr(key, 'char') and key.char:
                        # If the user types while an AI prediction is running,
                        # request cancellation of the current prediction.
                        try:
                            if self.ai_cancel_event is not None:
                                self.ai_cancel_event.set()
                        except Exception:
                            pass

                        self.keystroke_buffer += key.char
                        self.last_keystroke_time = time.time()
                        print(f"[DEBUG] Keystroke: '{key.char}', buffer: '{self.keystroke_buffer}'")
            
            except Exception as e:
                print(f"Error in keyboard handler: {e}")
        
        def on_release(key) -> None:
            """Handle key release events."""
            pass
        
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
    
    def _is_ctrl_backslash(self, key) -> bool:
        """Check if the pressed key is F8 (trigger key)."""
        try:
            if isinstance(key, keyboard.Key):
                return key == keyboard.Key.f8
            return False
        except:
            return False
    
    def _is_numeric_key(self, key) -> bool:
        """Check if the key is a selection key (F1-F5)."""
        try:
            if keyboard is None:
                return False
            if isinstance(key, keyboard.Key):
                return key in (
                    keyboard.Key.f1,
                    keyboard.Key.f2,
                    keyboard.Key.f3,
                    keyboard.Key.f4,
                    keyboard.Key.f5,
                )
            return False
        except Exception:
            return False
    
    def _get_numeric_key_value(self, key) -> int:
        """Map selection key (F1-F5) to a number 1-5."""
        try:
            if keyboard is None:
                return 0
            if isinstance(key, keyboard.Key):
                mapping = {
                    keyboard.Key.f1: 1,
                    keyboard.Key.f2: 2,
                    keyboard.Key.f3: 3,
                    keyboard.Key.f4: 4,
                    keyboard.Key.f5: 5,
                }
                return mapping.get(key, 0)
            return 0
        except Exception:
            return 0
    
    def _is_escape_key(self, key) -> bool:
        """Check if the key is Escape."""
        try:
            if isinstance(key, keyboard.Key):
                return key == keyboard.Key.esc
            return False
        except:
            return False
    
    def _on_suggest_trigger(self) -> None:
        """Handle the suggestion trigger (F8) - shows menu without auto-applying."""
        print("\n[Autocomplete Triggered]")
        
        if not self.helper.is_ready():
            print("Error: LyX is not running")
            return
        
        # Get suggestions based on current keystroke buffer
        prefix = self.keystroke_buffer.split()[-1] if self.keystroke_buffer else ""
        print(f"[DEBUG] Current buffer: '{self.keystroke_buffer}', prefix: '{prefix}', len={len(prefix)}")
        
        if not prefix or len(prefix) < 1:
            print("Type at least 1 character to get suggestions")
            return
        
        suggestions = self.engine.get_suggestions(prefix)
        
        if not suggestions:
            print(f"No suggestions for '{prefix}'")
            self.keystroke_buffer = ""
            return
        
        # Store suggestions and enter selection mode
        self.current_suggestions = suggestions
        self.current_prefix = prefix
        self.selected_index = 0
        self.is_selection_mode = True
        
        # Display suggestions
        self._show_suggestions()

        # Kick off an asynchronous AI-based suggestion using the last
        # 100 characters of the buffer as context. The AI worker will
        # be cancelled automatically if the user continues typing while
        # it is running.
        try:
            context_tail = self.keystroke_buffer[-100:] if self.keystroke_buffer else ""
            if context_tail:
                self._start_ai_suggestion(self.current_prefix, context_tail)
        except Exception as e:
            print(f"[AI][ERROR] Failed to start AI suggestion: {e}")
    
    def apply_selected_suggestion(self, index: int) -> None:
        """Apply a selected suggestion to LyX."""
        if not (0 <= index < len(self.current_suggestions)):
            print(f"[ERROR] Invalid selection index: {index}")
            return
        
        try:
            display, replacement = self.current_suggestions[index]
            print(f"\n[Applying] {display}")
            print(f"[DEBUG] Using prefix '{self.current_prefix}' (len={len(self.current_prefix)}) for deletion")
            
            if not self.helper.is_ready():
                print("[ERROR] LyX is not accessible")
                return
            success = self.helper.apply_suggestion(self.current_prefix, replacement)
            
            if success:
                print("[OK] Suggestion applied!")
                # Clear buffer after successful application
                self.keystroke_buffer = ""
            else:
                print("[ERROR] Failed to apply suggestion")
        
        except Exception as e:
            print(f"[ERROR] Exception while applying suggestion: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_suggestions(self) -> None:
        """Display current suggestions and wait for selection."""
        if not self.current_suggestions:
            return
        
        print("\n[Suggestions - Press F1-F5 to select, ESC to cancel]")
        for i, (display, _) in enumerate(self.current_suggestions[:5]):
            marker = "→ " if i == self.selected_index else "  "
            print(f"{marker}{i+1}. {display}")

    def _start_ai_suggestion(self, prefix: str, context_text: str) -> None:
        """Start a background AI prediction based on the given context.

        The prediction runs in a separate thread and, once finished,
        adds an "AI:" suggestion at the top of the suggestions list,
        unless the user has typed again in the meantime or explicitly
        cancelled the prediction.
        """

        # Cancel any existing prediction
        try:
            if self.ai_thread is not None and self.ai_thread.is_alive():
                self.ai_cancel_event.set()
        except Exception:
            pass

        # Reset cancellation flag for the new prediction
        self.ai_cancel_event = threading.Event()
        start_time = time.time()

        def worker() -> None:
            try:
                from ai_prediction import get_ai_prediction
            except ImportError as exc:
                print(
                    "[AI][ERROR] transformers not installed; "
                    "AI-based suggestions are disabled. Install with "
                    "'pip install transformers torch'."
                )
                print(f"[AI][DEBUG] Import error: {exc}")
                return

            # Generate the continuation; this is cancellable via
            # self.ai_cancel_event which is checked inside
            # get_ai_prediction.
            prediction = get_ai_prediction(context_text, cancel_event=self.ai_cancel_event)

            # If cancelled or empty, do nothing
            if not prediction or self.ai_cancel_event.is_set():
                return

            # If the user has typed after the prediction started,
            # discard the result to avoid stale completions.
            if self.last_keystroke_time > start_time:
                print("[AI][DEBUG] Discarding stale AI suggestion due to new typing.")
                return

            display = f"AI: {prediction}"
            replacement = prediction

            # Insert AI suggestion at the top so it appears as option 1
            try:
                self.current_suggestions.insert(0, (display, replacement))
                self._show_suggestions()
                print("[AI] New AI suggestion added as option 1.")
            except Exception as exc:
                print(f"[AI][ERROR] Failed to add AI suggestion: {exc}")

        self.ai_thread = threading.Thread(target=worker, daemon=True)
        self.ai_thread.start()
    
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
            print(f"Pipe path: {service.lyx_client.pipe_in}")
            import os
            pipe_exists = os.path.exists(service.lyx_client.pipe_in)
            print(f"Pipe file exists: {pipe_exists}")
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
