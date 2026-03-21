"""
LyX Autocomplete Engine - Provides text and math suggestions
"""

import re
from typing import List, Tuple, Set

# Math symbols and expressions
MATH_COMPLETIONS = {
    'sum': r'\sum',
    'prod': r'\prod',
    'int': r'\int',
    'frac': r'\frac{}{}',
    'sqrt': r'\sqrt{}',
    'alpha': r'\alpha',
    'beta': r'\beta',
    'gamma': r'\gamma',
    'delta': r'\delta',
    'epsilon': r'\epsilon',
    'lambda': r'\lambda',
    'mu': r'\mu',
    'pi': r'\pi',
    'sigma': r'\sigma',
    'tau': r'\tau',
    'phi': r'\phi',
    'psi': r'\psi',
    'omega': r'\omega',
    'infty': r'\infty',
    'leq': r'\leq',
    'geq': r'\geq',
    'neq': r'\neq',
    'approx': r'\approx',
    'equiv': r'\equiv',
    'propto': r'\propto',
    'leftarrow': r'\leftarrow',
    'rightarrow': r'\rightarrow',
    'leftrightarrow': r'\leftrightarrow',
    'Leftarrow': r'\Leftarrow',
    'Rightarrow': r'\Rightarrow',
    'cdot': r'\cdot',
    'times': r'\times',
    'div': r'\div',
    'pm': r'\pm',
    'mp': r'\mp',
    'exists': r'\exists',
    'forall': r'\forall',
    'partial': r'\partial',
    'nabla': r'\nabla',
    'dagger': r'\dagger',
    'dagger': r'\dagger',
    'star': r'\star',
    'ast': r'\ast',
    'circ': r'\circ',
}

# Common text completions
TEXT_COMPLETIONS = {
    'teh': 'the',
    'taht': 'that',
    'waht': 'what',
    'whcih': 'which',
    'thier': 'their',
    'becuase': 'because',
    'recieve': 'receive',
    'occured': 'occurred',
    'occassion': 'occasion',
    'existance': 'existence',
    'seperete': 'separate',
    'wich': 'which',
    'woudl': 'would',
    'shoudl': 'should',
    'coudl': 'could',
    'alot': 'a lot',
    'dont': "don't",
    'didnt': "didn't",
    'shouldnt': "shouldn't",
}

# Common English words for context-aware suggestions
COMMON_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
    'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
    'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
    'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
    'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
    'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
    'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
    'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'being', 'has', 'had',
    'where', 'why', 'equation', 'function', 'theorem', 'proof', 'definition',
    'example', 'note', 'section', 'chapter', 'figure', 'table', 'reference',
}

# Common LaTeX environments
LATEX_ENVIRONMENTS = {
    'equation': (r'\begin{equation}', r'\end{equation}'),
    'align': (r'\begin{align}', r'\end{align}'),
    'align*': (r'\begin{align*}', r'\end{align*}'),
    'gather': (r'\begin{gather}', r'\end{gather}'),
    'itemize': (r'\begin{itemize}', r'\end{itemize}'),
    'enumerate': (r'\begin{enumerate}', r'\end{enumerate}'),
}


class AutocompleteEngine:
    """Provides intelligent text and math completions for LyX documents."""
    
    def __init__(self):
        self.math_completions = MATH_COMPLETIONS
        self.text_completions = TEXT_COMPLETIONS
        self.common_words = COMMON_WORDS
        self.latex_environments = LATEX_ENVIRONMENTS
    
    def get_suggestions(self, prefix: str, context: str = "", in_math_mode: bool = False) -> List[Tuple[str, str]]:
        """
        Get autocomplete suggestions for a given prefix.
        
        Args:
            prefix: The text to match against
            context: Surrounding text context (last ~50 chars)
            in_math_mode: Whether cursor is in math mode
            
        Returns:
            List of (display_text, replacement_text) tuples, sorted by relevance
        """
        if not prefix or len(prefix) < 1:
            return []
        
        suggestions = []
        
        # Check if we're in math mode or should suggest math
        if in_math_mode or self._looks_like_math_prefix(prefix, context):
            suggestions.extend(self._get_math_suggestions(prefix))
        else:
            suggestions.extend(self._get_text_suggestions(prefix))
            suggestions.extend(self._get_latex_environment_suggestions(prefix))
        
        # Deduplicate and sort by relevance (exact prefix match first)
        seen = set()
        unique_suggestions = []
        for display, replacement in suggestions:
            if replacement not in seen:
                seen.add(replacement)
                unique_suggestions.append((display, replacement))
        
        # Sort: exact match first, then by match position, then by length
        def sort_key(item):
            display, replacement = item
            is_exact = display.lower() == prefix.lower()
            starts_with = display.lower().startswith(prefix.lower())
            contains = prefix.lower() in display.lower()
            return (not is_exact, not starts_with, not contains, len(display))
        
        unique_suggestions.sort(key=sort_key)
        return unique_suggestions[:10]  # Return top 10
    
    def _get_math_suggestions(self, prefix: str) -> List[Tuple[str, str]]:
        """Get math symbol and expression suggestions."""
        prefix_lower = prefix.lower()
        suggestions = []
        
        for key, latex_code in self.math_completions.items():
            if key.startswith(prefix_lower):
                # Display shows the key, replacement is the LaTeX
                # Use ASCII-compatible arrow instead of →
                suggestions.append((f"${key}$ => {latex_code}", latex_code))
        
        return suggestions
    
    def _get_text_suggestions(self, prefix: str) -> List[Tuple[str, str]]:
        """Get text and spell-check suggestions."""
        prefix_lower = prefix.lower()
        suggestions = []
        
        # Check for spelling corrections
        if prefix_lower in self.text_completions:
            correct = self.text_completions[prefix_lower]
            suggestions.append((f"{prefix} => {correct} (typo fix)", correct))
        
        # Check for word completions from common words
        for word in self.common_words:
            if word.startswith(prefix_lower) and word != prefix_lower:
                suggestions.append((word, word))
        
        return suggestions
    
    def _get_latex_environment_suggestions(self, prefix: str) -> List[Tuple[str, str]]:
        """Get LaTeX environment suggestions."""
        prefix_lower = prefix.lower()
        suggestions = []
        
        for env_name, (begin, end) in self.latex_environments.items():
            if env_name.startswith(prefix_lower):
                # For environments, suggest the full template
                template = f"\\begin{{{env_name}}}\n\n\\end{{{env_name}}}"
                suggestions.append((f"env: {env_name}", template))
        
        return suggestions
    
    def _looks_like_math_prefix(self, prefix: str, context: str = "") -> bool:
        """Heuristic to detect if prefix is likely a math expression."""
        # If it starts with common math prefixes or contains backslash
        math_prefixes = ('sum', 'int', 'frac', 'sqrt', 'alpha', 'beta', 'gamma',
                        'prod', 'delta', 'epsilon', 'lambda', 'mu', 'pi', 'sigma')
        
        if prefix.lower() in math_prefixes or prefix.startswith('\\'):
            return True
        
        # Check context for math mode indicators
        math_indicators = ['$', r'\[', r'\(', 'equation', 'align', 'math']
        context_has_math = any(indicator in context for indicator in math_indicators)
        
        return context_has_math and any(c.isalpha() for c in prefix)
    
    def get_at_word_boundary(self, full_text: str, cursor_pos: int) -> Tuple[str, str, bool]:
        """
        Extract the current word/prefix at cursor position for autocompletion.
        
        Returns:
            (prefix_to_complete, surrounding_context, in_math_mode)
        """
        if cursor_pos > len(full_text):
            cursor_pos = len(full_text)
        
        # Find word boundaries (alphanumeric + backslash)
        start = cursor_pos - 1
        while start >= 0 and (full_text[start].isalnum() or full_text[start] == '\\' or full_text[start] == '_'):
            start -= 1
        start += 1
        
        prefix = full_text[start:cursor_pos]
        
        # Get surrounding context (50 chars before and after)
        context_start = max(0, cursor_pos - 50)
        context = full_text[context_start:min(len(full_text), cursor_pos + 50)]
        
        # Detect if in math mode
        in_math = self._is_in_math_mode(full_text, cursor_pos)
        
        return prefix, context, in_math
    
    def _is_in_math_mode(self, text: str, cursor_pos: int) -> bool:
        """Check if cursor is within math mode delimiters."""
        # Count unescaped $ symbols before cursor
        dollar_count = 0
        i = 0
        while i < cursor_pos:
            if text[i] == '$':
                if i == 0 or text[i-1] != '\\':
                    dollar_count += 1
            i += 1
        
        # Odd number means we're in math mode
        return dollar_count % 2 == 1


if __name__ == '__main__':
    # Test the engine
    engine = AutocompleteEngine()
    
    # Test math suggestions
    print("Math suggestions for 'sum':")
    for display, replacement in engine.get_suggestions('sum', in_math_mode=True):
        print(f"  {display} -> {replacement}")
    
    print("\nText suggestions for 'the':")
    for display, replacement in engine.get_suggestions('the'):
        print(f"  {display} -> {replacement}")
    
    print("\nText suggestions for 'teh':")
    for display, replacement in engine.get_suggestions('teh'):
        print(f"  {display} -> {replacement}")
    
    # Test word extraction
    text = "This is an equation $x = a + b$ and more text."
    prefix, context, in_math = engine.get_at_word_boundary(text, len(text) - 10)
    print(f"\nWord extraction test:")
    print(f"  Prefix: '{prefix}'")
    print(f"  In math mode: {in_math}")
