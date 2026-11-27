import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import current_user
from app.injest_kb import ingest_one  # the Day 2 function, reused as is
from app.permissions import can_manage, can_see, validate_entry
from app.store import company_filter, store
from app.users import visibility_for

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])
MAX_MB = 20


def _existing_meta(doc_id):
    # Metadata of the first stored chunk of this company document, or None.
    data = store.get(
        where={"$and": [{"doc_id": doc_id}, {"scope": "company"}]},
        include=["metadatas"],
    )
    metas = data["metadatas"]
    return metas[0] if metas else None


def _company_metadatas(allowed):
    if not allowed:  # fail closed
        return []
    # The visibility filter runs inside the database query.
    data = store.get(where=company_filter(allowed), include=["metadatas"])
    return data["metadatas"]


@router.get("/documents")
def list_documents(user: dict = Depends(current_user)):
    seen = {}  # one entry per document, not per chunk
    for m in _company_metadatas(visibility_for(user["role"])):
        if m["doc_id"] not in seen:
            seen[m["doc_id"]] = {
                "doc_id": m["doc_id"],
                "title": m.get("title", m["doc_id"]),
                "department": m.get("department", ""),
                "visibility": m.get("visibility", ""),
                "version": m.get("version", ""),
                "effective_date": m.get("effective_date", ""),
                "can_manage": can_manage(
                    user, m.get("department", "")
                ),  # drives the Delete button
            }
    docs = sorted(seen.values(), key=lambda d: (d["department"], d["title"]))
    return {"documents": docs}


@router.post("/documents")
def upload_document(
    file: UploadFile = File(...),
    doc_id: str = Form(...),
    title: str = Form(...),
    department: str = Form(...),
    effective_date: str = Form(...),
    visibility: str = Form("all"),
    version: str = Form("1.0"),
    user: dict = Depends(current_user),
):
    doc_id, title, department = doc_id.strip(), title.strip(), department.strip()
    version, effective_date = version.strip(), effective_date.strip()

    # 1. May this user manage THIS department at all?
    if not can_manage(user, department):
        raise HTTPException(
            status_code=403, detail="You may not manage documents for this department"
        )

    # 2. Is the metadata well-formed?
    problems = validate_entry(
        doc_id, title, department, visibility, version, effective_date
    )
    if problems:
        raise HTTPException(status_code=422, detail=problems)

    # 3. Reusing an existing ID REPLACES that document, so check the OLD owner too.
    existing = _existing_meta(doc_id)
    if existing and not can_manage(user, existing["department"]):
        raise HTTPException(
            status_code=403, detail="That document ID belongs to another department"
        )

    # 4. Is the file a real, reasonably sized PDF? Checks run before any slow work.
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    data = file.file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File larger than {MAX_MB} MB.")
    if not data.startswith(
        b"%PDF"
    ):  # real PDFs start with these bytes, whatever the filename says
        raise HTTPException(status_code=400, detail="This file is not a valid PDF.")

    # 5. Reuse the Day 2 ingestion. The file name inside the temp folder is built
    # from the validated doc_id, never from the client's file name.
    entry = {
        "file": f"{doc_id}.pdf",
        "doc_id": doc_id,
        "title": title,
        "department": department,
        "visibility": visibility,
        "version": version,
        "effective_date": effective_date,
    }
    with tempfile.TemporaryDirectory() as tmp:  # the folder is deleted automatically afterwards
        folder = Path(tmp)
        (folder / entry["file"]).write_bytes(data)
        try:
            status = ingest_one(folder, entry)  # "added", "replaced" or "unchanged"
        except ValueError as e:  # e.g. a scanned PDF with no text
            raise HTTPException(status_code=422, detail=str(e))
        except Exception:
            logger.exception("ingest failed doc_id=%s", doc_id)
            raise HTTPException(status_code=422, detail="Could not process this PDF")

    logger.info("document %s doc_id=%s by=%s", status, doc_id, user["username"])
    return {"doc_id": doc_id, "status": status}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, user: dict = Depends(current_user)):
    meta = _existing_meta(doc_id)
    # A document you cannot see looks exactly like one that doesn't exist.
    if meta is None or not can_see(user, meta["visibility"]):
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_manage(user, meta["department"]):
        raise HTTPException(
            status_code=403, detail="You may not manage documents for this department"
        )
    store.delete(where={"doc_id": doc_id})
    logger.info("document deleted doc_id=%s by=%s", doc_id, user["username"])
    return {"deleted": doc_id}
