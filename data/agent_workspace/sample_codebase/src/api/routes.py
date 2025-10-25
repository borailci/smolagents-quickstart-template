"""
API route definitions and blueprints
"""

from flask import Blueprint, jsonify
from src.api.endpoints import tasks, users, projects

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Register routes
api_bp.register_blueprint(tasks.tasks_bp)
api_bp.register_blueprint(users.users_bp)
api_bp.register_blueprint(projects.projects_bp)


@api_bp.route('/')
def api_root():
    """API root endpoint"""
    return jsonify({
        'message': 'TaskFlow API v0.1.0',
        'endpoints': {
            'tasks': '/api/tasks',
            'users': '/api/users',
            'projects': '/api/projects',
            'health': '/health'
        }
    }), 200
