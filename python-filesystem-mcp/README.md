# Python Filesystem MCP Server

A Python-based Model Context Protocol (MCP) server implementation that provides filesystem operations through a REST API. This server fully implements the MCP specification.

## Features

- Full MCP v1 protocol compliance
- File and directory context retrieval
- File creation and modification
- Path validation and security
- Configurable allowed paths
- Read-only mode support

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn server:app --host 127.0.0.1 --port 8000
```

The server will start on `http://127.0.0.1:8000`. By default, it will serve files from the current directory.

### Development Mode

For development, you can use uvicorn's auto-reload feature:
```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

This will automatically restart the server when code changes are detected.

## API Endpoints

### MCP Protocol Endpoints
- `GET /mcp/v1/context/{path}` - Get context for a file or directory
- `POST /mcp/v1/context/{path}` - Update or create file context

## Configuration

The server supports the following configuration:
- `allowed_paths`: List of allowed filesystem paths
- `read_only`: Enable read-only mode
- `max_file_size_mb`: Maximum allowed file size in megabytes
- `exclude_patterns`: Patterns to exclude from operations

## Security Notes

1. Path Security:
   - All paths are validated against allowed directories
   - Symlinks are checked to prevent access outside allowed paths
   - Parent directory access is controlled

2. Best Practices:
   - Run in a controlled environment
   - Use read-only mode when possible
   - Configure allowed paths appropriately
   - Keep dependencies updated
