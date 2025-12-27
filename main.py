from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
import os
import asyncio
import json
from fetcher import fetch_content
from summarizer import summarize_content, summarize_content_stream

app = FastAPI(title="Web Summarizer")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/summary", response_class=HTMLResponse)
async def summary(request: Request, url: str = Query(...)):
    return templates.TemplateResponse("loading.html", {
        "request": request,
        "url": url
    })


@app.get("/api/summary")
async def api_summary(url: str = Query(...)):
    try:
        content, source_type = fetch_content(url)
        summary = summarize_content(content, source_type)
        return JSONResponse({
            "url": url,
            "summary": summary,
            "source_type": source_type
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def summary_generator(url: str):
    try:
        yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching content...'})}\n\n"
        
        content, source_type = fetch_content(url)
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating summary...'})}\n\n"
        
        stream = summarize_content_stream(content, source_type)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'type': 'content', 'chunk': content_chunk})}\n\n"
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Complete'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'source_type': source_type, 'url': url})}\n\n"
        
    except ValueError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'An error occurred: {str(e)}'})}\n\n"


@app.get("/api/summary/stream")
async def api_summary_stream(url: str = Query(...)):
    return StreamingResponse(
        summary_generator(url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/download")
async def download(summary: str = Form(...)):
    temp_file = "summary.md"
    with open(temp_file, "w") as f:
        f.write(summary)
    
    return FileResponse(
        temp_file,
        media_type="text/markdown",
        filename="summary.md"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)