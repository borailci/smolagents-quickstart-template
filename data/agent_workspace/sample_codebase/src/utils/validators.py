"""
Input validation utilities
"""


def validate_task(data):
    """
    Validate task input data.

    Args:
        data: Dictionary containing task data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, 'Request body cannot be empty'

    if 'title' not in data:
        return False, 'Task title is required'

    if not isinstance(data['title'], str):
        return False, 'Task title must be a string'

    if len(data['title'].strip()) == 0:
        return False, 'Task title cannot be empty'

    if len(data['title']) > 200:
        return False, 'Task title cannot exceed 200 characters'

    if 'status' in data:
        valid_statuses = ['todo', 'in_progress', 'completed']
        if data['status'] not in valid_statuses:
            return False, f'Status must be one of: {", ".join(valid_statuses)}'

    return True, None


def validate_user(data):
    """
    Validate user input data.

    Args:
        data: Dictionary containing user data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, 'Request body cannot be empty'

    if 'name' not in data:
        return False, 'User name is required'

    if 'email' not in data:
        return False, 'User email is required'

    if not isinstance(data['name'], str):
        return False, 'User name must be a string'

    if not isinstance(data['email'], str):
        return False, 'User email must be a string'

    if '@' not in data['email']:
        return False, 'Invalid email format'

    if 'role' in data:
        valid_roles = ['admin', 'member']
        if data['role'] not in valid_roles:
            return False, f'Role must be one of: {", ".join(valid_roles)}'

    return True, None


def validate_project(data):
    """
    Validate project input data.

    Args:
        data: Dictionary containing project data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, 'Request body cannot be empty'

    if 'name' not in data:
        return False, 'Project name is required'

    if not isinstance(data['name'], str):
        return False, 'Project name must be a string'

    if len(data['name'].strip()) == 0:
        return False, 'Project name cannot be empty'

    if 'status' in data:
        valid_statuses = ['active', 'archived']
        if data['status'] not in valid_statuses:
            return False, f'Status must be one of: {", ".join(valid_statuses)}'

    return True, None
