from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
import os
from fetcher import fetch_content
from summarizer import summarize_content

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