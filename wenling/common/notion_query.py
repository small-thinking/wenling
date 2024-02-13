import os
from typing import Any, List, Optional, Tuple

from notion_client import AsyncClient

from wenling.common.utils import Logger


class NotionQuery:
    def __init__(self, database_id: str):
        self.database_id = database_id

        self.logger = Logger(logger_name=os.path.basename(__file__))
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
        # Initialize the base structure with an "and" clause to hold all conditions
        filter_conditions = {"and": []}

        # Add conditions for start and end dates directly into the "and" clause
        if start_date:
            filter_conditions["and"].append({"property": "Archive Date", "date": {"on_or_after": start_date}})
        if end_date:
            filter_conditions["and"].append({"property": "Archive Date", "date": {"on_or_before": end_date}})

        # Prepare the "or" clause for tags if tags are provided
        if tags:
            # Initialize an "or" clause to hold tag conditions
            tag_conditions = {"or": []}
            # Add each tag to the "or" clause
            for tag in tags:
                tag_conditions["or"].append({"property": "Tags", "multi_select": {"contains": tag}})
            # Add the "or" clause for tags to the main "and" clause if there are tags
            filter_conditions["and"].append(tag_conditions)

        # Perform the query using the constructed filter conditions
        try:
            if os.environ.get("VERBOSE") == "True":
                self.logger.info(f"Querying Notion database with filter conditions: {filter_conditions}")
            results = await self.notion.databases.query(
                database_id=self.database_id, filter=filter_conditions if filter_conditions else None
            )
            if not results:
                self.logger.info("No results found.")
                return []
            # Extract the page_ids from the results.
            page_ids = [page.get("id") for page in results.get("results")]
            if os.environ.get("VERBOSE") == "True":
                self.logger.info(f"Retrieved {len(page_ids)} results.")
            return page_ids
        except Exception as e:
            self.logger.error(f"Error querying Notion database: {e}")
            return []

    async def query_page_contents(self, page_id: str) -> Tuple[str, str, List[str]]:
        """
        Query the contents of the page with the given page_id.

        Args:
            page_id (str): The ID of the page to query.

        Returns:
            Tuple[str, str, str]: A tuple containing the URL, title, and tags of the page.
        """
        # Query the contents of the page with the given page_id
        page = await self.notion.pages.retrieve(page_id=page_id)
        if os.environ.get("VERBOSE") == "True":
            self.logger.info(f"Retrieved page: {page}")
        # Extract the URL and title properties from the page
        url = page.get("properties").get("URL").get("rich_text")[0].get("text")
        title = page.get("properties").get("Title").get("title")[0].get("text").get("content")
        tags_blob = page.get("properties").get("Tags").get("multi_select")
        tags = [tag.get("name") for tag in tags_blob]
        # Return the URL and title as a tuple
        return url, title, tags
