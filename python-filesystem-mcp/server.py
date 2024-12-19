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

from fastapi import FastAPI
import mcp
from mcp.server import Server
from mcp.server.fastapi import create_mcp_router
import mcp.types as types
from pydantic import BaseModel

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

    async def initialize(self) -> None:
        """Initialize the server."""
        logger.info("Initializing MCP File Server...")
        await super().initialize()

    async def shutdown(self) -> None:
        """Shutdown the server."""
        logger.info("Shutting down MCP File Server...")
        await super().shutdown()

    def validate_path(self, requested_path: str) -> str:
        """Validate and normalize file path against allowed directories."""
        abs_path = os.path.abspath(requested_path)
        
        if not any(abs_path.startswith(allowed) for allowed in self.allowed_paths):
            raise ValueError(f"Access denied - path outside allowed directories: {abs_path}")
        
        try:
            real_path = os.path.realpath(abs_path)
            if not any(real_path.startswith(allowed) for allowed in self.allowed_paths):
                raise ValueError(f"Symlink points outside allowed directories: {abs_path}")
            return real_path
        except OSError as e:
            raise ValueError(f"Invalid path: {abs_path}") from e

    async def get_file_info(self, path: str) -> FileInfo:
        """Get detailed file information."""
        path = self.validate_path(path)
        stat_info = os.stat(path)
        
        info = FileInfo(
            name=os.path.basename(path),
            type="directory" if os.path.isdir(path) else "file",
            size=stat_info.st_size if os.path.isfile(path) else None,
            created_at=datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            permissions=stat.filemode(stat_info.st_mode)
        )
        
        if info.type == "directory":
            children = []
            for item in os.listdir(path):
                if not any(fnmatch.fnmatch(item, pattern) for pattern in self.exclude_patterns):
                    try:
                        child_info = await self.get_file_info(os.path.join(path, item))
                        children.append(child_info)
                    except ValueError:
                        continue
            info.children = children
            
        return info

    async def handle_get_context(self, request: mcp.types.GetContextRequest) -> mcp.types.GetContextResponse:
        """Handle get context request."""
        try:
            file_info = await self.get_file_info(request.path)
            return mcp.types.GetContextResponse(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=json.dumps(file_info.dict(), indent=2)
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return mcp.types.GetContextResponse(
                content=[mcp.types.TextContent(type="text", text=f"Error: {str(e)}")]
            )

    async def handle_update_context(self, request: mcp.types.UpdateContextRequest) -> None:
        """Handle update context request."""
        if self.read_only:
            raise ValueError("Server is in read-only mode")
        
        try:
            path = self.validate_path(request.path)
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    f.write("")
        except Exception as e:
            logger.error(f"Error updating context: {str(e)}")
            raise

def create_app() -> FastAPI:
    """Create FastAPI application with MCP routes."""
    app = FastAPI(title="MCP File Server")
    
    # Create MCP server instance
    server = MCPFileServer("mcp-file-server", [os.getcwd()])
    
    # Create and mount MCP router
    mcp_router = create_mcp_router(server)
    app.include_router(mcp_router, prefix="/mcp/v1")
    
    @app.on_event("startup")
    async def startup():
        await server.initialize()
    
    @app.on_event("shutdown")
    async def shutdown():
        await server.shutdown()
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
