import os
from typing import List
from dotenv import load_dotenv
from smolagents import tool, Tool
from langchain_community.agent_toolkits import FileManagementToolkit

load_dotenv()
AGENT_WORKSPACE_PATH = os.getenv("AGENT_WORKSPACE_PATH")


# ========== Get Langchain tools and convert to SmolAgents tools ==========
langchain_tools = FileManagementToolkit(
    root_dir=AGENT_WORKSPACE_PATH,
    selected_tools=["list_directory", "read_file", "write_file", "file_search"],
).get_tools()

list_directory_tool, read_file_tool, write_file_tool, file_search_tool = langchain_tools


# ===================== Converted Tools ============================
@tool
def list_workspace_dir() -> List[str]:
    """
    Lists the directories in the agent's workspace.

    Returns:
        List[str]: A list of directory names available in the agent's workspace.
    """
    return list_directory_tool.invoke(input={})


@tool
def read_file(file_path: str) -> List[str]:
    """
    Reads the contents of a file specified by the given file path.

    Args:
        file_path (str): The path to the file to be read.

    Returns:
        List[str]: A list of strings representing the lines or contents of the file.
    """
    return read_file_tool.invoke(input={"file_path": file_path})


@tool
def write_file(file_path: str, text: str, append: bool = False) -> bool:
    """
    Writes the given text to a file specified by the file path.

    Args:
        file_path (str): The path to the file to be written.
        text (str): The text to be written to the file.
        append (bool): Whether to append to an existing file. Defaults to False.

    Returns:
        bool: True if the file was written successfully, False otherwise.
    """
    return write_file_tool.invoke(input={"file_path": file_path, "text": text, "append": append})


@tool
def file_search(pattern: str) -> List[str]:
    """
    Searches for files matching a Unix shell-style pattern.

    Args:
        pattern (str): A Unix shell-style pattern for matching file or directory names.
            Use '*' to match any sequence of characters.

    Returns:
        List[str]: A list of matching file paths.
    """
    return file_search_tool.invoke(input={"pattern": pattern})


# ================== Custom Tools ================================
@tool
def get_tree(root_path: str) -> List[str]:
    """
    Lists the directories and files in the agent's workspace, starting from the given root path, formatted as a tree.

    The root is always the agent's workspace root ("."), and only relative paths from this root are allowed.
    The tool will not traverse outside the workspace root. If an invalid path is provided, an error will be returned.

    Args:
        root_path (str): The relative path from the workspace root from which to list directories and files. Use "." for the root.

    Returns:
        List[str]: A list of strings representing the tree structure.
    """
    base_path = AGENT_WORKSPACE_PATH
    abs_root = os.path.abspath(os.path.join(base_path, root_path))
    # Enforce that abs_root is within base_path
    base_path_abs = os.path.abspath(base_path)
    if not abs_root.startswith(base_path_abs):
        return ["Error: Access outside of agent workspace is not allowed."]

    def tree(dir_path, prefix=""):
        try:
            entries = sorted(os.listdir(dir_path))
        except (PermissionError, OSError):
            return [f"{prefix}[Permission Denied] {os.path.basename(dir_path)}/"]
        entries = [e for e in entries if not e.startswith('.')]
        result = []
        for idx, entry in enumerate(entries):
            path = os.path.join(dir_path, entry)
            connector = "└── " if idx == len(entries) - 1 else "├── "
            if os.path.isdir(path):
                result.append(f"{prefix}{connector}{entry}")
                extension = "    " if idx == len(entries) - 1 else "│   "
                result.extend(tree(path, prefix + extension))
            else:
                result.append(f"{prefix}{connector}{entry}")
        return result

    # Add root dot
    tree_lines = ["."]
    tree_lines.extend(tree(abs_root))
    # Join as a single string, wrap in markdown code block
    tree_str = "\n".join(tree_lines)
    markdown_tree = f"```markdown\n{tree_str}\n```"
    return markdown_tree


# ================== Toolkit Class ============================
class FileSystemToolkit:
    @staticmethod
    def get_tools() -> List[Tool]:
        return [
            read_file,
            write_file,
            file_search,
            list_workspace_dir,
            get_tree,
        ]
