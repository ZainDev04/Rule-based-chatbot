"""
WSGI entry point for PythonAnywhere (or any WSGI host).

In the PythonAnywhere "Web" tab, point the WSGI configuration file at this
module, or paste the following into the generated file:

    import sys
    sys.path.insert(0, "/home/<username>/Rule-based-chatbot/web")
    from wsgi import application
"""

from app import app as application  # noqa: F401
