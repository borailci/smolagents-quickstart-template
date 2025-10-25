"""
Task model
"""


class Task:
    """
    Represents a task in the system.

    Attributes:
        id: Unique task identifier
        title: Task title
        description: Detailed task description
        status: Current task status (todo, in_progress, completed)
        project_id: Associated project
        assigned_to: User ID task is assigned to
        created_at: Timestamp when task was created
        updated_at: Timestamp of last update
    """

    def __init__(self, id, title, description, status, project_id,
                 assigned_to, created_at, updated_at):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.project_id = project_id
        self.assigned_to = assigned_to
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        """Convert task to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'project_id': self.project_id,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"
