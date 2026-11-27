import re
from datetime import date

from app.users import visibility_for

# Letters, digits, - and _ only. Strict on purpose: IDs go into database filters.
DOC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$")
VISIBILITIES = ("all", "hr_only")


def can_manage(user, department):
    """May this user upload, replace or delete documents of this department?"""
    role = user["role"]
    if role == "admin":
        return True
    if role == "hr":
        return department == user["department"]  # HR manages only its own department
    return False  # employees manage nothing


def can_see(user, visibility):
    return visibility in visibility_for(user["role"])


def validate_entry(doc_id, title, department, visibility, version, effective_date):
    """Return a list of problems (an empty list means the input is fine)."""
    problems = []
    if not DOC_ID_RE.match(doc_id):
        problems.append("doc_id must be 3-40 characters: letters, digits, - or _")
    if not 1 <= len(title) <= 120:
        problems.append("title must be 1-120 characters")
    if not 1 <= len(department) <= 40:
        problems.append("department must be 1-40 characters")
    if visibility not in VISIBILITIES:
        problems.append("visibility must be one of: " + ", ".join(VISIBILITIES))
    if not 1 <= len(version) <= 20:
        problems.append("version must be 1-20 characters")
    try:
        date.fromisoformat(effective_date)  # raises ValueError if not YYYY-MM-DD
    except ValueError:
        problems.append("effective_date must be YYYY-MM-DD")
    return problems


# app/permissions.py is the document gatekeeper with 3 jobs:

# can_manage(user, department) — Decides who can upload, replace, or delete documents (admin = any department, hr = own department only, employee = none).

# can_see(user, visibility) — Checks if a user's role is allowed to read a document's visibility tag ("all" or "hr_only").

# validate_entry(...) — Checks all 6 document metadata fields (doc_id, title, department, visibility, version, effective_date) before saving and returns a list of errors ([] means everything is valid).
