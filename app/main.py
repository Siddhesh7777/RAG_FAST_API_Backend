import os
import tempfile
from fastapi import FastAPI, File, HTTPException, UploadFile
from app.rag import extract_text

from app.chunker import chunk_pages
from app.loader import load_pdf
from app.store import add_chunk
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from pydantic import BaseModel
from app.agent import graph
import logging
import time
from dotenv import load_dotenv
from app.config import settings
from app.logging_setup import setup_logging

load_dotenv()


setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="PDF Chunking API")

Max_mb = 20


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
def upload_file(thread_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    data = file.file.read()
    if len(data) > Max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"File size exceeds {Max_mb} MB limit"
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(data)
        path = tmp.name
    logger.info(
        "upload start thread=%s file=%s bytes=%d", thread_id, file.filename, len(data)
    )
    start = time.perf_counter()

    try:
        chunks = chunk_pages(
            load_pdf(path),
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        add_chunk(chunks, thread_id, file.filename)

    except ValueError as e:
        logger.warning("upload rejected thread=%s reason=%s", thread_id, e)
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.remove(path)

    logger.info(
        "upload done thread=%s chunks=%d seconds=%.1f",
        thread_id,
        len(chunks),
        time.perf_counter() - start,
    )
    return {"filename": file.filename, "chunks": len(chunks)}


# this is added as a part of the new code for the chat endpoint
class ChatRequest(BaseModel):
    thread_id: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    logger.info(
        "chat start thread=%s question_chars=%d", req.thread_id, len(req.message)
    )

    def token_stream():
        start = time.perf_counter()
        try:
            events = graph.stream(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                stream_mode="messages",
            )
            for chunk, meta in events:
                if (
                    isinstance(chunk, AIMessageChunk)
                    and chunk.content
                    and meta.get("langgraph_node") == "chat"
                ):
                    text = extract_text(chunk.content)
                    if text:
                        yield text
        except Exception:
            logger.exception("chat failed thread=%s", req.thread_id)
            yield "\n\nSorry, something went wrong. Please try again."
        finally:
            logger.info(
                "chat done thread=%s seconds=%.1f",
                req.thread_id,
                time.perf_counter() - start,
            )

    return StreamingResponse(token_stream(), media_type="text/plain")
