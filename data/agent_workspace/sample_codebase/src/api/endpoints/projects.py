"""
Project endpoints
"""

from flask import Blueprint, request, jsonify
from src.models.project import Project
from src.utils.validators import validate_project
from src.utils.helpers import get_timestamp

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

# In-memory storage for demo purposes
projects_store = {}
next_project_id = 1


@projects_bp.route('', methods=['GET'])
def list_projects():
    """List all projects"""
    return jsonify({
        'projects': list(projects_store.values()),
        'total': len(projects_store)
    }), 200


@projects_bp.route('', methods=['POST'])
def create_project():
    """Create a new project"""
    data = request.get_json()

    # Validate input
    is_valid, error = validate_project(data)
    if not is_valid:
        return jsonify({'error': error, 'code': 'VALIDATION_ERROR'}), 400

    global next_project_id
    project = Project(
        id=next_project_id,
        name=data['name'],
        description=data.get('description', ''),
        owner_id=data.get('owner_id'),
        status=data.get('status', 'active'),
        created_at=get_timestamp(),
        updated_at=get_timestamp()
    )

    projects_store[next_project_id] = project.__dict__
    next_project_id += 1

    return jsonify({
        'message': 'Project created successfully',
        'project': project.__dict__
    }), 201


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    if project_id not in projects_store:
        return jsonify({
            'error': 'Project not found',
            'code': 'PROJECT_NOT_FOUND'
        }), 404

    return jsonify(projects_store[project_id]), 200


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project"""
    if project_id not in projects_store:
        return jsonify({
            'error': 'Project not found',
            'code': 'PROJECT_NOT_FOUND'
        }), 404

    data = request.get_json()
    project = projects_store[project_id]

    # Update allowed fields
    if 'name' in data:
        project['name'] = data['name']
    if 'description' in data:
        project['description'] = data['description']
    if 'status' in data:
        if data['status'] not in ['active', 'archived']:
            return jsonify({
                'error': 'Invalid status',
                'code': 'INVALID_STATUS'
            }), 400
        project['status'] = data['status']

    project['updated_at'] = get_timestamp()

    return jsonify({
        'message': 'Project updated successfully',
        'project': project
    }), 200


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete project"""
    if project_id not in projects_store:
        return jsonify({
            'error': 'Project not found',
            'code': 'PROJECT_NOT_FOUND'
        }), 404

    deleted_project = projects_store.pop(project_id)

    return jsonify({
        'message': 'Project deleted successfully',
        'project': deleted_project
    }), 200
