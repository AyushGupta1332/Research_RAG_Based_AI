"""
Research Agent — Auth Service

Business logic for authentication operations.
Separates concerns from the API layer.
"""

from ..models.user import User
from ..extensions import db


class AuthService:
    """Authentication service for user management."""

    @staticmethod
    def get_user_by_id(user_id):
        """Get a user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email):
        """Get a user by email."""
        return User.query.filter_by(email=email.lower()).first()

    @staticmethod
    def get_user_by_username(username):
        """Get a user by username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def create_user(username, email, password):
        """
        Create a new user.
        
        Returns:
            tuple: (user, error_message) — user is None if creation failed
        """
        # Check for duplicates
        if User.query.filter_by(username=username).first():
            return None, 'Username already taken'
        if User.query.filter_by(email=email.lower()).first():
            return None, 'Email already registered'

        user = User(username=username, email=email.lower())
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
            return user, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def authenticate(email, password):
        """
        Authenticate a user with email and password.
        
        Returns:
            tuple: (user, error_message) — user is None if auth failed
        """
        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            return None, 'Invalid email or password'
        if not user.check_password(password):
            return None, 'Invalid email or password'
        if not user.is_active:
            return None, 'Account is deactivated'

        return user, None
