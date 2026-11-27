import pytest

from app import documents_api

PDF = b"%PDF-1.4 minimal"  # enough to pass the "is it a PDF" check


def _form(**over):
    data = {
        "doc_id": "HR-TEST-001",
        "title": "Test policy",
        "department": "HR",
        "visibility": "all",
        "version": "1.0",
        "effective_date": "2026-04-01",
    }
    data.update(over)
    return data


def _upload(client, headers, who, data=None, content=PDF, name="x.pdf"):
    return client.post(
        "/documents",
        data=data or _form(),
        files={"file": (name, content, "application/pdf")},
        headers=headers(who),
    )


@pytest.fixture()
def fakes(monkeypatch):
    # Replace the slow parts (embedding, Chroma) with fakes. These tests check
    # the PERMISSION rules, which is why they run in milliseconds.
    calls = {"ingested": [], "deleted": [], "existing": {}}

    def fake_ingest(folder, entry, force=False):
        calls["ingested"].append(entry["doc_id"])
        return "added"

    class FakeStore:
        def delete(self, where):
            calls["deleted"].append(where)

    monkeypatch.setattr(documents_api, "ingest_one", fake_ingest)
    monkeypatch.setattr(
        documents_api, "_existing_meta", lambda doc_id: calls["existing"].get(doc_id)
    )
    monkeypatch.setattr(documents_api, "store", FakeStore())
    return calls


def test_upload_requires_login(client, fakes):
    r = client.post(
        "/documents", data=_form(), files={"file": ("x.pdf", PDF, "application/pdf")}
    )
    assert r.status_code == 401


def test_employee_cannot_upload(client, headers, fakes):
    assert _upload(client, headers, "alice").status_code == 403
    assert fakes["ingested"] == []


def test_hr_can_upload_for_hr_department(client, headers, fakes):
    r = _upload(client, headers, "hannah")
    assert r.status_code == 200
    assert r.json()["status"] == "added"
    assert fakes["ingested"] == ["HR-TEST-001"]


def test_hr_cannot_upload_for_another_department(client, headers, fakes):
    assert _upload(client, headers, "hannah", _form(department="IT")).status_code == 403
    assert fakes["ingested"] == []


def test_hr_cannot_overwrite_another_departments_document(client, headers, fakes):
    fakes["existing"]["IT-SUP-001"] = {"department": "IT", "visibility": "all"}
    r = _upload(client, headers, "hannah", _form(doc_id="IT-SUP-001", department="HR"))
    assert r.status_code == 403
    assert fakes["ingested"] == []


def test_admin_can_upload_for_any_department(client, headers, fakes):
    assert _upload(client, headers, "root", _form(department="IT")).status_code == 200


def test_non_pdf_is_rejected(client, headers, fakes):
    assert _upload(client, headers, "hannah", content=b"just text").status_code == 400
    assert _upload(client, headers, "hannah", name="notes.txt").status_code == 400


def test_bad_metadata_is_rejected(client, headers, fakes):
    assert (
        _upload(client, headers, "hannah", _form(visibility="public")).status_code
        == 422
    )
    assert (
        _upload(
            client, headers, "hannah", _form(effective_date="01/04/2026")
        ).status_code
        == 422
    )
    assert fakes["ingested"] == []


def test_listing_uses_the_callers_visibility(client, headers, monkeypatch):
    seen = []

    def fake_metadatas(allowed):
        seen.append(list(allowed))
        return [
            {
                "doc_id": "IT-SUP-001",
                "title": "IT Helpdesk",
                "department": "IT",
                "visibility": "all",
                "version": "2.1",
                "effective_date": "2026-04-01",
            }
        ]

    monkeypatch.setattr(documents_api, "_company_metadatas", fake_metadatas)
    alice = client.get("/documents", headers=headers("alice")).json()["documents"]
    hannah = client.get("/documents", headers=headers("hannah")).json()["documents"]
    assert seen == [["all"], ["all", "hr_only"]]  # each caller got the right filter
    assert alice[0]["can_manage"] is False
    assert hannah[0]["can_manage"] is False  # HR cannot manage IT documents


def test_delete_rules(client, headers, fakes):
    fakes["existing"]["IT-SUP-001"] = {"department": "IT", "visibility": "all"}
    fakes["existing"]["HR-CONF-001"] = {"department": "HR", "visibility": "hr_only"}
    fakes["existing"]["HR-POL-001"] = {"department": "HR", "visibility": "all"}

    assert (
        client.delete("/documents/IT-SUP-001", headers=headers("alice")).status_code
        == 403
    )
    assert (
        client.delete("/documents/IT-SUP-001", headers=headers("hannah")).status_code
        == 403
    )
    assert (
        client.delete("/documents/HR-CONF-001", headers=headers("root")).status_code
        == 404
    )  # admin can't see it
    assert (
        client.delete("/documents/NOPE-001", headers=headers("root")).status_code == 404
    )
    assert fakes["deleted"] == []  # nothing was deleted so far

    assert (
        client.delete("/documents/HR-POL-001", headers=headers("hannah")).status_code
        == 200
    )
    assert fakes["deleted"] == [{"doc_id": "HR-POL-001"}]
