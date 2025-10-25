"""
Task endpoints
"""

from flask import Blueprint, request, jsonify
from src.models.task import Task
from src.utils.validators import validate_task
from src.utils.helpers import get_timestamp

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

# In-memory storage for demo purposes
tasks_store = {}
next_task_id = 1


@tasks_bp.route('', methods=['GET'])
def list_tasks():
    """List all tasks"""
    return jsonify({
        'tasks': list(tasks_store.values()),
        'total': len(tasks_store)
    }), 200


@tasks_bp.route('', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.get_json()

    # Validate input
    is_valid, error = validate_task(data)
    if not is_valid:
        return jsonify({'error': error, 'code': 'VALIDATION_ERROR'}), 400

    global next_task_id
    task = Task(
        id=next_task_id,
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'todo'),
        project_id=data.get('project_id'),
        assigned_to=data.get('assigned_to'),
        created_at=get_timestamp(),
        updated_at=get_timestamp()
    )

    tasks_store[next_task_id] = task.__dict__
    next_task_id += 1

    return jsonify({
        'message': 'Task created successfully',
        'task': task.__dict__
    }), 201


@tasks_bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get task details"""
    if task_id not in tasks_store:
        return jsonify({
            'error': 'Task not found',
            'code': 'TASK_NOT_FOUND'
        }), 404

    return jsonify(tasks_store[task_id]), 200


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task"""
    if task_id not in tasks_store:
        return jsonify({
            'error': 'Task not found',
            'code': 'TASK_NOT_FOUND'
        }), 404

    data = request.get_json()
    task = tasks_store[task_id]

    # Update allowed fields
    if 'title' in data:
        task['title'] = data['title']
    if 'description' in data:
        task['description'] = data['description']
    if 'status' in data:
        if data['status'] not in ['todo', 'in_progress', 'completed']:
            return jsonify({
                'error': 'Invalid status',
                'code': 'INVALID_STATUS'
            }), 400
        task['status'] = data['status']
    if 'assigned_to' in data:
        task['assigned_to'] = data['assigned_to']

    task['updated_at'] = get_timestamp()

    return jsonify({
        'message': 'Task updated successfully',
        'task': task
    }), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task"""
    if task_id not in tasks_store:
        return jsonify({
            'error': 'Task not found',
            'code': 'TASK_NOT_FOUND'
        }), 404

    deleted_task = tasks_store.pop(task_id)

    return jsonify({
        'message': 'Task deleted successfully',
        'task': deleted_task
    }), 200
