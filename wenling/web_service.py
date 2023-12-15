"""
Run with: clear; python -m wenling.scripts.fetch_web_page
"""

import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wenling.archiver import ArchiverOrchestrator
from wenling.common.utils import Logger, load_env

app = FastAPI()
logger = Logger(logger_name=os.path.basename(__file__), verbose=True)
load_env()


class ArchiveRequest(BaseModel):
    url: str


class GenerateArticleRequest(BaseModel):
    date_range: str
    tags: list[str]


@app.post("/archive-article/")
async def archive_article(request: ArchiveRequest):
    orchestrator = ArchiverOrchestrator(verbose=True)
    try:
        # Log the params.
        logger.info(f"Archive url: {request.url}")
        page_id = await orchestrator.archive(request.url)
        if page_id is None:
            raise HTTPException(status_code=404, detail="Corresponding archiver not found")
        return {"message": "Article archived successfully", "page_id": page_id}
    except Exception as e:
        # Print stack trace.
        raise HTTPException(status_code=500, detail=f"Got the error: {str(e)}")


@app.post("/generate-article/")
async def generate_article(request: GenerateArticleRequest):
    # Dummy implementation for generating an article
    logger.info(f"Generate article with params: {request}")
    return {"message": "Article generated successfully", "page_id": "123456789"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("wenling:app", host="0.0.0.0", port=port, log_level="debug", reload=True)
