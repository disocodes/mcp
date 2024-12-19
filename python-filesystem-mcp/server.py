#!/usr/bin/env python3

import asyncio
import os
import shutil
import stat
import fnmatch
import difflib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Sequence
import json
import logging

import mcp
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import mcp.types as types
from pydantic import BaseModel, Field, FileUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileInfo(BaseModel):
    name: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    created_at: str
    modified_at: str
    permissions: str
    children: Optional[List['FileInfo']] = None

class MCPFileServer(Server):
    def __init__(self, name: str, allowed_paths: List[str]):
        super().__init__(name)
        self.allowed_paths = [os.path.abspath(p) for p in allowed_paths]
        self.read_only = False
        self.max_file_size_mb = 10
        self.exclude_patterns = ["*.pyc", "__pycache__", ".git"]

    def validate_path(self, requested_path: str) -> str:
        """Validate and normalize file path against allowed directories."""
        abs_path = os.path.abspath(requested_path)
        
        if not any(abs_path.startswith(allowed) for allowed in self.allowed_paths):
            raise ValueError(f"Access denied - path outside allowed directories: {abs_path}")
        
        try:
            real_path = os.path.realpath(abs_path)
            if not any(real_path.startswith(allowed) for allowed in self.allowed_paths):
                raise ValueError("Access denied - symlink target outside allowed directories")
            return real_path
        except Exception as e:
            parent_dir = os.path.dirname(abs_path)
            try:
                real_parent = os.path.realpath(parent_dir)
                if not any(real_parent.startswith(allowed) for allowed in self.allowed_paths):
                    raise ValueError("Access denied - parent directory outside allowed directories")
                return abs_path
            except Exception as e:
                raise ValueError(f"Parent directory does not exist: {parent_dir}")

    def get_file_info(self, path: str) -> FileInfo:
        """Get detailed file information."""
        stats = os.stat(path)
        is_dir = os.path.isdir(path)
        
        # Format permissions string
        mode = stats.st_mode
        perms = ''
        for who in 'USR', 'GRP', 'OTH':
            for what in 'R', 'W', 'X':
                if mode & getattr(stat, f'S_I{what}{who}'):
                    perms += what.lower()
                else:
                    perms += '-'
        
        info = FileInfo(
            name=os.path.basename(path),
            type="directory" if is_dir else "file",
            size=None if is_dir else stats.st_size,
            created_at=datetime.fromtimestamp(stats.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stats.st_mtime).isoformat(),
            permissions=perms
        )
        
        if is_dir:
            info.children = []
            try:
                for item in os.listdir(path):
                    if not any(fnmatch.fnmatch(item, pattern) for pattern in self.exclude_patterns):
                        item_path = os.path.join(path, item)
                        info.children.append(self.get_file_info(item_path))
            except PermissionError:
                pass
        
        return info

    def create_unified_diff(self, original: str, modified: str, filepath: str = 'file') -> str:
        """Create a unified diff between two texts."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f'a/{filepath}',
            tofile=f'b/{filepath}',
            lineterm=''
        )
        
        return ''.join(diff)

    @Server.list_tools()
    async def handle_list_tools(self) -> List[types.Tool]:
        """List available filesystem tools."""
        return [
            types.Tool(
                name="read_file",
                description="Read the contents of a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"}
                    },
                    "required": ["path"]
                }
            ),
            types.Tool(
                name="write_file",
                description="Write content to a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "content": {"type": "string", "description": "Content to write"}
                    },
                    "required": ["path", "content"]
                }
            ),
            types.Tool(
                name="list_directory",
                description="List contents of a directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the directory"}
                    },
                    "required": ["path"]
                }
            ),
            types.Tool(
                name="move_file",
                description="Move or rename a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source path"},
                        "destination": {"type": "string", "description": "Destination path"}
                    },
                    "required": ["source", "destination"]
                }
            ),
            types.Tool(
                name="search_files",
                description="Search for files matching a pattern",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "root_path": {"type": "string", "description": "Root path to search from"},
                        "pattern": {"type": "string", "description": "Search pattern"},
                        "recursive": {"type": "boolean", "description": "Search recursively"}
                    },
                    "required": ["root_path", "pattern"]
                }
            )
        ]

    @Server.call_tool()
    async def handle_call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool calls."""
        try:
            if name == "read_file":
                path = self.validate_path(arguments["path"])
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return [types.TextContent(type="text", text=content)]

            elif name == "write_file":
                if self.read_only:
                    raise ValueError("Server is in read-only mode")
                path = self.validate_path(arguments["path"])
                content = arguments["content"]
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return [types.TextContent(type="text", text=f"Successfully wrote to {path}")]

            elif name == "list_directory":
                path = self.validate_path(arguments["path"])
                info = self.get_file_info(path)
                return [types.TextContent(type="text", text=json.dumps(info.dict(), indent=2))]

            elif name == "move_file":
                if self.read_only:
                    raise ValueError("Server is in read-only mode")
                source = self.validate_path(arguments["source"])
                dest = self.validate_path(arguments["destination"])
                if os.path.exists(dest):
                    raise ValueError("Destination already exists")
                shutil.move(source, dest)
                return [types.TextContent(type="text", text=f"Moved {source} to {dest}")]

            elif name == "search_files":
                root = self.validate_path(arguments["root_path"])
                pattern = arguments["pattern"]
                recursive = arguments.get("recursive", True)
                
                matches = []
                if recursive:
                    for root, _, files in os.walk(root):
                        if any(fnmatch.fnmatch(os.path.basename(root), p) for p in self.exclude_patterns):
                            continue
                        for file in files:
                            if fnmatch.fnmatch(file.lower(), pattern.lower()):
                                matches.append(os.path.join(root, file))
                else:
                    for item in os.listdir(root):
                        if fnmatch.fnmatch(item.lower(), pattern.lower()):
                            matches.append(os.path.join(root, item))
                
                return [types.TextContent(type="text", text=json.dumps(matches, indent=2))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    # Get allowed directories from command line
    import sys
    if len(sys.argv) < 2:
        print("Usage: python server.py <allowed_directory> [additional_directories...]")
        sys.exit(1)

    allowed_paths = [os.path.abspath(p) for p in sys.argv[1:]]
    for path in allowed_paths:
        if not os.path.isdir(path):
            print(f"Error: {path} is not a directory")
            sys.exit(1)

    # Create and run server
    server = MCPFileServer("mcp-filesystem", allowed_paths)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-filesystem",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
