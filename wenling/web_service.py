"""
Run with: clear; python -m wenling.scripts.fetch_web_page
"""

import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wenling.archiver import ArchiverOrchestrator
from wenling.common.utils import load_env

app = FastAPI()


class ArchiveRequest(BaseModel):
    url: str


class GenerateArticleRequest(BaseModel):
    date_range: str
    tags: list[str]


@app.post("/archive-article/")
async def archive_article(request: ArchiveRequest):
    orchestrator = ArchiverOrchestrator(verbose=True)
    try:
        page_id = await orchestrator.archive(request.url)
        return {"message": "Article archived successfully", "page_id": page_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-article/")
async def generate_article(request: GenerateArticleRequest):
    # Dummy implementation for generating an article
    return {"message": "Article generated successfully", "page_id": "123456789"}


if __name__ == "__main__":
    load_env()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("wenling:app", host="0.0.0.0", port=port, log_level="debug", reload=True)
