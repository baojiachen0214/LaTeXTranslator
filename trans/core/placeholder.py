import re
import uuid
from typing import Dict, List, NamedTuple, Pattern


class Placeholder(NamedTuple):
    """
    A named tuple to store placeholder information.

    Attributes:
        id (str): Unique identifier for the placeholder
        content (str): Original content that was replaced
        type (str): Type classification of the content (e.g., equation, citation, reference, etc.)
    """
    id: str
    content: str
    type: str


class PlaceholderManager:
    """
    A manager class for handling text placeholders during preprocessing and postprocessing.
    This class allows temporarily replacing sensitive content (like equations, citations, 
    verbatim text) with unique placeholders, and later restoring the original content.
    """

    def __init__(self):
        """
        Initialize the PlaceholderManager with empty storage structures.
        """
        # Dictionary mapping placeholder IDs to Placeholder objects
        self.placeholders: Dict[str, Placeholder] = {}
        # Reverse mapping from content to placeholder ID (for quick lookup)
        self.reverse_map: Dict[str, str] = {}
        # Counter for generating unique IDs (not currently used, but available for future use)
        self._counter = 0

    def _make_id(self, ptype: str) -> str:
        """
        Generate a unique placeholder ID based on the content type.

        Args:
            ptype (str): Type of the content being protected

        Returns:
            str: Unique placeholder ID in the format __TGTEX_TYPE_XXXXXXXX__
        """
        # Extract first 3 characters of type and convert to uppercase
        suffix = (ptype or "UNK")[:3].upper()
        # Generate UUID and take first 8 characters, convert to uppercase
        return f"__TGTEX_{suffix}_{uuid.uuid4().hex[:8].upper()}__"

    def add(self, content: str, ptype: str = "unknown") -> str:
        """
        Add content to the placeholder storage and return its unique ID.

        Args:
            content (str): The content to be stored as a placeholder
            ptype (str): Type classification of the content (default: "unknown")

        Returns:
            str: The unique placeholder ID
        """
        # Generate unique ID for this content
        ph_id = self._make_id(ptype)
        # Store the placeholder with its metadata
        self.placeholders[ph_id] = Placeholder(ph_id, content, ptype)
        # Add reverse mapping for quick lookup
        self.reverse_map[content] = ph_id
        return ph_id

    def replace_in_text(self, text: str, patterns: List[re.Pattern], max_protect_len: int = 2000) -> str:
        """
        Replace matched content in text with placeholders, avoiding over-protection of large sections.

        Args:
            text (str): Input text to process
            patterns (List[re.Pattern]): List of regex patterns to match protected content
            max_protect_len (int): Maximum length of content to protect (default: 2000)

        Returns:
            str: Text with matched content replaced by placeholders
        """
        # Sort patterns by length (descending) to avoid partial replacements
        # Longer patterns should be processed first to avoid shorter patterns matching within longer ones
        sorted_patterns = sorted(patterns, key=lambda p: len(p.pattern), reverse=True)

        for pat in sorted_patterns:
            def repl(match):
                """
                Replacement function called for each regex match.

                Args:
                    match: Regex match object

                Returns:
                    str: Placeholder ID if content is valid length, otherwise original content
                """
                content = match.group(0)

                # If match is very large, skip protection to avoid protecting too much content
                if len(content) > max_protect_len:
                    # Don't replace, return original content to avoid over-protection
                    return content

                # Determine placeholder type based on content patterns
                ptype = "unknown"
                # Still use previous logic to determine type
                if r"\begin{equation" in content or r"\begin{align" in content:
                    ptype = "EQU"  # Equation environment
                elif r"\cite" in content:
                    ptype = "CIT"  # Citation command
                elif r"\ref" in content:
                    ptype = "REF"  # Reference command
                elif r"\url" in content or r"\href" in content:
                    ptype = "URL"  # URL/Hyperlink command
                elif r"\begin{verbatim" in content or r"\begin{lstlisting" in content:
                    ptype = "VER"  # Verbatim/listing environment
                elif r"\usepackage" in content or r"\documentclass" in content:
                    ptype = "CMD"  # Package/class command

                # Add the content to placeholder storage and get its ID
                ph_id = self.add(content, ptype)
                return ph_id

            # Apply the replacement function to all matches of current pattern
            text = pat.sub(repl, text)

        return text

    def restore(self, text: str) -> str:
        """
        Restore original content by replacing placeholders with their original content.

        Args:
            text (str): Text containing placeholders to be restored

        Returns:
            str: Text with placeholders replaced by original content
        """
        # Sort placeholders by ID length (descending) to avoid partial replacements
        # Longer IDs should be processed first to avoid shorter IDs matching within longer ones
        sorted_items = sorted(self.placeholders.items(), key=lambda item: len(item[0]), reverse=True)

        for ph_id, ph_obj in sorted_items:
            # Replace each placeholder ID with its original content
            text = text.replace(ph_id, ph_obj.content)

        return text


# List of regex patterns for content that should be protected during processing
# These patterns match LaTeX structures that should not be modified during translation
PROTECTED_PATTERNS = [
    # Equation environments (with and without star for unnumbered)
    re.compile(r"\\begin{equation\*?}.*?\\end{equation\*?}", re.DOTALL),
    # Align environments (with and without star for unnumbered)
    re.compile(r"\\begin{align\*?}.*?\\end{align\*?}", re.DOTALL),
    # Theorem environments (with and without star)
    re.compile(r"\\begin{theorem\*?}.*?\\end{theorem\*?}", re.DOTALL),
    # Proof environments (with and without star)
    re.compile(r"\\begin{proof\*?}.*?\\end{proof\*?}", re.DOTALL),
    # Figure environments (with and without star)
    re.compile(r"\\begin{figure\*?}.*?\\end{figure\*?}", re.DOTALL),
    # Table environments (with and without star)
    re.compile(r"\\begin{table\*?}.*?\\end{table\*?}", re.DOTALL),
    # Itemize environments (with and without star)
    re.compile(r"\\begin{itemize\*?}.*?\\end{itemize\*?}", re.DOTALL),
    # Enumerate environments (with and without star)
    re.compile(r"\\begin{enumerate\*?}.*?\\end{enumerate\*?}", re.DOTALL),
    # Citation commands
    re.compile(r"\\cite\{.*?\}"),
    # Reference commands
    re.compile(r"\\ref\{.*?\}"),
    # Label commands
    re.compile(r"\\label\{.*?\}"),
    # URL commands
    re.compile(r"\\url\{.*?\}"),
    # Hyperlink commands
    re.compile(r"\\href\{.*?\}\{.*?\}"),
    # Verbatim environments (multiline, using DOTALL flag)
    re.compile(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", re.DOTALL),
    # Lstlisting environments (multiline, using DOTALL flag) - Added lstlisting
    re.compile(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", re.DOTALL),
]