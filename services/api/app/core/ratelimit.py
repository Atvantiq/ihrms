"""Rate limiting (slowapi). In-memory by default; point at Redis in prod via
RATELIMIT_STORAGE_URI for multi-instance correctness.

Default budget is generous for normal use and exists to blunt brute-force and
runaway clients. Auth-sensitive routes (dev-login, future password login)
should add a tighter per-route limit with @limiter.limit("...").
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["240/minute"],
    storage_uri=get_settings().ratelimit_storage_uri or "memory://",
    headers_enabled=True,
)
