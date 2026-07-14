from fastapi import Body, FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from fastapi.concurrency import run_in_threadpool
import os
import asyncio
import json
from fetcher import (
    StealthRetryAvailableError,
    clean_youtube_url,
    fetch_content,
    fetch_webpage_content,
    is_youtube_url,
)
from storage import (
    DEFAULT_TITLE_FALLBACK,
    build_summaries_zip,
    bulk_delete_summaries,
    create_summary,
    delete_summary,
    get_summary,
    initialize_database,
    list_summaries,
    markdown_filename,
    rename_summary,
    validate_summary_ids,
)
from summarizer import (
    generate_summary_title,
    summarize_content,
    summarize_content_stream,
    summarize_content_stream_async,
)

app = FastAPI(title="Web Summarizer")
templates = Jinja2Templates(directory="templates")
initialize_database()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/summaries/{summary_id}", response_class=HTMLResponse)
async def saved_summary(request: Request, summary_id: int):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"summary_id": summary_id},
    )


@app.get("/summary", response_class=HTMLResponse)
async def summary(request: Request, url: str = Query(...)):
    return templates.TemplateResponse(
        request=request,
        name="loading.html",
        context={"url": url},
    )


@app.get("/api/summary")
async def api_summary(url: str = Query(...)):
    try:
        url = clean_youtube_url(url)
        content, source_type = await run_in_threadpool(fetch_content, url)
        summary = await run_in_threadpool(summarize_content, content, source_type)
        return JSONResponse({
            "url": url,
            "summary": summary,
            "source_type": source_type
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def summary_generator(url: str, request: Request, stealth_mode: bool = False):
    try:
        url = clean_youtube_url(url)
        yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching content...'})}\n\n"

        # Run blocking fetch in threadpool
        if stealth_mode and not is_youtube_url(url):
            content, source_type = await run_in_threadpool(fetch_webpage_content, url, True)
        else:
            content, source_type = await run_in_threadpool(fetch_content, url)

        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating summary...'})}\n\n"

        # Use async streaming
        stream = await summarize_content_stream_async(content, source_type)

        full_summary = ""
        async for chunk in stream:
            # Check if client is still connected
            if await request.is_disconnected():
                # Client disconnected, break the loop
                break

            if chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_summary += content_chunk
                yield f"data: {json.dumps({'type': 'content', 'chunk': content_chunk})}\n\n"

        # Only send completion if not disconnected
        if not await request.is_disconnected():
            yield f"data: {json.dumps({'type': 'status', 'message': 'Saving summary...'})}\n\n"
            title = DEFAULT_TITLE_FALLBACK
            try:
                title = await generate_summary_title(full_summary)
            except Exception:
                pass

            if await request.is_disconnected():
                return

            try:
                saved = await run_in_threadpool(create_summary, title, url, source_type, full_summary)
                saved_id, save_error = saved["id"], None
            except Exception:
                saved_id = None
                save_error = "The completed summary could not be saved. You can still download it now."

            yield f"data: {json.dumps({'type': 'status', 'message': 'Complete'})}\n\n"
            done = {
                "type": "done",
                "source_type": source_type,
                "url": url,
                "summary_id": saved_id,
                "title": title,
            }
            if save_error:
                done["save_error"] = save_error
            yield f"data: {json.dumps(done)}\n\n"

    except asyncio.CancelledError:
        # Handle cancellation gracefully
        pass
    except StealthRetryAvailableError as e:
        event_type = "error" if stealth_mode else "stealth_available"
        yield f"data: {json.dumps({'type': event_type, 'message': str(e)})}\n\n"
    except ValueError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'An error occurred: {str(e)}'})}\n\n"


@app.get("/api/summary/stream")
async def api_summary_stream(
    request: Request,
    url: str = Query(...),
    stealth_mode: bool = Query(False),
):
    return StreamingResponse(
        summary_generator(url, request, stealth_mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/summaries")
async def api_list_summaries():
    return {"summaries": await run_in_threadpool(list_summaries)}


@app.post("/api/summaries/bulk-delete")
async def api_bulk_delete_summaries(payload: dict = Body(...)):
    try:
        summary_ids = await run_in_threadpool(validate_summary_ids, payload.get("ids"))
        return await run_in_threadpool(bulk_delete_summaries, summary_ids)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/summaries/download-zip")
async def api_download_zip(payload: dict = Body(...)):
    try:
        summary_ids = await run_in_threadpool(validate_summary_ids, payload.get("ids"))
        archive = await run_in_threadpool(build_summaries_zip, summary_ids)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="web-summaries.zip"'},
    )


@app.get("/api/summaries/{summary_id}")
async def api_get_summary(summary_id: int):
    record = await run_in_threadpool(get_summary, summary_id)
    if not record:
        raise HTTPException(status_code=404, detail="Summary not found")
    return record


@app.patch("/api/summaries/{summary_id}")
async def api_rename_summary(summary_id: int, payload: dict = Body(...)):
    try:
        record = await run_in_threadpool(rename_summary, summary_id, payload.get("title"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not record:
        raise HTTPException(status_code=404, detail="Summary not found")
    return record


@app.delete("/api/summaries/{summary_id}")
async def api_delete_summary(summary_id: int):
    if not await run_in_threadpool(delete_summary, summary_id):
        raise HTTPException(status_code=404, detail="Summary not found")
    return {"deleted_ids": [summary_id]}


@app.get("/api/summaries/{summary_id}/download")
async def api_download_summary(summary_id: int):
    record = await run_in_threadpool(get_summary, summary_id)
    if not record:
        raise HTTPException(status_code=404, detail="Summary not found")
    filename = await run_in_threadpool(markdown_filename, record["title"], summary_id)
    return Response(
        record["markdown"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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


@app.get("/download/transcript")
async def download_transcript(url: str):
    content, _ = await run_in_threadpool(fetch_content, url)
    return StreamingResponse(
        iter([content]),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=transcript.txt"}
    )


@app.get("/api/transcript")
async def api_transcript(url: str = Query(...)):
    try:
        content, source_type = await run_in_threadpool(fetch_content, url)
        return JSONResponse({
            "url": url,
            "transcript": content,
            "source_type": source_type
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
