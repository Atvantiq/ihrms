from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings

app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
    description="Atvantiq People — iHRMS API. Shares the ONAQT Supabase Postgres: "
    "reads/writes the public employee cluster per blueprint doc 24; all iHRMS "
    "tables live in the `ihrms` schema.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
