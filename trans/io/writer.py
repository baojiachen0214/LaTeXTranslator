# trans/io/writer.py
from pathlib import Path
from typing import Dict
from trans.utils.logger import logger


def write_tex_file(file_path: Path, content: str):
    """
    Write content to a .tex file with proper directory creation.

    Args:
        file_path (Path): Path where the .tex file will be written
        content (str): Content to write to the file
    """
    # Create parent directories if they don't exist (including intermediate directories)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the content to the file with UTF-8 encoding
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Log successful file write operation
    logger.info(f"Written file: {file_path}")


def write_tex_project(output_dir: Path, project_map: Dict[str, str]):
    """
    Write all files in a LaTeX project from a mapping dictionary.

    Args:
        output_dir (Path): Base directory where the project will be written
        project_map (Dict[str, str]): Dictionary mapping relative file paths to their content
                                    Format: {relative_path: file_content, ...}
    """
    # Iterate through each file path and content in the project map
    for rel_path, content in project_map.items():
        # Create full output path by combining base directory with relative path
        full_output_path = output_dir / rel_path
        # Write the individual file with its content
        write_tex_file(full_output_path, content)