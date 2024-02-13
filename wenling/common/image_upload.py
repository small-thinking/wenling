import asyncio
import os
import ssl
import tempfile
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import parse_qs

import aiohttp
import flickrapi
import requests
import retrying
from dotenv import load_dotenv  # type: ignore
from flickrapi.auth import FlickrAccessToken

from wenling.common.utils import Logger


async def upload_image_to_flickr(image_url: str, title: str, description: str, tags: List[str], logger: Logger) -> str:
    """
    Uploads an image to Flickr and returns the URL of the uploaded photo.

    Args:
    - image_url (str): Path to the image file.
    - title (str): Title of the photo.
    - description (str): Description of the photo.
    - tags (List[str]): List of tags for the photo.
    - logger (Logger): Logger object for logging.

    Returns:
    - str: URL of the uploaded photo on Flickr.

    Raises:
    - Exception: If there is an error in uploading or parsing the response.
    """
    load_dotenv(override=True)

    api_key = os.environ.get("FLICKR_API_KEY")
    api_secret = os.environ.get("FLICKR_SECRET")
    token = os.environ.get("FLICKR_ACCESS_TOKEN")
    token_secret = os.environ.get("FLICKR_ACCESS_TOKEN_SECRET")
    fullname = os.environ.get("FLICKR_FULLNAME")
    username = os.environ.get("FLICKR_USERNAME")
    userid = os.environ.get("FLICKR_USERID")
    access_level = "write"

    flickr_access_token = FlickrAccessToken(
        token=token, token_secret=token_secret, access_level=access_level, fullname=fullname, username=username
    )
    flickr = flickrapi.FlickrAPI(
        api_key=api_key, secret=api_secret, username=username, token=flickr_access_token, format="rest"
    )

    try:
        # Get the image data
        if image_url.startswith("https://github.com/"):
            image_url = image_url.replace("blob", "raw")
        response = requests.get(image_url)
        response.raise_for_status()
        # Create a temporary file and save the image data
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(response.content)
            temp_file_path = temp.name
        if os.environ.get("VERBOSE") == "True":
            logger.info(f"For flickr upload, download file to {temp_file_path}.")

        response = flickr.upload(
            filename=temp_file_path,
            tags=" ".join(tags),
            is_public=1,
            title=title,
            description=description,
        )
        response_root = ET.fromstring(response.decode("utf-8"))  # type: ignore
        photoid = response_root.find("photoid").text  # type: ignore
        return f"https://www.flickr.com/photos/{userid}@N05/{photoid}"
    except Exception as e:
        logger.error(f"Error uploading image to Flickr: {e}")
        raise


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=3)
async def upload_image_to_imgur(image_path: str, logger: Logger) -> str:
    """
    Uploads an image to Imgur and returns the URL of the uploaded image.

    Parameters:
        image_path (str): The path to the image file to be uploaded.
        logger (Logger): The logger object for logging messages.

    Returns:
        str: The URL of the uploaded image.

    Raises:
        ValueError: If IMGUR_CLIENT_ID environment variable is not set.
    """
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
            if os.environ.get("VERBOSE") == "True":
                logger.warning(f"Failed to upload image to imgur: {e}, retest in {retest_interval} seconds.")
            await asyncio.sleep(retest_interval)
            return ""

    return data["data"]["link"]


@retrying.retry(wait_fixed=1000, stop_max_attempt_number=3)
async def save_image_to_imgur(image_url: str, logger: Logger):
    """
    Save an image from the given URL to Imgur.

    Args:
        image_url (str): The URL of the image to be saved.
        logger (Logger): An instance of the logger to log messages.

    Returns:
        str: The URL of the image saved on Imgur.

    Raises:
        HTTPError: If there is an error while getting the image data.
        Exception: If there is an error while uploading the image to Imgur.
    """
    # Get the image data
    if image_url.startswith("https://github.com/"):
        image_url = image_url.replace("blob", "raw")
    response = requests.get(image_url)
    response.raise_for_status()
    # Create a temporary file and save the image data
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(response.content)
        temp_file_path = temp.name
    if os.environ.get("VERBOSE") == "True":
        logger.info(f"Download file to {temp_file_path}.")
    imgur_url = await upload_image_to_imgur(temp_file_path, logger)
    os.remove(temp_file_path)
    return imgur_url
