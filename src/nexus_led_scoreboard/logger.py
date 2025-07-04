import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(
    console_level: str = 'INFO',
    file_level: str = 'DEBUG',
    log_file_path: str = None
) -> None:
    """
    Sets up the application-wide logging configuration.

    Args:
        console_level (str): Logging level for console output (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR').
        file_level (str): Logging level for file output.
        log_file_path (str, optional): Full path to the log file. If None, defaults to 'logs/application.log'.
    """
    # Ensure the root logger is clean before configuring
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.root.setLevel(logging.DEBUG) # Set root to DEBUG to capture all messages

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    # --- File Handler (Rotating) ---
    if log_file_path is None:
        # Determine project root dynamically
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, 'application.log')

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10485760, # 10 MB
        backupCount=5,     # Keep 5 backup logs
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

    # Example usage after setup_logging:
    # logger = logging.getLogger(__name__)
    # logger.debug("This is a debug message")
    # logger.info("This is an info message")