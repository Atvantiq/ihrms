from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.observability import RequestContextMiddleware, configure_logging
from app.core.ratelimit import limiter

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Atvantiq People — iHRMS API. Shares the ONAQT Supabase Postgres: "
    "reads/writes the public employee cluster per blueprint doc 24; all iHRMS "
    "tables live in the `ihrms` schema.",
)

# Rate limiting
app.state.limiter = limiter
# slowapi's handler signature is narrower than Starlette's generic type
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# Request correlation IDs + structured access logs (outermost)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Consistent error envelope, no stack-trace leaks
register_error_handlers(app)

app.include_router(api_router)
