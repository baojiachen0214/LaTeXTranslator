# trans/io/tex_loader.py
import os
from pathlib import Path
from typing import Dict
from trans.utils.logger import logger


def load_tex_file(file_path: Path) -> str:
    """
    Load and return the content of a .tex file with proper encoding handling.

    Args:
        file_path (Path): Path to the .tex file to load

    Returns:
        str: Content of the .tex file
    """
    try:
        # Try to open and read the file with UTF-8 encoding first
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # If UTF-8 fails, log a warning and try Latin-1 encoding as fallback
        logger.warning(f"UTF-8 decode failed for {file_path}, trying latin-1...")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    return content


def load_tex_project(project_dir: Path) -> Dict[str, str]:
    """
    Load all .tex files in a project directory and return them as a mapping.

    Args:
        project_dir (Path): Directory containing the LaTeX project files

    Returns:
        Dict[str, str]: Dictionary mapping relative file paths to their content
                       Format: {relative_path: file_content, ...}
    """
    # Initialize empty dictionary to store file paths and their contents
    project_map = {}

    # Walk through the project directory recursively
    for root, dirs, files in os.walk(project_dir):
        # Process each file in the current directory
        for file in files:
            # Check if the file has .tex extension
            if file.endswith('.tex'):
                # Create full path to the file
                full_path = Path(root) / file
                # Get relative path from the project directory root
                rel_path = full_path.relative_to(project_dir)
                # Load the content of the .tex file
                content = load_tex_file(full_path)
                # Add the file to the project map with relative path as key
                project_map[rel_path] = content

    return project_map