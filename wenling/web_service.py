"""
Run with: 
"""

import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wenling.archiver import ArchiverOrchestrator

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
        await orchestrator.archive(request.url)
        return {"message": "Article archived successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-article/")
async def generate_article(request: GenerateArticleRequest):
    # Dummy implementation for generating an article
    return {"message": "Article generated successfully", "date_range": request.date_range, "tags": request.tags}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("wenling:app", host="0.0.0.0", port=8000, log_level="debug", reload=True)
