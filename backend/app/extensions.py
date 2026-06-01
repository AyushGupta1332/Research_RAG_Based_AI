"""
Research Agent — Flask Extension Instances

Extensions are instantiated here (without app binding) so they can be
imported anywhere without circular imports. They're initialized in
the app factory via init_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

# Database ORM
db = SQLAlchemy()

# JWT Authentication
jwt = JWTManager()

# Database Migrations
migrate = Migrate()
