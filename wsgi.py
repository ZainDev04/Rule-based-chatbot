"""
Root entrypoint for Vercel.

Vercel's Python preset looks for wsgi.py (among others) at the project root
and loads the top-level `app` variable as the function handler. The real
application lives in web/app.py; this file only re-exports it.
"""

from web.app import app  # noqa: F401
