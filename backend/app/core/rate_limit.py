import ipaddress
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_address(request: Request) -> str:
    """Use the rightmost proxy-added address when behind our reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for", "")
    for candidate in reversed(forwarded.split(",")):
        try:
            return str(ipaddress.ip_address(candidate.strip()))
        except ValueError:
            continue
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_address,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI") or None,
)
