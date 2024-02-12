import asyncio
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

from notion_client import AsyncClient

from wenling.common.utils import Logger


class NotionQuery:
    def __init__(self, database_id: str, verbose: bool = False):
        self.database_id = database_id
        self.verbose = verbose
        self.logger = Logger(logger_name=os.path.basename(__file__), verbose=verbose)
        self.token = os.environ.get("NOTION_TOKEN")
        if not self.token:
            raise ValueError("Please set the Notion token in .env.")
        self.notion = AsyncClient(auth=self.token)

    async def query_pages(self, start_date: str, end_date: str, tags: Optional[List[str]] = None) -> List[Any]:
        """
        Query the database with given date range and tags.
        The start and end dates that represent the range can be the same date, or a range of dates.
        The tags are optional, and can be empty.

        Args:
            start_date (str): The start date of the range.
            end_date (str): The end date of the range.
            tags (Optional[List[str]]): Optional list of tags to filter the results. Defaults to None.

        Returns:
            List[str]: A list of page IDs that match the query.

        """

        # Construct the filter conditions based on the start and end dates
        filter_conditions = []
        if start_date:
            filter_conditions.append({"property": "Archive Date", "date": {"on_or_after": start_date}})
        if end_date:
            filter_conditions.append({"property": "Archive Date", "date": {"on_or_before": end_date}})

        # Add filter conditions for tags if provided
        if tags:
            for tag in tags:
                filter_conditions.append({"property": "Tags", "multi_select": {"contains": tag}})

        # Perform the query using the constructed filter conditions
        try:
            if self.verbose:
                self.logger.info(f"Querying Notion database with filter conditions: {filter_conditions}")
            results = await self.notion.databases.query(
                database_id=self.database_id, filter={"and": filter_conditions} if filter_conditions else None
            )
            if self.verbose:
                self.logger.info(f"Query {len(results)} results.")
        except Exception as e:
            self.logger.error(f"Error querying Notion database: {e}")
            return []
        if not results:
            self.logger.info("No results found.")
            return []
        return results

    async def query_page_contents(self, page_id: str) -> Tuple[str, str]:
        """
        Query the contents of the page with the given page_id.

        Args:
            page_id (str): The ID of the page to query.

        Returns:
            Tuple[str, str]: A tuple containing the URL and title of the page.
        """
        # Query the contents of the page with the given page_id
        page = await self.notion.pages.retrieve(page_id=page_id)

        # Extract the URL and title properties from the page
        url = page.get("properties").get("URL").get("url")
        title = page.get("properties").get("Title").get("title")

        # Return the URL and title as a tuple
        return url, title
