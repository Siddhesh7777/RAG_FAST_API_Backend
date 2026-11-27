import os
from datetime import date

import requests
import streamlit as st

API = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Kestrel Assistant", layout="wide")


def logout():
    for key in ("token", "me", "thread_id", "messages"):
        st.session_state.pop(key, None)


def api(method, path, **kwargs):
    """Every call to the backend goes through here, so the token is always attached."""
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    r = requests.request(method, f"{API}{path}", headers=headers, timeout=60, **kwargs)
    if r.status_code == 401:  # token expired or invalid: back to the login screen
        logout()
        st.rerun()
    return r


def nice_error(r):
    try:
        detail = r.json().get("detail", r.text)
    except Exception:
        return r.text
    return "; ".join(detail) if isinstance(detail, list) else str(detail)


def login_screen():
    st.title("Kestrel Assistant")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        r = requests.post(
            f"{API}/auth/login",
            data={"username": username, "password": password},
            timeout=30,
        )
        if r.ok:
            st.session_state.token = r.json()["access_token"]
            st.session_state.me = api(
                "GET", "/auth/me"
            ).json()  # role, department, visibility
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()
        else:
            st.error("Incorrect username or password")


def open_thread(thread_id):
    r = api("GET", f"/threads/{thread_id}/messages")  # the server checks ownership
    st.session_state.thread_id = thread_id
    st.session_state.messages = r.json() if r.ok else []


def chat_page():
    st.title("Ask about company policy")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask an HR, IT or finance question")
    if not prompt:
        return

    # The conversation is created on the first question, by the server.
    if not st.session_state.thread_id:
        st.session_state.thread_id = api("POST", "/threads").json()["thread_id"]
    thread_id = st.session_state.thread_id

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    def stream():
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        with requests.post(
            f"{API}/chat",
            json={"thread_id": thread_id, "message": prompt},
            headers=headers,
            stream=True,
            timeout=120,
        ) as r:
            if r.status_code != 200:
                yield f"Error: {nice_error(r)}"
                return
            r.encoding = "utf-8"
            for piece in r.iter_content(chunk_size=None, decode_unicode=True):
                if piece:
                    yield piece

    with st.chat_message("assistant"):
        reply = st.write_stream(stream())
    st.session_state.messages.append({"role": "assistant", "content": reply})


def documents_page(me):
    st.title("Company documents")
    r = api("GET", "/documents")
    docs = r.json().get("documents", []) if r.ok else []
    if not docs:
        st.info("No documents found.")
    for d in docs:
        cols = st.columns([5, 2, 2, 1])
        cols[0].write(f"**{d['title']}**  \n{d['doc_id']} · v{d['version']}")
        cols[1].write(d["department"])
        cols[2].write(d["visibility"])
        # The server decides can_manage. The UI only shows or hides the button.
        if d["can_manage"] and cols[3].button("Delete", key=f"del-{d['doc_id']}"):
            res = api("DELETE", f"/documents/{d['doc_id']}")
            st.success("Deleted") if res.ok else st.error(nice_error(res))
            st.rerun()

    if me["role"] not in ("hr", "admin"):
        return  # employees never see the upload form

    st.divider()
    st.subheader("Upload or replace a document")
    with st.form("upload", clear_on_submit=True):
        pdf = st.file_uploader("PDF file", type=["pdf"])
        c1, c2 = st.columns(2)
        doc_id = c1.text_input(
            "Document ID (reuse an ID to replace)", placeholder="HR-POL-007"
        )
        title = c2.text_input("Title")
        c3, c4, c5 = st.columns(3)
        department = c3.text_input("Department", value=me["department"])
        visibility = c4.selectbox("Visibility", ["all", "hr_only"])
        version = c5.text_input("Version", value="1.0")
        effective = st.date_input("Effective hast", value=date.today())
        submitted = st.form_submit_button("Upload")
    if submitted:
        if not pdf:
            st.error("Choose a PDF first")
            return
        res = api(
            "POST",
            "/documents",
            files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
            data={
                "doc_id": doc_id,
                "title": title,
                "department": department,
                "visibility": visibility,
                "version": version,
                "effective_date": effective.isoformat(),
            },
        )
        if res.ok:
            st.success(f"{res.json()['doc_id']}: {res.json()['status']}")
        else:
            st.error(nice_error(res))


# ---- main flow: login first, then the app ----
if "token" not in st.session_state:
    login_screen()
    st.stop()  # nothing below runs until the user is logged in

me = st.session_state.me
with st.sidebar:
    st.write(f"**{me['username']}** ({me['role']})")
    if st.button("Log out"):
        logout()
        st.rerun()
    page = st.radio("Page", ["Chat", "Documents"])
    if page == "Chat":
        if st.button("New chat", use_container_width=True):
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()
        st.subheader("Your conversations")
        for t in api("GET", "/threads").json():
            if st.button(t["title"], key=t["thread_id"], use_container_width=True):
                open_thread(t["thread_id"])
                st.rerun()

if page == "Chat":
    chat_page()
else:
    documents_page(me)
