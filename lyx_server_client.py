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
            lyx_home: Path to LyX config directory. If None, uses default Windows path.
        """
        if lyx_home is None:
            # Default LyX config path on Windows
            lyx_home = os.path.join(
                os.environ.get('APPDATA', ''),
                'LyX2.5'  # Adjust version as needed
            )
        
        self.lyx_home = lyx_home
        self.pipe_in_base = os.path.join(lyx_home, 'lyxpipehhh')
        self.pipe_out_base = os.path.join(lyx_home, 'lyxpipeff')
        
        # Actual pipe paths for Windows named pipes
        self.pipe_in = f"\\\\.\\pipe\\{self.pipe_in_base}".replace('\\', '/')
        self.pipe_out = f"\\\\.\\pipe\\{self.pipe_out_base}".replace('\\', '/')
    
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
        try:
            # Format: LYXCMD:<client>:<function>:<argument>
            command = f"LYXCMD:{client}:{function}:{argument}\n"
            
            with open(self.pipe_in, 'w') as pipe:
                pipe.write(command)
                pipe.flush()
            
            return True
        except Exception as e:
            print(f"Error sending command to LyX: {e}")
            return False
    
    def insert_text(self, text: str) -> bool:
        """Insert text at cursor position."""
        # Escape special characters for LyX
        escaped = self._escape_for_lyx(text)
        return self.send_command('self-insert', escaped)
    
    def insert_math(self, latex_code: str) -> bool:
        """Insert math expression at cursor position."""
        escaped = self._escape_for_lyx(latex_code)
        return self.send_command('math-insert', escaped)
    
    def delete_backward(self, count: int = 1) -> bool:
        """Delete characters backward."""
        for _ in range(count):
            self.send_command('delete-backward-char')
        return True
    
    def delete_forward(self, count: int = 1) -> bool:
        """Delete characters forward."""
        for _ in range(count):
            self.send_command('delete-forward-char')
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
        """Escape special characters for LyX command format."""
        # Escape backslashes and quotes
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        return text
    
    def is_lyx_running(self) -> bool:
        """Check if LyX server is accessible."""
        try:
            # Try to open the pipe - this will exist if LyX is running
            with open(self.pipe_in, 'r') as _:
                return True
        except (FileNotFoundError, OSError):
            return False
    
    def find_lyx_config_path(self) -> Optional[str]:
        """
        Auto-detect LyX config path by checking common locations.
        """
        possible_paths = [
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.5'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.4'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX2.3'),
            os.path.join(os.environ.get('APPDATA', ''), 'LyX'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
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
        if delete_prefix and prefix:
            # Delete the prefix
            self.client.delete_backward(len(prefix))
        
        # Determine if it's a math expression (contains backslash)
        if '\\' in suggestion or '{' in suggestion or '^' in suggestion:
            return self.client.insert_math(suggestion)
        else:
            return self.client.insert_text(suggestion)
    
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
