import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.data import load_profiles
from app.matching import MatchRequest, dataset_options, match
from app.llm import parse_request

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.profiles = load_profiles()
    yield


app = FastAPI(title="Умный подбор подрядчиков", lifespan=lifespan)


class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=500, strict=True)


@app.post("/parse")
def parse_order(request: ParseRequest):
    parsed = parse_request(request.text, dataset_options(app.state.profiles), timeout_s=8)
    if parsed is None:
        configured = all(os.getenv(name, "").strip() for name in ("OPENAI_API_KEY", "OPENAI_MODEL"))
        error = ("Не удалось разобрать текст: AI не ответил вовремя или вернул некорректный ответ; "
                 "заполните форму вручную" if configured else
                 "Разбор текста доступен только с ключом OpenAI и моделью (OPENAI_API_KEY, OPENAI_MODEL); "
                 "заполните форму")
        return {"fields": None, "missing": [], "error": error}
    return {"fields": {key: value for key, value in parsed.items() if key != "missing"},
            "missing": parsed["missing"], "source": "llm"}


@app.get("/health")
def health():
    return {"status": "ok", "profiles": len(app.state.profiles)}


@app.get("/options")
def options():
    return dataset_options(app.state.profiles)


@app.post("/match")
def find_contractors(request: MatchRequest):
    return match(request, app.state.profiles)


@app.get("/", response_class=FileResponse)
def index():
    return FileResponse(ROOT / "web/index.html")
