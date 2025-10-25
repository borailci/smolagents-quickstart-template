"""
Task endpoint tests
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_list_tasks(client):
    """Test listing tasks"""
    response = client.get('/api/tasks')
    assert response.status_code == 200
    assert 'tasks' in response.json


def test_create_task(client):
    """Test creating a task"""
    task_data = {
        'title': 'Test Task',
        'description': 'Test Description',
        'status': 'todo'
    }
    response = client.post('/api/tasks', json=task_data)
    assert response.status_code == 201
    assert response.json['task']['title'] == 'Test Task'


def test_create_task_missing_title(client):
    """Test creating task without title"""
    task_data = {
        'description': 'Test Description'
    }
    response = client.post('/api/tasks', json=task_data)
    assert response.status_code == 400
    assert 'VALIDATION_ERROR' in response.json['code']


def test_get_task(client):
    """Test getting a task"""
    # Create a task first
    task_data = {'title': 'Test Task', 'status': 'todo'}
    create_response = client.post('/api/tasks', json=task_data)
    task_id = create_response.json['task']['id']

    # Get the task
    response = client.get(f'/api/tasks/{task_id}')
    assert response.status_code == 200
    assert response.json['title'] == 'Test Task'


def test_get_nonexistent_task(client):
    """Test getting a nonexistent task"""
    response = client.get('/api/tasks/999')
    assert response.status_code == 404
    assert 'TASK_NOT_FOUND' in response.json['code']


def test_update_task(client):
    """Test updating a task"""
    # Create a task first
    task_data = {'title': 'Original Title', 'status': 'todo'}
    create_response = client.post('/api/tasks', json=task_data)
    task_id = create_response.json['task']['id']

    # Update the task
    update_data = {'title': 'Updated Title', 'status': 'in_progress'}
    response = client.put(f'/api/tasks/{task_id}', json=update_data)
    assert response.status_code == 200
    assert response.json['task']['title'] == 'Updated Title'
    assert response.json['task']['status'] == 'in_progress'


def test_delete_task(client):
    """Test deleting a task"""
    # Create a task first
    task_data = {'title': 'Task to Delete', 'status': 'todo'}
    create_response = client.post('/api/tasks', json=task_data)
    task_id = create_response.json['task']['id']

    # Delete the task
    response = client.delete(f'/api/tasks/{task_id}')
    assert response.status_code == 200
    assert response.json['task']['title'] == 'Task to Delete'

    # Verify task is deleted
    get_response = client.get(f'/api/tasks/{task_id}')
    assert get_response.status_code == 404
