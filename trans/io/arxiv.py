# trans/io/arxiv.py
import arxiv
import os
import tarfile
from pathlib import Path
from trans.utils.logger import logger


def get_arxiv_id(url: str) -> str:
    """
    Extract arXiv ID from various URL formats or return the input if it's already an ID.

    Args:
        url (str): URL or arXiv ID in various formats

    Returns:
        str: Extracted arXiv ID
    """
    # Remove http/https protocol if present
    if url.startswith("https://"):
        url = url.lstrip("https://")
    elif url.startswith("http://"):
        url = url.lstrip("http://")

    # Remove www. prefix if present
    if url.startswith("www."):
        url = url.lstrip("www.")

    # Handle different arXiv URL formats
    if url.startswith("arxiv.org/abs/"):
        # Extract ID from abstract page URL (e.g., arxiv.org/abs/2101.00001)
        arxiv_id = url.lstrip("arxiv.org/abs/")
    elif url.startswith("arxiv.org/pdf/"):
        # Extract ID from PDF URL (e.g., arxiv.org/pdf/2101.00001.pdf) and remove .pdf extension
        arxiv_id = url.lstrip("arxiv.org/pdf/").replace(".pdf", "")
    else:
        # If it's not a URL format, assume it's already an arXiv ID
        arxiv_id = url

    return arxiv_id


def get_paper_title(arxiv_id: str) -> str:
    """
    Retrieve the title of an arXiv paper using its ID.

    Args:
        arxiv_id (str): arXiv paper ID

    Returns:
        str: Title of the arXiv paper
    """
    # Search for the paper using arXiv API and get the first result
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))
    return paper.title


def download_arxiv_project(url: str, output_dir: Path, use_cache: bool = True):
    """
    Download an arXiv paper's source files and extract them.

    Args:
        url (str): URL or arXiv ID of the paper to download
        output_dir (Path): Directory where the paper source will be downloaded
        use_cache (bool): Whether to use cached files if they exist (default: True)
    """
    # Extract arXiv ID from the provided URL
    arxiv_id = get_arxiv_id(url)
    logger.info(f"Downloading arXiv paper... arxiv_id: {arxiv_id}")

    # Get paper metadata using arXiv API
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))

    # Define path for the downloaded tar.gz source file
    tar_gz_path = output_dir / f"{arxiv_id}.tar.gz"

    # Check if cached file exists and cache usage is enabled
    if tar_gz_path.exists() and use_cache:
        logger.info(f"Found cached source file, skipping download...")
    else:
        # Download the source files as tar.gz archive
        paper.download_source(dirpath=output_dir, filename=f"{arxiv_id}.tar.gz")
        logger.info(f"Paper source downloaded successfully!")

    # Define extraction directory path
    source_path = output_dir / "source"
    # Create extraction directory if it doesn't exist
    source_path.mkdir(exist_ok=True)

    # Extract the downloaded tar.gz file to the source directory
    extract_tar_gz(tar_gz_path, source_path)


def extract_tar_gz(file_path: Path, extract_path: Path):
    """
    Extract a tar.gz archive to the specified directory.

    Args:
        file_path (Path): Path to the tar.gz file to extract
        extract_path (Path): Directory where the archive contents will be extracted
    """
    try:
        # Open the tar.gz file in read mode with gzip compression
        with tarfile.open(file_path, 'r:gz') as tar:
            # Extract all contents to the specified extraction path
            tar.extractall(path=extract_path)
            logger.info(f"File extracted to {extract_path} successfully")
    except Exception as e:
        # Log extraction error and re-raise the exception
        logger.error(f"Error extracting file: {e}")
        raise