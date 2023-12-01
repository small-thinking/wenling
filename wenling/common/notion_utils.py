"""Store the data in Notion.
"""
import json
import os
from typing import Any, Dict, List, Optional

from notion_client import AsyncClient

from wenling.common.utils import Logger


class NotionStorage:
    """Store the data into notion knowledge base."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.token = os.environ.get("NOTION_TOKEN")
        if not self.token:
            raise ValueError("Please set the Notion token in .env.")
        self.notion = AsyncClient(auth=self.token)
        self.root_page_id = os.environ.get("NOTION_ROOT_PAGE_ID")
        self.logger = Logger(os.path.basename(__file__), verbose=verbose)
        if self.verbose:
            self.logger.info("Notion storage initialized.")

    async def _get_or_create_database(self) -> str:
        """Get the database id or create a new one if it does not exist."""
        results = await self.notion.search(query=self.root_page_id, filter={"property": "object", "value": "database"})
        results = results.get("results")
        if len(results):
            database_id = results[0]["id"]
            if self.verbose:
                self.logger.info(f"Database {database_id} already exists.")
            return results[0]["id"]
        else:
            # Create a new database.
            if self.verbose:
                self.logger.info(f"Database for page {self.root_page_id} does not exist. Creating a new one...")
            parent = {"page_id": self.root_page_id}
            properties: Dict[str, Any] = {
                "Title": {"title": {}},
                "Type": {"select": {}},
                "Tags": {"multi_select": {}},
                "Archive Date": {"date": {}},
                "Status": {"select": {}},
                "URL": {"rich_text": {}},
            }
            response = await self.notion.databases.create(
                parent=parent,
                title=[{"type": "text", "text": {"content": "Wenling Archive"}}],
                properties=properties,
            )
            if self.verbose:
                self.logger.info("Database created.")
            return response["id"]

    async def _create_page_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create blocks in the page.
        The blocks is expected to be a list of dicts.
        """
        page_contents: List[Dict[str, Any]] = []
        for block in blocks:
            if block.get("type") in ["h1", "heading_1"]:
                page_contents.append(
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
                    }
                )
            elif block.get("type") in ["h2", "heading_2"]:
                page_contents.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
                    }
                )
            elif block.get("type") in ["h3", "heading_3"]:
                page_contents.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
                    }
                )
            elif block.get("type") in ["image", "img"]:
                page_contents.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": block["url"]}},
                    }
                )
            elif block.get("type") == "text":
                page_contents.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": block["text"]}}]},
                    }
                )
            else:
                self.logger.warning(f"Unsupported block type: {block['type']}")
        return page_contents

    async def _add_to_database(self, database_id: str, json_obj: Dict[str, Any]) -> None:
        """Add the data as a page to the database.
        The json object is expected to have two keys: properties and children.
        Each is also expected to be a dictionary.
        The properties contains Title, Type, Tags, Archive Date, Status, and URL.
        The children contains the blocks of contents of the page.
        """
        if "properties" not in json_obj:
            raise ValueError("The json object must have a 'properties' key.")
        properties: Dict[str, Any] = json_obj["properties"]
        page_properties = {
            "Title": [
                {
                    "type": "text",
                    "text": {"content": str(properties["title"])},
                }
            ],
            "Type": {"name": properties["type"]},
            "Archive Date": {"start": properties["datetime"]},
            "Tags": [{"name": tag} for tag in properties.get("tags", [])],
            "Status": {"name": properties.get("status", "Archived")},
            "URL": [{"type": "text", "text": {"content": properties.get("url", "")}}],
        }
        children = await self._create_page_blocks(json_obj["children"])
        response = await self.notion.pages.create(
            parent={"type": "database_id", "database_id": database_id},
            properties=page_properties,
            children=children[:200],
        )
        if "id" not in response:
            raise ValueError("Failed to create the page.")
        if self.verbose:
            self.logger.info("Page created.")

    async def store(self, json_obj: Dict[str, Any]):
        """Store the data into Notion."""
        if self.verbose:
            self.logger.info("Storing data into Notion.")
        database_id = os.environ.get("NOTION_DATABASE_ID") or await self._get_or_create_database()
        self.logger.info(f"Database id: {database_id}")
        await self._add_to_database(database_id, json_obj)
        if self.verbose:
            self.logger.info("Data stored into Notion.")