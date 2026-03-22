"""Start the standalone story backend FastAPI service."""

from __future__ import annotations

import os

import uvicorn


def _chdir_to_backend_root() -> str:
    """Ensure relative paths resolve from backend root."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    return os.getcwd()


def main() -> None:
    working_dir = _chdir_to_backend_root()
    print(f"Story backend working directory: {working_dir}")

    uvicorn.run(
        "api.app:app",
        host=os.getenv("STORY_API_HOST", "0.0.0.0"),
        port=int(os.getenv("STORY_API_PORT", "8000")),
        reload=os.getenv("STORY_API_RELOAD", "true").lower() == "true",
    )


if __name__ == "__main__":
    main()
