from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}


class Note(BaseModel):
    text: str


@app.post("/shout")
def shout(note: Note):
    return {"shouted_text": note.text.upper()}
