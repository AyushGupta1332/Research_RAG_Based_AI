"""
Research Agent — Flask Application Factory

Creates and configures the Flask application using the factory pattern.
This allows for easy testing and multiple configurations.
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from .config import config_by_name
from .extensions import db, jwt, migrate
from .middleware.logging_middleware import setup_logging, RequestLoggingMiddleware


def create_app(config_name=None):
    """
    Application factory for creating the Flask app.
    
    Args:
        config_name: Configuration to use ('development', 'testing', 'production').
                     Defaults to FLASK_ENV environment variable.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(
        __name__,
        static_folder='../../frontend/static',
        template_folder='../../frontend/templates'
    )

    # Load configuration
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    _init_extensions(app)

    # Setup logging
    setup_logging(app)

    # Setup CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Add request logging middleware
    app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register health check
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'research-agent',
            'version': '0.1.0'
        }), 200

    app.logger.info(f"Research Agent started in {config_name} mode")

    return app


def _init_extensions(app):
    """Initialize Flask extensions."""
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Create tables if they don't exist (dev convenience)
    with app.app_context():
        # Import models so they're registered with SQLAlchemy
        from .models import User, Paper, PaperSection, Chunk, PaperExtraction, ResearchSession, ResearchMessage  # noqa: F401
        db.create_all()

        # Pre-load embedding and reranker models on the main thread
        # to initialize CUDA resources safely and prevent background thread deadlocks.
        if app.config.get('ENV') != 'testing' and not app.config.get('TESTING'):
            try:
                app.logger.info("Pre-loading local embedding and reranker models on main thread...")
                from .services.embedding_service import _load_model
                from .services.reranker_service import _load_reranker
                _load_model()
                _load_reranker()
                app.logger.info("Models pre-loaded successfully.")
            except Exception as e:
                app.logger.warning(f"Model pre-loading skipped or failed: {e}")


def _register_blueprints(app):
    """Register all API blueprints."""
    from .api.auth import auth_bp
    from .api.papers import papers_bp
    from .api.query import query_bp
    from .api.pages import pages_bp
    from .api.sessions import sessions_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(papers_bp, url_prefix='/api/papers')
    app.register_blueprint(query_bp, url_prefix='/api/query')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')
    app.register_blueprint(pages_bp)  # No prefix — serves HTML pages


def _register_error_handlers(app):
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'Resource not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
