"""
Research Agent — Standardized API Responses

Provides consistent response formatting across all endpoints.
"""

from flask import jsonify


def success_response(data=None, message='Success', status_code=200):
    """
    Create a standardized success response.
    
    Args:
        data: Response payload (dict or list)
        message: Human-readable message
        status_code: HTTP status code (default 200)
    
    Returns:
        Flask Response object
    """
    response = {
        'status': 'success',
        'message': message
    }
    if data is not None:
        response['data'] = data

    return jsonify(response), status_code


def error_response(message='An error occurred', status_code=400):
    """
    Create a standardized error response.
    
    Args:
        message: Error message (str or list of strings)
        status_code: HTTP status code (default 400)
    
    Returns:
        Flask Response object
    """
    response = {
        'status': 'error',
        'message': message if isinstance(message, str) else message,
    }

    if isinstance(message, list):
        response['errors'] = message
        response['message'] = message[0] if message else 'Validation error'

    return jsonify(response), status_code
