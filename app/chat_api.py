import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel, Field

from app.agent import graph
from app.auth import current_user  # "valid token required" dependency
from app.rag import extract_text
from app.threads import (
    DEFAULT_TITLE,
    create_thread,
    get_owned_thread,
    list_threads,
    set_title,
)
from app.users import visibility_for

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    thread_id: str
    # Limits protect your Gemini quota: no empty messages, no giant ones.
    message: str = Field(min_length=1, max_length=4000)


def _owned_or_404(thread_id: str, user: dict) -> dict:
    thread = get_owned_thread(thread_id, user["username"])
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


def _history(thread_id: str) -> list:
    # Read the saved conversation from the LangGraph checkpointer.
    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state and state.values else []
    out = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": extract_text(m.content)})
        elif isinstance(m, AIMessage):
            text = extract_text(m.content).strip()
            if text:  # skip tool-call messages that carry no text
                out.append({"role": "assistant", "content": text})
    return out


@router.post("/threads")
def new_thread(user: dict = Depends(current_user)):
    return create_thread(user["username"])


@router.get("/threads")
def my_threads(user: dict = Depends(current_user)):
    return list_threads(user["username"])


@router.get("/threads/{thread_id}/messages")
def thread_messages(thread_id: str, user: dict = Depends(current_user)):
    _owned_or_404(thread_id, user)  # ownership check BEFORE reading anything
    return _history(thread_id)


@router.post("/chat")
def chat(req: ChatRequest, user: dict = Depends(current_user)):
    thread = _owned_or_404(req.thread_id, user)

    # Everything the agent needs to know about WHO is asking is set here, by the
    # server, from the verified user. The model cannot change any of it.
    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "username": user["username"],
            "visibility": visibility_for(user["role"]),
        },
        "metadata": {"thread_id": req.thread_id},
        # If you use tracing, keep your callbacks line here, for example:
        # "callbacks": get_callbacks(),
    }

    if thread["title"] == DEFAULT_TITLE:
        set_title(req.thread_id, req.message[:60])  # first question becomes the title

    # Log the length of the question, never the question itself.
    logger.info(
        "chat start user=%s thread=%s question_chars=%d",
        user["username"],
        req.thread_id,
        len(req.message),
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
            logger.exception(
                "chat failed user=%s thread=%s", user["username"], req.thread_id
            )
            yield "\n\nSorry, something went wrong. Please try again."
        finally:
            logger.info(
                "chat done user=%s thread=%s seconds=%.1f",
                user["username"],
                req.thread_id,
                time.perf_counter() - start,
            )

    return StreamingResponse(token_stream(), media_type="text/plain")
