# trans/cli.py
import typer
from pathlib import Path
import os
from trans.config import load_config, get_config
from trans.core.translator import TexTranslator
from trans.io.arxiv import download_arxiv_project
from trans.io.tex_loader import load_tex_file, load_tex_project
from trans.io.writer import write_tex_file, write_tex_project
from trans.build.compiler import compile_project
from trans.utils.logger import logger
import asyncio
import shutil

# Initialize the Typer CLI application
app = typer.Typer()


@app.command()
def main(
        config_file: Path = typer.Option("config.yaml", "--config", "-c", help="Path to config.yaml"),
):
    """
    Run TransGPTex with a YAML config file.

    Args:
        config_file (Path): Path to the configuration file (default: config.yaml)
    """
    # Check if config file exists
    if not config_file.exists():
        typer.echo(f"Config file not found: {config_file}. Please create one based on config.example.yaml", err=True)
        raise typer.Exit(code=1)

    try:
        # Load configuration from the specified file
        load_config(config_file)
    except ValueError as e:
        # Handle configuration loading errors
        typer.echo(f"Configuration error: {e}", err=True)
        raise typer.Exit(code=1)

    # Get loaded configuration
    cfg = get_config()
    # Create output directory with parent directories if needed
    output_dir = Path(cfg.output.dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle different operation modes
    if cfg.mode == "arxiv":
        # ArXiv mode: download paper from arXiv, translate, and optionally compile
        source_dir = output_dir / "source"
        translated_dir = output_dir / "translated_source"
        logger.info(f"Mode: arxiv. Downloading from {cfg.input.url}")
        # Download arXiv paper source files
        download_arxiv_project(cfg.input.url, source_dir, use_cache=True)  # Add cache option if needed
        logger.info("Download complete. Starting translation...")
        # Translate the downloaded project
        asyncio.run(translate_project(source_dir, translated_dir))
        # Compile the translated project if compilation is enabled
        if cfg.output.compile:
            compile_project(translated_dir, output_dir / f"translated_paper.pdf")

    elif cfg.mode == "single":
        # Single file mode: translate a single .tex file
        input_path = Path(cfg.input.path)
        output_path = output_dir / input_path.name
        logger.info(f"Mode: single. Translating file {input_path}")
        # Load the content of the single file
        content = load_tex_file(input_path)
        # Initialize translator
        translator = TexTranslator()
        # Translate the content
        translated_content = asyncio.run(translator.translate_content(content))
        # Write the translated content to output file
        write_tex_file(output_path, translated_content)
        # Compile the single file if compilation is enabled
        if cfg.output.compile:
            import subprocess
            try:
                # Run xelatex to compile the single file
                subprocess.run(['xelatex', '-interaction=nonstopmode', output_path.name], cwd=output_path.parent,
                               check=True)
                logger.info(f"Single file compiled to {output_path.with_suffix('.pdf')}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to compile single file: {e}")

    elif cfg.mode == "project":
        # Project mode: translate an entire LaTeX project directory
        input_dir = Path(cfg.input.dir)
        translated_dir = output_dir / "translated_project"
        logger.info(f"Mode: project. Translating project {input_dir}")
        # Load all .tex files from the project directory
        project_map = load_tex_project(input_dir)
        # Initialize translator
        translator = TexTranslator()
        # Dictionary to store translated content
        translated_map = {}
        # Translate each file in the project
        for rel_path, content in project_map.items():
            logger.info(f"Translating {rel_path}...")
            translated_content = asyncio.run(translator.translate_content(content))
            translated_map[rel_path] = translated_content
        # Write all translated files to the output directory
        write_tex_project(translated_dir, translated_map)
        # Copy non-tex files (images, bibliography, etc.) to preserve project structure
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                src_file = Path(root) / file
                if src_file.suffix != '.tex':
                    # Calculate relative path from input directory
                    rel_file = src_file.relative_to(input_dir)
                    # Create destination path in translated directory
                    dst_file = translated_dir / rel_file
                    # Create parent directories if they don't exist
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    # Copy file with metadata preservation
                    shutil.copy2(src_file, dst_file)
        # Compile the entire translated project if compilation is enabled
        if cfg.output.compile:
            compile_project(translated_dir, output_dir / f"translated_project.pdf")


async def translate_project(source_dir: Path, translated_dir: Path):
    """
    Translate all .tex files in a project directory.

    Args:
        source_dir (Path): Directory containing the source LaTeX project
        translated_dir (Path): Directory where translated files will be written
    """
    # Load all .tex files from the source directory
    project_map = load_tex_project(source_dir)
    # Initialize the translator
    translator = TexTranslator()
    # Dictionary to store translated content
    translated_map = {}
    # Process each file in the project
    for rel_path, content in project_map.items():
        logger.info(f"Translating {rel_path}...")
        # Translate the content of each file
        translated_content = await translator.translate_content(content)
        # Store the translated content
        translated_map[rel_path] = translated_content
    # Write all translated files to the output directory
    write_tex_project(translated_dir, translated_map)


if __name__ == "__main__":
    # Run the CLI application
    app()