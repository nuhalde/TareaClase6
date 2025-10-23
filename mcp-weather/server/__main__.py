"""
Re-export the server entrypoint from the internal package.
"""

from __future__ import annotations

from .server.__main__ import main

if __name__ == "__main__":
    main()
