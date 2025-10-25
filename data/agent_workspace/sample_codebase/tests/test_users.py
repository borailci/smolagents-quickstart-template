"""
User endpoint tests
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


def test_list_users(client):
    """Test listing users"""
    response = client.get('/api/users')
    assert response.status_code == 200
    assert 'users' in response.json


def test_create_user(client):
    """Test creating a user"""
    user_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'role': 'member'
    }
    response = client.post('/api/users', json=user_data)
    assert response.status_code == 201
    assert response.json['user']['name'] == 'John Doe'
    assert response.json['user']['email'] == 'john@example.com'


def test_create_user_missing_email(client):
    """Test creating user without email"""
    user_data = {
        'name': 'John Doe'
    }
    response = client.post('/api/users', json=user_data)
    assert response.status_code == 400
    assert 'VALIDATION_ERROR' in response.json['code']


def test_create_user_invalid_email(client):
    """Test creating user with invalid email"""
    user_data = {
        'name': 'John Doe',
        'email': 'invalid-email',
        'role': 'member'
    }
    response = client.post('/api/users', json=user_data)
    assert response.status_code == 400


def test_get_user(client):
    """Test getting a user"""
    # Create a user first
    user_data = {'name': 'Jane Doe', 'email': 'jane@example.com'}
    create_response = client.post('/api/users', json=user_data)
    user_id = create_response.json['user']['id']

    # Get the user
    response = client.get(f'/api/users/{user_id}')
    assert response.status_code == 200
    assert response.json['name'] == 'Jane Doe'


def test_update_user(client):
    """Test updating a user"""
    # Create a user first
    user_data = {'name': 'Original Name', 'email': 'original@example.com'}
    create_response = client.post('/api/users', json=user_data)
    user_id = create_response.json['user']['id']

    # Update the user
    update_data = {'name': 'Updated Name', 'role': 'admin'}
    response = client.put(f'/api/users/{user_id}', json=update_data)
    assert response.status_code == 200
    assert response.json['user']['name'] == 'Updated Name'
    assert response.json['user']['role'] == 'admin'


def test_delete_user(client):
    """Test deleting a user"""
    # Create a user first
    user_data = {'name': 'User to Delete', 'email': 'delete@example.com'}
    create_response = client.post('/api/users', json=user_data)
    user_id = create_response.json['user']['id']

    # Delete the user
    response = client.delete(f'/api/users/{user_id}')
    assert response.status_code == 200

    # Verify user is deleted
    get_response = client.get(f'/api/users/{user_id}')
    assert get_response.status_code == 404
