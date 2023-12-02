import asyncio
import inspect
import logging
import os
import ssl
import tempfile
import threading
from datetime import datetime
from typing import Any, Optional

import aiohttp
import pytz  # type: ignore
import requests  # type: ignore
import retrying
from bs4 import BeautifulSoup
from colorama import Fore, ansi
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


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=3)
def fetch_url_content(url: str, css_selector: str) -> Optional[str]:
    """
    Fetches and extracts content from a given URL based on the specified CSS selector.

    Args:
    - url (str): The URL to fetch content from.
    - css_selector (str): A CSS selector to extract a specific content block from the HTML.

    Returns:
    - Optional[str]: A string containing the HTML of the first element matched by the CSS selector, or None if no match is found.

    Raises:
    - Exception: If the request to the URL fails or returns a non-200 status code.
    """
    response = requests.get(url)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the first element matching the CSS Selector
        element = soup.select_one(css_selector)

        # Return the HTML content of the element, or None if no element is found
        return str(element) if element else None
    else:
        raise Exception(f"Failed to fetch content from {url}, status code: {response.status_code}")


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

    def __init__(self, logger_name: str, verbose: bool = True, level: Any = logging.INFO):
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
        self.logger.debug(Fore.MAGENTA + f"({caller_name} L{caller_line}): {message}" + Fore.RESET)

    def info(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.info(Fore.BLACK + f"({caller_name} L{caller_line}): {message}" + Fore.RESET)

    def error(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.error(Fore.RED + f"({caller_name} L{caller_line}): {message}" + Fore.RESET)

    def warning(self, message: str) -> None:
        if not self.verbose:
            return
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame[3]
        caller_line = caller_frame[2]
        self.logger.warning(Fore.YELLOW + f"({caller_name} L{caller_line}): {message}" + Fore.RESET)


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=3)
async def upload_image_to_imgur(image_path: str, logger: Logger, verbose: bool = False) -> str:
    client_id = os.getenv("IMGUR_CLIENT_ID")
    if not client_id:
        raise ValueError("IMGUR_CLIENT_ID is not set")
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {client_id}"}

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data={"image": image_data}, ssl=ssl_context) as response:
                response.raise_for_status()
                data = await response.json()
        except Exception as e:
            retest_interval = 300
            if verbose:
                logger.warning(f"Failed to upload image to imgur: {e}, retest in {retest_interval} seconds.")
            await asyncio.sleep(retest_interval)
            return ""

    return data["data"]["link"]


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=3)
async def save_image_to_imgur(image_url: str, logger: Logger, verbose: bool = False):
    # Get the image data
    if image_url.startswith("https://github.com/"):
        image_url = image_url.replace("blob", "raw")
    response = requests.get(image_url)
    response.raise_for_status()
    # Create a temporary file and save the image data
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(response.content)
        temp_file_path = temp.name
    if verbose:
        logger.info(f"Download file to {temp_file_path}.")
    imgur_url = await upload_image_to_imgur(temp_file_path, logger, verbose=verbose)
    os.remove(temp_file_path)
    return imgur_url
