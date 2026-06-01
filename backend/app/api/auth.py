"""
Research Agent — Authentication API Blueprint

Handles user registration, login, token refresh, and profile endpoints.
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)

from ..extensions import db
from ..models.user import User
from ..utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Expects JSON: { "username": str, "email": str, "password": str }
    Returns: User data + access/refresh tokens
    """
    data = request.get_json()

    if not data:
        return error_response('Request body must be JSON', 400)

    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Validation
    errors = []
    if not username or len(username) < 3:
        errors.append('Username must be at least 3 characters')
    if not email or '@' not in email:
        errors.append('Valid email is required')
    if not password or len(password) < 6:
        errors.append('Password must be at least 6 characters')

    if errors:
        return error_response(errors, 400)

    # Check for existing user
    if User.query.filter_by(username=username).first():
        return error_response('Username already taken', 409)
    if User.query.filter_by(email=email).first():
        return error_response('Email already registered', 409)

    # Create user
    user = User(username=username, email=email)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration failed: {e}")
        return error_response('Registration failed', 500)

    # Generate tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    logger.info(f"User registered: {username} ({email})")

    return success_response({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }, 'Registration successful', 201)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user and return tokens.
    
    Expects JSON: { "email": str, "password": str }
    Returns: User data + access/refresh tokens
    """
    data = request.get_json()

    if not data:
        return error_response('Request body must be JSON', 400)

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return error_response('Email and password are required', 400)

    # Find user
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return error_response('Invalid email or password', 401)

    if not user.is_active:
        return error_response('Account is deactivated', 403)

    # Generate tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    logger.info(f"User logged in: {user.username}")

    return success_response({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }, 'Login successful')


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh an access token using a valid refresh token.
    
    Requires: Authorization header with refresh token
    Returns: New access token
    """
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)

    return success_response({
        'access_token': new_access_token
    }, 'Token refreshed')


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get the current authenticated user's profile.
    
    Requires: Authorization header with access token
    Returns: User data
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))

    if not user:
        return error_response('User not found', 404)

    return success_response({
        'user': user.to_dict()
    })
