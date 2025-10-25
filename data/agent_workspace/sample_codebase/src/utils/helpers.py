"""
Helper functions
"""

from datetime import datetime


def get_timestamp():
    """
    Get current timestamp in ISO 8601 format.

    Returns:
        String representation of current UTC time
    """
    return datetime.utcnow().isoformat() + 'Z'


def format_response(message, data=None, status_code=200):
    """
    Format a standardized API response.

    Args:
        message: Response message
        data: Response data (optional)
        status_code: HTTP status code

    Returns:
        Dictionary formatted response
    """
    response = {
        'message': message,
        'status': status_code
    }
    if data:
        response['data'] = data
    return response


def paginate(items, page=1, per_page=10):
    """
    Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Dictionary with paginated results
    """
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page
    }


def filter_dict(data, allowed_keys):
    """
    Filter dictionary to only include allowed keys.

    Args:
        data: Dictionary to filter
        allowed_keys: List of keys to keep

    Returns:
        Filtered dictionary
    """
    return {k: v for k, v in data.items() if k in allowed_keys}
