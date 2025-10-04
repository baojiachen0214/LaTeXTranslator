import re
from typing import List


class ContextAwareChunker:
    """
    A context-aware text chunker that splits LaTeX documents into chunks while preserving structural boundaries.
    This chunker prioritizes splitting at semantic boundaries like chapters, sections, equations, etc.,
    to maintain document structure and context.
    """

    def __init__(self, chunk_size: int, overlap: int = 100):
        """
        Initialize the ContextAwareChunker with specified chunk size and overlap.

        Args:
            chunk_size (int): Maximum size of each chunk in characters
            overlap (int): Number of overlapping characters between consecutive chunks (default: 100)
        """
        self.chunk_size = chunk_size  # Maximum allowed chunk size
        self.overlap = overlap  # Overlap size between chunks
        # List of separators in order of priority for splitting
        # Prioritize structural elements first (chapters, sections) then content elements
        self.separators = [
            "\n\\chapter{",  # Chapter start (highest priority)
            "\n\\section{",  # Section start
            "\n\\subsection{",  # Subsection start
            "\n\\subsubsection{",  # Subsubsection start
            "\n\\begin{enumerate}",  # Enumerate environment start
            "\n\\begin{itemize}",  # Itemize environment start
            "\n\\begin{description}",  # Description environment start
            "\n\\begin{quote}",  # Quote environment start
            "\n\\begin{quotation}",  # Quotation environment start
            "\n\\begin{verse}",  # Verse environment start
            "\n\\begin{verbatim}",  # Verbatim environment start
            "\n\\begin{align}",  # Align environment start
            "\n\\begin{equation}",  # Equation environment start
            "\n\n",  # Double newline (paragraph break)
            "\n$$",  # Display math start
            ". ",  # Sentence end followed by space
            ", ",  # Comma followed by space
            "; ",  # Semicolon followed by space
            ":\n"  # Colon followed by newline
        ]

    def _split_once(self, text: str, sep: str, K: int) -> List[str]:
        """
        Split a text chunk using a specific separator while respecting the maximum chunk size K.

        Args:
            text (str): The text to be split
            sep (str): The separator to use for splitting
            K (int): Maximum allowed chunk size

        Returns:
            List[str]: List of text chunks after splitting
        """
        # Split the text using the given separator
        parts = text.split(sep)

        # If there's only one part (no splits occurred), return the original text
        if len(parts) == 1:
            return [text]

        # List to store the new split parts
        new_parts = []
        # Current accumulated chunk
        current = ""

        # Iterate through each part from the split
        for i, part in enumerate(parts):
            # Add the separator back to each part except the first one
            piece = (sep if i > 0 else "") + part

            # Check if adding this piece would exceed the chunk size limit
            if len(current) + len(piece) <= K:
                # If not exceeding, add the piece to current chunk
                current += piece
            else:
                # If adding would exceed, save current chunk and start new one
                if current:
                    new_parts.append(current)
                current = piece  # Start new chunk with current piece

        # Add the final accumulated chunk if it's not empty
        if current:
            new_parts.append(current)

        return new_parts

    def split(self, text: str) -> List[str]:
        """
        Split the input text into chunks based on separators and size constraints.

        Args:
            text (str): The input text to be chunked

        Returns:
            List[str]: List of text chunks
        """
        # Start with the entire text as one chunk
        chunks = [text]

        # Process each separator in order of priority
        for sep in self.separators:
            new_chunks = []  # Temporary list for new chunks

            # Process each existing chunk
            for chunk in chunks:
                # If chunk is already within size limit, keep it as is
                if len(chunk) <= self.chunk_size:
                    new_chunks.append(chunk)
                else:
                    # If chunk is too large, try to split it using current separator
                    parts = self._split_once(chunk, sep, self.chunk_size)
                    new_chunks.extend(parts)  # Add split parts to new chunks

            # Update chunks with the newly processed chunks
            chunks = new_chunks

        # Apply overlap between chunks if overlap is specified and there are multiple chunks
        if self.overlap > 0 and len(chunks) > 1:
            overlapped = []  # List to store chunks with overlap

            # Process each chunk with overlap consideration
            for i, chunk in enumerate(chunks):
                if i == 0:
                    # First chunk: no overlap needed, add as is
                    overlapped.append(chunk)
                else:
                    # Get the last 'overlap' characters from previous chunk
                    prev_end = chunks[i - 1][-self.overlap:]
                    # Combine previous overlap with current chunk
                    overlapped.append(prev_end + chunk)

            return overlapped

        # Return chunks without overlap if overlap is not needed
        return chunks