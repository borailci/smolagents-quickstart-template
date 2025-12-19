from pathlib import Path
from typing import List

from smolagents import Tool

from config import settings

# Use centralized config
MIN_WRITE_CHARS = settings.MIN_WRITE_CHARS


def build_validator_tools(target_root: Path) -> List[Tool]:
    """Build tools for the Validator Agent to read and overwrite files in the target directory."""
    
    class ReadFileTool(Tool):
        name = "read_file"
        description = "Read the content of a file to validate."
        inputs = {"filename": {"type": "string", "description": "Name of the file to read."}}
        output_type = "string"

        def forward(self, filename: str) -> str:
            # Security: prevent path traversal
            if ".." in filename or filename.startswith("/"):
                return "Error: Invalid filename. Path traversal not allowed."
            
            path = target_root / filename
            if not path.exists():
                return f"Error: File {filename} not found."
            return path.read_text(encoding="utf-8")

    class WriteFileTool(Tool):
        name = "write_file"
        description = "Overwrite the file with fixed content."
        inputs = {
            "filename": {"type": "string", "description": "Name of the file to write."},
            "content": {"type": "string", "description": "The fixed content."}
        }
        output_type = "string"

        def forward(self, filename: str, content: str) -> str:
            # Security: prevent path traversal
            if ".." in filename or filename.startswith("/"):
                return "Error: Invalid filename. Path traversal not allowed."
            
            if len(content.strip()) < MIN_WRITE_CHARS:
                return f"Error: Content too short ({len(content.strip())} chars). Minimum: {MIN_WRITE_CHARS}. Please write the FULL file content."
            
            path = target_root / filename
            path.write_text(content, encoding="utf-8")
            return f"Successfully updated {filename}."

    return [ReadFileTool(), WriteFileTool()]

