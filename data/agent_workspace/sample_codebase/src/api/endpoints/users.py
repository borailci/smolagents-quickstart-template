"""
User endpoints
"""

from flask import Blueprint, request, jsonify
from src.models.user import User
from src.utils.validators import validate_user
from src.utils.helpers import get_timestamp

users_bp = Blueprint('users', __name__, url_prefix='/users')

# In-memory storage for demo purposes
users_store = {}
next_user_id = 1


@users_bp.route('', methods=['GET'])
def list_users():
    """List all users"""
    return jsonify({
        'users': list(users_store.values()),
        'total': len(users_store)
    }), 200


@users_bp.route('', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.get_json()

    # Validate input
    is_valid, error = validate_user(data)
    if not is_valid:
        return jsonify({'error': error, 'code': 'VALIDATION_ERROR'}), 400

    global next_user_id
    user = User(
        id=next_user_id,
        name=data['name'],
        email=data['email'],
        role=data.get('role', 'member'),
        active=data.get('active', True),
        created_at=get_timestamp()
    )

    users_store[next_user_id] = user.__dict__
    next_user_id += 1

    return jsonify({
        'message': 'User created successfully',
        'user': user.__dict__
    }), 201


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details"""
    if user_id not in users_store:
        return jsonify({
            'error': 'User not found',
            'code': 'USER_NOT_FOUND'
        }), 404

    return jsonify(users_store[user_id]), 200


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user"""
    if user_id not in users_store:
        return jsonify({
            'error': 'User not found',
            'code': 'USER_NOT_FOUND'
        }), 404

    data = request.get_json()
    user = users_store[user_id]

    # Update allowed fields
    if 'name' in data:
        user['name'] = data['name']
    if 'email' in data:
        user['email'] = data['email']
    if 'role' in data:
        if data['role'] not in ['admin', 'member']:
            return jsonify({
                'error': 'Invalid role',
                'code': 'INVALID_ROLE'
            }), 400
        user['role'] = data['role']
    if 'active' in data:
        user['active'] = bool(data['active'])

    return jsonify({
        'message': 'User updated successfully',
        'user': user
    }), 200


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user"""
    if user_id not in users_store:
        return jsonify({
            'error': 'User not found',
            'code': 'USER_NOT_FOUND'
        }), 404

    deleted_user = users_store.pop(user_id)

    return jsonify({
        'message': 'User deleted successfully',
        'user': deleted_user
    }), 200
