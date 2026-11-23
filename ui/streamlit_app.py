import uuid

import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.title("Document Agent")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.caption(f"Conversation: {st.session_state.thread_id[:8]}")
    if st.button("New chat"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    pdf = st.file_uploader("Upload a PDF", type=["pdf"])
    if pdf and st.button("Index PDF"):
        r = requests.post(
            f"{API}/upload",
            params={"thread_id": st.session_state.thread_id},
            files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
        )
        if r.ok:
            st.success(f"Indexed {r.json()['chunks']} chunks")
        else:
            st.error(r.json().get("detail", "Upload failed"))

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask about your document"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    def stream():
        with requests.post(
            f"{API}/chat",
            json={"thread_id": st.session_state.thread_id, "message": prompt},
            stream=True,
        ) as r:
            r.raise_for_status()
            r.encoding = "utf-8"
            for piece in r.iter_content(chunk_size=None, decode_unicode=True):
                if piece:
                    yield piece

    with st.chat_message("assistant"):
        reply = st.write_stream(stream())
    st.session_state.messages.append({"role": "assistant", "content": reply})
