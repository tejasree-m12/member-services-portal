"""Entry point for the web server.

Development:  flask --app wsgi run --debug
Production:   gunicorn wsgi:app
"""
from dotenv import load_dotenv

load_dotenv()  # read backend/.env before the config module looks at os.environ

from app import create_app  # noqa: E402  (must come after load_dotenv)

app = create_app()
