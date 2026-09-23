from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.data import load_profiles
from app.matching import MatchRequest, dataset_options, match

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    app.state.profiles = load_profiles()
    yield


app = FastAPI(title="Умный подбор подрядчиков", lifespan=lifespan)


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
