import os
from dotenv import load_dotenv

load_dotenv()  # loads .env if present (no-op in production where env vars are set directly)

_raw = os.environ.get("SECRET_KEY")
if not _raw:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set.\n"
        "  Local dev:  add SECRET_KEY=... to a .env file in the project root\n"
        "  fly.io:     fly secrets set SECRET_KEY=$(openssl rand -hex 32)"
    )

SECRET_KEY = _raw
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
