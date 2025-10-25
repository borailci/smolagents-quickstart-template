"""
Authentication middleware
"""

from functools import wraps
from flask import request, jsonify


def require_auth(f):
    """
    Simple authentication decorator.
    In production, would validate JWT tokens or similar.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Missing authorization header',
                'code': 'MISSING_AUTH'
            }), 401

        # In production, validate token here
        # For demo purposes, just check header exists

        return f(*args, **kwargs)

    return decorated_function
