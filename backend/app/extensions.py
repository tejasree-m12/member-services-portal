"""Flask extensions, created once and attached to the app in ``create_app``.

Keeping them in their own module avoids circular imports: models and routes
import ``db`` from here instead of from the app package.
"""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
