"""Legacy story backend startup entrypoint.

Transitional compatibility:
1. preferred entrypoint: ``run_story_api.py``
2. this file stays as a compatibility shell for existing scripts
"""

from __future__ import annotations

import run_story_api


def main() -> None:
    """Delegate to the canonical story entrypoint."""
    run_story_api.main()


if __name__ == "__main__":
    main()
