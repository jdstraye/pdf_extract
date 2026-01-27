"""
Helper functions common throughout the PreAuth ML model-making project.
"""
""" 
Creates a custom log handler that creates a fresh log file with a date in the name but also creates a symlink to the latest log file.
"""
import logging
import re
import pandas as pd
from typing import List, Tuple, Union, Sequence, Dict
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import os
import sys
import colorsys
# Minimum saturation threshold used by color classification heuristics
SPAN_SAT_MIN = 0.05

# --------------------------
# Global Setup: Constants, Paths, & Logging
# --------------------------
class GlobalConfig:
    def __init__(self):
        # Constants
        ## Random Seed
        self.RANDOM_STATE = 42

        ## Number multiplier to define how many samples to try (heuristic, per-model)
        self.RANDOM_SEARCH_ITER_MULT = 0.1

        ## Defaults for SMOTE sanity check (minimum delta in minority share after resampling)
        self.DEFAULT_SMOTE_MIN_IMPROVEMENT = 0.01

        ## Logging Levels
        self.DEBUG_MODE = True  # Set to False to disable debug checks and critical error raising
        self.FILE_LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARN, ERROR, CRITICAL
        self.CONSOLE_LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARN, ERROR, CRITICAL
#        self.CONSOLE_LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARN, ERROR, CRITICAL

        # Paths
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.LOG_DIR = self.BASE_DIR / "logs"
        self.MODELS_DIR = self.BASE_DIR / "models"
        self.REPORTS_DIR = self.LOG_DIR / "reports"
        self.PROBA_DIR = self.LOG_DIR / "proba"
        self.DEFAULT_SCHEMA_PATH = Path("src/column_headers.json")

        ## Path Setup
        for d in [self.LOG_DIR, self.MODELS_DIR, self.REPORTS_DIR, self.PROBA_DIR]:
            d.mkdir(parents=True, exist_ok=True)

gv = GlobalConfig()

# --- Custom Log Handler & Logging Setup (from previous code) ---
class CustomRotatingFileHandler(RotatingFileHandler):
    """
    A custom rotating file handler that appends a timestamp to the log file name.
    """
    def __init__(self, filename, maxBytes, backupCount):
        self.base_filename = Path(filename).stem
        self.base_dir = Path(filename).absolute().parent
        self.current_datetime = datetime.now().strftime("%Y%m%d.%H%M")
        self.baseFilename = str(self.base_dir / f"{self.base_filename}-{self.current_datetime}.log")
        super().__init__(self.baseFilename, maxBytes=maxBytes, backupCount=backupCount)
        self.latest_log_path = self.base_dir / f"{self.base_filename}_latest.log"
        if self.latest_log_path.exists() or self.latest_log_path.is_symlink():
            self.latest_log_path.unlink()
        self.latest_log_path.symlink_to(Path(self.baseFilename).relative_to(self.base_dir))

    def doRollover(self):
        """
        Modified rollover to handle the timestamped log file names correctly.
        """
        if self.stream:
            self.stream.close()
        current_datetime = datetime.now().strftime("%Y%m%d.%H%M")
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.base_dir}/{self.base_filename}-{current_datetime}.{i}.log"
                dfn = f"{self.base_dir}/{self.base_filename}-{current_datetime}.{i + 1}.log"
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = f"{self.base_dir}/{self.base_filename}-{current_datetime}.1.log"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)
        self.baseFilename = f"{self.base_dir}/{self.base_filename}-{current_datetime}.log"
        self.stream = open(self.baseFilename, 'w')



# --- Logging ---
def debug_setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
        ]
    )

def setup_logging(log_file: Path):
    """
    Modifies the root logger to setup a rotating file handler and a console handler for logging. 
    It needs to be called once at the start of the program to setup 
    the file location and log levels.

    Args:
        log_file (Path): The path to the log file.

    After that initial call, it can be used by just calling
     logger = logging.getLogger(__name__)
    as usual to get a logger in that module.
    The file handler also creates/updates a symlink to the latest log file.
    The log levels for file and console are set in utils.py as part of the GlobalConfig class,
    FILE_LOG_LEVEL and CONSOLE_LOG_LEVEL.
    """
    
    print("DEBUG: setup_logging() was called!")  # <-- Add this

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clean up existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Prepare formatters
    file_formatter = logging.Formatter('%(filename)s:%(lineno)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s')

    # Valid log levels
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # File handler
    ## Check if a file handler for this log_file already exists
    file_handler_exists = any(
        isinstance(h, CustomRotatingFileHandler) and h.baseFilename == str(log_file)
        for h in root_logger.handlers
    )
    if not file_handler_exists:
        file_handler = CustomRotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_level = gv.FILE_LOG_LEVEL.upper()
        if file_level not in valid_levels:
            raise ValueError(f"Invalid file log level: {gv.FILE_LOG_LEVEL}. Must be one of {valid_levels}")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    ## Check if a console handler already exists
    console_handler = None
    console_handler_exists = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers
        #isinstance(type(h), logging.StreamHandler) for h in root_logger.handlers
    )
    print(f"DEBUG: {console_handler_exists = }, {root_logger.handlers = }")  # <-- Add this
    print("DEBUG: root_logger.handlers = [")
    for i, handler in enumerate(root_logger.handlers):
        print(f"  {i}: {type(handler).__name__} - {handler}")
    print("]")

    if not console_handler_exists:
        console_handler = logging.StreamHandler()
        console_level = gv.CONSOLE_LOG_LEVEL.upper()
        if console_level not in valid_levels:
            raise ValueError(f"Invalid console log level: {gv.CONSOLE_LOG_LEVEL}. Must be one of {valid_levels}")
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        print(f"DEBUG: Logging configured for: {log_file}")  # <-- Add this

# Picklable get_logger for every class/module
def get_logger(name: str) -> logging.Logger:
    """
    Centralized logger setup for all classes. Unlike setup_logging(), this can be 
    pickled because it does not use a FileHandler or store the Logger object on 
    the instance.
    Args:
        name: Logger name (e.g., f"{__name__}.{ClassName}").
    Returns:
        logging.Logger: Configured logger with handlers.
    """
    lg = logging.getLogger(name)
    if lg.level == logging.NOTSET:
        lg.setLevel(gv.CONSOLE_LOG_LEVEL.upper())
    lg.propagate = False

    # Attach handlers if missing
    if not lg.handlers:
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        if ch.level == logging.NOTSET:
            ch.setLevel(gv.CONSOLE_LOG_LEVEL.upper())
        ch.setFormatter(logging.Formatter(
            "%(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s"
        ))
        lg.addHandler(ch)

    return lg

logger = logging.getLogger(__name__)

def load_column_headers(column_headers_json: Path, df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Loads feature, categorical, and target column names from a JSON schema file
    and validates that feature columns exist in the DataFrame.

    Args:
        column_headers_json (Path): Path to the JSON file containing column definitions.
        df (pd.DataFrame): The DataFrame to check for column existence.

    Returns:
        Dict:
            "feature_cols": List of sanitized names for feature columns ('X' == 'True').
            "categorical_cols": List of names for categorical columns ('categorical' == 'True').
            "target_cols": List of names for target columns ('Y' == 'True').
            "ohe_cols": List of names for columns that are one-hot encoded ('ohe_from' exists).
    ... (rest unchanged)