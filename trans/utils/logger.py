# trans/utils/logger.py
import logging
from rich.logging import RichHandler
from rich.console import Console

console = Console(color_system="256", style=None, force_terminal=True)

def setup_logger(name: str = "trans", level: int = logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_path=True,
        markup=True,
        show_time=True,
        show_level=True,
    )
    handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = setup_logger()