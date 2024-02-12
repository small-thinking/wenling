"""
Run with: clear; python -m wenling.scripts.fetch_web_page
"""

import datetime
import os
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from wenling.archiver import ArchiverOrchestrator
from wenling.common.notion_query import NotionQuery
from wenling.common.utils import Logger, load_env

app = FastAPI()
security = HTTPBearer()
logger = Logger(logger_name=os.path.basename(__file__), verbose=True)
load_env()


class ArchiveRequest(BaseModel):
    url: str
    notes: Optional[str]


class GenerateArticleRequest(BaseModel):
    date_range: str
    tags: list[str]


class QueryArticleRequest(BaseModel):
    database_id: str
    start_date: str
    end_date: str
    tags: list[str]


def get_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials:
        api_key = credentials.credentials
        if api_key == os.environ.get("WENLING_API_KEY"):
            return api_key
        else:
            # Print out the entire request.
            logger.info(f"Request: {credentials}")
            logger.error(f"Invalid API Key Provided: {api_key}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API Key",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key not found",
        )


@app.post("/archive-article/")
async def archive_article(request: ArchiveRequest, api_key: str = Depends(get_api_key)):
    orchestrator = ArchiverOrchestrator(verbose=True)
    try:
        # Log the params.
        logger.info(f"Archive url: {request.url}")
        page_id = await orchestrator.archive(url=request.url, notes=request.notes)
        if page_id is None:
            raise HTTPException(status_code=404, detail="Corresponding archiver not found")
        return {"message": "Article archived successfully", "page_id": page_id}
    except Exception as e:
        # Print stack trace.
        raise HTTPException(status_code=500, detail=f"Got the error: {str(e)}")


@app.post("/generate-article/")
async def generate_article(request: GenerateArticleRequest, api_key: str = Depends(get_api_key)):
    # Dummy implementation for generating an article
    logger.info(f"Generate article with params: {request}")
    return {"message": "Article generated successfully", "page_id": "123456789"}


@app.post("/query-pages/")
async def query_article(request: QueryArticleRequest, api_key: str = Depends(get_api_key)):
    notion_query = NotionQuery(database_id=request.database_id, verbose=True)
    # Set default start date and end date if not provided
    if not request.start_date:
        request.start_date = str(datetime.date.today())
    if not request.end_date:
        request.end_date = str(datetime.date.today())
    pages = await notion_query.query_pages(start_date=request.start_date, end_date=request.end_date, tags=request.tags)
    return {"message": "Query successful", "pages": pages}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("wenling:app", host="0.0.0.0", port=port, log_level="debug", reload=True)
