import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str | None = None):
    '''
    Configures and returns a logger with file rotations
    Logs are stored in logs/pipeline.log
    '''
    
    # We ensure log directory exists
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "pipeline.log")
    
    # We create a logger and set its level
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # Setting up my file handler
        file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
        
        # Setting up my date Formatter so it is human readable
        datefmt='%m/%d/%Y %I:%M:%S %p'
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt= datefmt
        )
        
        file_handler.setFormatter(formatter)
        
        # I only want to log warning levels and above to the log file
        file_handler.setLevel(logging.WARNING)
        logger.addHandler(file_handler)
        
        # Setting up my console_handler to print ot the terminal
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
    return logger