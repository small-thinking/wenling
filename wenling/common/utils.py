from typing import Any, Dict, List, Optional
from datetime import datetime
import pytz
import inspect
import logging
from colorama import Fore, ansi
import threading
import requests  # type: ignore
from dotenv import load_dotenv  # type: ignore


def load_env(env_file_path: str = "") -> None:
    if env_file_path:
        load_env(env_file_path)
    else:
        load_dotenv()


def get_datetime(timestamp: Optional[float] = None) -> str:
    """Convert the timestamp to datetime string.

    Args:
        timestamp (float): The timestamp to convert.

    Returns:
        str: The datetime string.
    """
    timezone = pytz.timezone("Etc/GMT+8")
    if not timestamp:
        timestamp = datetime.now().timestamp()
    return datetime.fromtimestamp(timestamp, timezone).strftime("%Y-%m-%d %H:%M:%S")


def check_url_exists(url):
    try:
        response = requests.head(url)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

# Create a logger class that accept level setting.
# The logger should be able to log to stdout and display the datetime, caller, and line of code.
class Logger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, logger_name: str, verbose: bool = True, level: Any = logging.INFO
    ):
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(logger_name)
            self.verbose = verbose
            self.logger.setLevel(level=level)
            self.formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s (%(filename)s:%(lineno)d)"
            )
            self.console_handler = logging.StreamHandler()
            self.console_handler.setLevel(level=level)
            self.console_handler.setFormatter(self.formatter)
            self.logger.addHandler(self.console_handler)

    def output(self, message: str, color: str = ansi.Fore.GREEN) -> None:
        print(color + message + Fore.RESET)

    def debug(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.debug(
            Fore.MAGENTA + f"({caller_name} L{caller_line}): {message}" + Fore.RESET
        )

    def info(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.info(
            Fore.BLACK + f"({caller_name} L{caller_line}): {message}" + Fore.RESET
        )

    def error(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.error(
            Fore.RED + f"({caller_name} L{caller_line}): {message}" + Fore.RESET
        )

    def warning(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.warning(
            Fore.YELLOW + f"({caller_name} L{caller_line}): {message}" + Fore.RESET
        )