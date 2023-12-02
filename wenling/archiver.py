"""
"""
import asyncio
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag

from wenling.common.model_utils import OpenAIChatModel
from wenling.common.notion_utils import NotionStorage
from wenling.common.utils import *


class ArchiverOrchestrator:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = Logger(logger_name=os.path.basename(__file__), verbose=verbose)
        self.archivers: List[Dict[str, Any]] = [
            {
                "match_regex": r"^https://mp\.weixin\.qq\.com/s/.*$",
                "archiver": WechatArticleArchiver(verbose=verbose),
            }
        ]

    async def archive(self, url: str):
        """Match the url with pattern and find the corresponding archiver."""
        for archiver in self.archivers:
            if re.match(pattern=archiver["match_regex"], string=url):
                if self.verbose:
                    self.logger.info(f"Archive url with archiver {archiver['archiver'].name}...")
                await archiver["archiver"].archive(url)
                if self.verbose:
                    self.logger.info(f"Archived url with archiver {archiver['archiver'].name}.")


class Archiver(ABC):
    """Archiver is a tool used to archive the bookmarked articles."""

    def __init__(self, vendor_type: str = "openai", verbose: bool = False):
        load_env()
        self.api_key = os.getenv("ARCHIVER_API_KEY")
        self.verbose = verbose
        self.logger = Logger(logger_name=os.path.basename(__file__), verbose=verbose)
        self.notion_store = NotionStorage(verbose=verbose)
        if vendor_type == "openai":
            self.model = OpenAIChatModel()
        else:
            raise NotImplementedError
        self.name = self._set_name()
        self._extra_setup()

    def _extra_setup(self):
        pass

    @abstractmethod
    def _set_name(self) -> str:
        pass

    async def archive(self, url: str):
        if not check_url_exists(url):
            raise ValueError(f"The url {url} does not exist.")
        article_json_obj = await self._archive(url)
        await self.notion_store.store(json_obj=article_json_obj)

    @abstractmethod
    async def _archive(self, url: str) -> Dict[str, Any]:
        pass

    def list_archived(self) -> List[str]:
        return []


class WechatArticleArchiver(Archiver):
    """
    WechatArticleArchiver is a tool used to archive the bookmarked wechart articles.
    """

    def __init__(self, vendor_type: str = "openai", verbose: bool = False):
        super().__init__(vendor_type=vendor_type, verbose=verbose)
        self.root_css_selector = "div#img-content.rich_media_wrp"

    def _set_name(self) -> str:
        return "WechatArticleArchiver"

    def _parse_title(self, element_bs: BeautifulSoup) -> str:
        title = element_bs.select_one("h1").get_text().strip()
        return title

    def _parse_author(self, element_bs: BeautifulSoup) -> str:
        author = element_bs.select_one(".rich_media_meta.rich_media_meta_text").get_text().strip()
        return author

    def _parse_publish_time(self, element_bs: BeautifulSoup) -> Dict[str, str]:
        publish_time_element = element_bs.select_one(".detail-time")
        publish_time = publish_time_element.get_text().strip() if publish_time_element else "Not available"
        return {"type": "h2", "text": publish_time}

    def _parse_tags(self, element_bs: BeautifulSoup) -> List[str]:
        tags = [tag.get_text().strip() for tag in element_bs.select(".article-tag__item")]
        return tags

    def _parse_paragraph(self, paragraph_tag: Tag, cache: Dict[str, Any]) -> List[Dict[str, str]]:
        # 1. Each <p style="visibility: visible;">content</> is a paragraph, and will be put as an individual dictionary.
        # 1. 1. If the content a simple text, it will be stored as {"type": "text", "text": <content>}.
        # 1. 2. If the content is an image, it will be stored as {"type": "image", "url": <url>}.
        # 2. A <blockquote style="visibility: visible;">...</blockquote>, then store as {"type": "quote", "text": <content>}.
        # 3. A <span data-vw...>...</span> indicate a video, and store as {"type": "video", "url": <url>}. The url can be obtained from the attr data-src.
        parsed_elements = []
        if paragraph_tag.name == "p":
            if "text-align: center;" in paragraph_tag.get("style", "") and paragraph_tag.find("strong"):
                # <strong> directly wrapped by <p style="text-align: center;">
                strong_text = paragraph_tag.find("strong").get_text().strip()
                if strong_text not in cache:
                    parsed_elements.append({"type": "h2", "text": strong_text})
                    cache[strong_text] = True
            elif paragraph_tag.find("img"):  # Check for images
                image_url = paragraph_tag.find("img")["data-src"]
                if image_url not in cache:
                    parsed_elements.append({"type": "image", "url": image_url})
                    cache[image_url] = True
            else:  # Regular text content, including <strong> not in center-aligned <p>
                for child in paragraph_tag.contents:
                    if child.name == "strong":
                        strong_text = child.get_text().strip()
                        if strong_text not in cache:
                            parsed_elements.append({"type": "h2", "text": strong_text})
                            cache[strong_text] = True
                    elif child.string:
                        text = child.string.strip()
                        if text:
                            if text not in cache:
                                parsed_elements.append({"type": "text", "text": text})
                                cache[text] = True
        elif paragraph_tag.name == "blockquote":
            text = paragraph_tag.get_text().strip()
            if text not in cache:
                parsed_elements.append({"type": "quote", "text": text})
                cache[text] = True
        elif paragraph_tag.name == "span":
            text = paragraph_tag.get_text().strip()
            if text:
                if text not in cache:
                    parsed_elements.append({"type": "text", "text": text})
                    cache[text] = True
        elif paragraph_tag.name == "span" and paragraph_tag.get("data-vw"):
            video_url = paragraph_tag.get("data-src")
            if video_url not in cache:
                parsed_elements.append({"type": "video", "url": video_url})
                cache[video_url] = True
        elif paragraph_tag.name in ["ul", "ol"]:
            for li in paragraph_tag.find_all("li"):
                li_text = li.get_text().strip()
                if li_text:
                    if li_text not in cache:
                        parsed_elements.append({"type": "text", "text": li_text})
                        cache[li_text] = True
        elif paragraph_tag.name == "em":
            em_text = paragraph_tag.get_text().strip()
            if em_text not in cache:
                parsed_elements.append({"type": "text", "text": em_text})
                cache[em_text] = True
        else:
            content = paragraph_tag.get_text().strip()
            if content:
                if content not in cache:
                    parsed_elements.append({"type": f"{paragraph_tag.name}", "text": content})
                    cache[content] = True

        return parsed_elements

    def _parse_section(self, section_tag: Tag, cache: Dict[str, Any]) -> List[Dict[str, Any]]:
        content_list = []
        for tag in section_tag.descendants:
            if tag.name in ["p", "blockquote", "span", "ul", "ol"]:
                blob = self._parse_paragraph(tag, cache)
                if blob:
                    content_list.extend(blob)
        return content_list

    def _parse_content(self, element_bs: BeautifulSoup) -> List[Dict[str, Any]]:
        content_element = element_bs.select_one("#js_content")
        content_json_obj: List[Dict[str, Any]] = []

        if not content_element:
            raise ValueError("The content element is not found.")

        # Initialize cache here
        cache: Dict[str, Any] = {}

        # Process all <section> tags first
        for section in content_element.find_all("section", recursive=False):
            content_json_obj.extend(self._parse_section(section, cache))

        # Process <p>, <ul>, <ol> tags that are direct children of the content_element
        for tag in content_element.find_all(["p", "blockquote", "span", "ul", "ol"], recursive=False):
            blob = self._parse_paragraph(tag, cache)
            if blob:
                content_json_obj.extend(blob)

        return content_json_obj

    async def _archive(self, url: str) -> Dict[str, Any]:
        # 1. Get the content block from the web page with the path div#img-content.rich_media_wrp.
        # Parse the elements and put them into a json object with list of elements.
        # 2. Get the title from the first h1 element, put it into {"type": "h1", "text": <title>}
        # 3. Get the author name from a sub element with class "rich_media_meta rich_media_meta_text", put it into {"type": "h2", "text": <author_name>}
        # 4. Get the publish time from a sub element (not direct sub) with class "detail-time", and put it into {"type": "h2", "text": <publis_time>}
        # 5. Get the tags from a sub elements (not direct sub) each with class "article-tag__item", and put them into {"type": "text", "text": <comma separated tags>}
        # 6. Get the content from a sub element with id "js_content", pass the entire blob as string to function _parse_content.
        element = fetch_url_content(url=url, css_selector=self.root_css_selector)
        element_bs = BeautifulSoup(element, "html.parser")
        if not element:
            raise ValueError(f"The url {url} does not have the element {self.root_css_selector}.")

        article_json_obj: Dict[str, Any] = {"properties": {}, "children": self._parse_content(element_bs=element_bs)}
        article_json_obj["properties"]["url"] = url
        article_json_obj["properties"]["title"] = self._parse_title(element_bs=element_bs)
        article_json_obj["properties"]["type"] = "微信"
        article_json_obj["properties"]["datetime"] = get_datetime()
        tags = self._parse_tags(element_bs=element_bs) + [self._parse_author(element_bs=element_bs)]
        tags = [tag.replace("#", "") for tag in tags]
        article_json_obj["properties"]["tags"] = tags
        if self.verbose:
            json_object_str = json.dumps(article_json_obj, indent=2)
            self.logger.info(f"Archived article: {json_object_str}")
        return article_json_obj
