"""
User model
"""


class User:
    """
    Represents a user in the system.

    Attributes:
        id: Unique user identifier
        name: User's full name
        email: User's email address
        role: User role (admin, member)
        active: Whether user account is active
        created_at: Timestamp when user was created
    """

    def __init__(self, id, name, email, role, active, created_at):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.active = active
        self.created_at = created_at

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at
        }

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def __repr__(self):
        return f"<User {self.id}: {self.name}>"
