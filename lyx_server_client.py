"""
LyX Server Client - Communicates with LyX via named pipes
"""

import os
import re
from typing import Optional, Dict, Tuple
from pathlib import Path


class LyXServerClient:
    """Client for communicating with LyX via named pipes (lyxpipe)."""
    
    def __init__(self, lyx_home: Optional[str] = None):
        """
        Initialize the LyX server client.
        
        Args:
            lyx_home: Unused on Windows named-pipe setups; kept for API compatibility.
        """
        # Keep the attribute for callers that expect a config path,
        # even though we no longer use it to construct the pipe path.
        self.lyx_home = lyx_home

        # Basic Windows LyXServer named pipe base path.
        # LyX will create "\\\.\pipe\lyxpipe.in" and "\\\.\pipe\lyxpipe.out".
        # You can override this with the LYX_PIPE environment variable.
        self.pipe_base = os.environ.get('LYX_PIPE') or r"\\.\pipe\lyxpipe"

        # Normalize if the base already includes .in/.out
        if self.pipe_base.endswith('.in'):
            self.pipe_base = self.pipe_base[:-3]
        elif self.pipe_base.endswith('.out'):
            self.pipe_base = self.pipe_base[:-4]

        # Standard LyX naming: <base>.in / <base>.out
        self.pipe_in = f"{self.pipe_base}.in"
        self.pipe_out = f"{self.pipe_base}.out"
    
    def send_command(self, function: str, argument: str = "", client: str = "external") -> bool:
        """
        Send a command to LyX via the input pipe.
        
        Args:
            function: LyX function name (e.g., 'self-insert', 'math-insert')
            argument: Argument for the function
            client: Client identifier
            
        Returns:
            True if successful
        """
        import time
        max_retries = 3
        retry_delay = 0.1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Format: LYXCMD:<client>:<function>:<argument>\n
                # LyXServer expects line-based commands terminated by a newline
                command = f"LYXCMD:{client}:{function}:{argument}"
                
                print(f"[DEBUG] Sending to LyX: {command}")

                # Always send a newline so LyX can parse the command
                with open(self.pipe_in, 'w', encoding='utf-8', newline='\n') as pipe:
                    pipe.write(command + "\n")
                    pipe.flush()
                
                return True
            
            except FileNotFoundError:
                print(f"[ERROR] Pipe file not found at {self.pipe_in}")
                print(f"[ERROR] Make sure LyX is running and server pipes are enabled")
                return False
            
            except IOError as e:
                if attempt < max_retries - 1:
                    print(f"[WARNING] Pipe busy or inaccessible (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[ERROR] Failed to send command after {max_retries} attempts: {e}")
                    print(f"[ERROR] Pipe path: {self.pipe_in}")
                    return False
            
            except Exception as e:
                print(f"[ERROR] Unexpected error sending command: {e}")
                print(f"[ERROR] Pipe path: {self.pipe_in}")
                return False
        
        return False
    
    def insert_text(self, text: str) -> bool:
        """Insert text at cursor position - one character at a time."""
        import time
        success = True
        for char in text:
            # Use the proper LyX format for self-insert
            escaped = self._escape_for_lyx(char)
            if not self.send_command('self-insert', escaped):
                print(f"Warning: Failed to insert character '{char}'")
                success = False
            time.sleep(0.05)  # Small delay between characters for LyX to process
        return success
    
    def insert_math(self, latex_code: str) -> bool:
        """Insert math expression at cursor position."""
        escaped = self._escape_for_lyx(latex_code)
        return self.send_command('math-insert', escaped)
    
    def delete_backward(self, count: int = 1) -> bool:
        """Delete characters backward."""
        import time
        for _ in range(count):
            # LFUN name from LyX Functions manual
            self.send_command('char-delete-backward')
            time.sleep(0.05)  # Small delay between deletes
        return True
    
    def delete_forward(self, count: int = 1) -> bool:
        """Delete characters forward."""
        for _ in range(count):
            # LFUN name from LyX Functions manual
            self.send_command('char-delete-forward')
        return True
    
    def get_buffer_content(self) -> Optional[str]:
        """
        Attempt to get the current buffer content.
        Note: This requires LyX to be set up to output the buffer.
        """
        try:
            # Request buffer info
            self.send_command('server-get-layout')
            
            # Try to read from output pipe
            if os.path.exists(self.pipe_out):
                with open(self.pipe_out, 'r') as pipe:
                    return pipe.read()
        except Exception as e:
            print(f"Error reading buffer: {e}")
        
        return None
    
    def _escape_for_lyx(self, text: str) -> str:
        """Prepare text for LyX command format.

        The LFUN syntax for self-insert/math-insert is:
            self-insert <STRING>
            math-insert <ARG>

        The server protocol uses ':' as a field separator in
        LYXCMD:<client>:<function>:<argument>. We currently avoid
        introducing extra quoting and just pass text through.
        """
        return text
    
    def is_lyx_running(self) -> bool:
        """Check if LyX server is accessible."""
        pipe_exists = os.path.exists(self.pipe_in)
        out_exists = os.path.exists(self.pipe_out)
        
        if not pipe_exists:
            print(f"[DEBUG] LyX input pipe not found at {self.pipe_in}")
            return False
        if not out_exists:
            print(f"[DEBUG] LyX output pipe not found at {self.pipe_out}")
            return False
        
        # Try to write a no-op to ensure LyX is responsive
        try:
            with open(self.pipe_in, 'a', encoding='utf-8') as pipe:
                pipe.write('')
                pipe.flush()
            return True
        except Exception as e:
            print(f"[DEBUG] Unable to access LyX pipe: {e}")
            return False
    
    def find_lyx_config_path(self) -> Optional[str]:
        """
        Auto-detect LyX config path by checking common locations.
        """
        possible_paths = [
            os.environ.get('LYX_HOME'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.5'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.4'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.3'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'LyX2.5'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'LyX2.4'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'LyX2.3'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'LyX'),
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                # Check if pipes exist or could exist
                return path
        
        return None


class LyXAutocompleteHelper:
    """Helper class to integrate autocomplete with LyX."""
    
    def __init__(self, lyx_client: Optional[LyXServerClient] = None):
        """Initialize the helper."""
        self.client = lyx_client or LyXServerClient()
    
    def apply_suggestion(self, prefix: str, suggestion: str, delete_prefix: bool = True) -> bool:
        """
        Apply a suggestion by:
        1. Deleting the typed prefix
        2. Inserting the suggestion
        
        Args:
            prefix: The text that was typed
            suggestion: The suggestion to insert
            delete_prefix: Whether to delete the prefix
            
        Returns:
            True if successful
        """
        try:
            if delete_prefix and prefix:
                # Delete the prefix
                if not self.client.delete_backward(len(prefix)):
                    print("[WARNING] Failed to delete prefix")
            
            # Small delay to ensure deletion is processed
            import time
            time.sleep(0.1)
            
            # Determine if it's a math expression (contains backslash)
            if '\\' in suggestion or '{' in suggestion or '^' in suggestion:
                print(f"[INFO] Inserting as LaTeX/Math: {suggestion}")
                return self.client.insert_math(suggestion)
            else:
                print(f"[INFO] Inserting as text: {suggestion}")
                return self.client.insert_text(suggestion)
        
        except Exception as e:
            print(f"[ERROR] Exception in apply_suggestion: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_ready(self) -> bool:
        """Check if LyX is running and accessible."""
        return self.client.is_lyx_running()


if __name__ == '__main__':
    # Test the client
    client = LyXServerClient()
    
    print(f"LyX config path: {client.lyx_home}")
    print(f"Is LyX running: {client.is_lyx_running()}")
    
    # If LyX is running, test basic commands
    if client.is_lyx_running():
        print("\nTesting text insertion...")
        client.insert_text("Hello, LyX!")
        
        print("Testing math insertion...")
        client.insert_math(r"\alpha")
