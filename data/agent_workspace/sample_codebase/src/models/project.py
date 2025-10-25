"""
Project model
"""


class Project:
    """
    Represents a project in the system.

    Attributes:
        id: Unique project identifier
        name: Project name
        description: Project description
        owner_id: User ID of project owner
        status: Project status (active, archived)
        created_at: Timestamp when project was created
        updated_at: Timestamp of last update
    """

    def __init__(self, id, name, description, owner_id, status,
                 created_at, updated_at):
        self.id = id
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        """Convert project to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def is_active(self):
        """Check if project is active"""
        return self.status == 'active'

    def __repr__(self):
        return f"<Project {self.id}: {self.name}>"
