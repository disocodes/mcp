# Claude MCP Server

A Python-based Model Context Protocol (MCP) server implementation that provides filesystem operations through a REST API. This server fully implements the MCP specification and includes additional enhanced features for file management.

## Features

### MCP Protocol Implementation
- Full MCP v1 protocol compliance
- Context-aware file operations
- Configurable preferences system
- Secure file access controls

### Enhanced File Operations
- Comprehensive file metadata
- Directory tree visualization
- Pattern-based file searching
- File moving and renaming
- Line-based file editing with diff generation
- Multiple file operations support
- Recursive directory operations

### Security Features
- Path validation and normalization
- Symlink security checks
- Configurable allowed paths
- Read-only mode support
- File size limits
- Exclude patterns for sensitive directories

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python server.py [allowed_directory] [additional_directories...]
```

The server will start on `http://localhost:8000`

## API Endpoints

### MCP Protocol Endpoints
- `GET /mcp/v1/context/{path}` - Get context for a file or directory
- `POST /mcp/v1/context/{path}` - Update or create file context
- `GET /mcp/v1/preferences` - Get current preferences
- `PUT /mcp/v1/preferences` - Update preferences

### Enhanced File Operations
- `POST /files/edit` - Edit file with diff generation
- `POST /files/move` - Move or rename files
- `GET /files/search` - Search files by pattern
- `GET /files/tree` - Get directory tree structure

### Legacy Endpoints
- `GET /list/{path}` - List directory contents
- `GET /read/{path}` - Read file contents
- `POST /write/{path}` - Write file
- `DELETE /delete/{path}` - Delete file or directory
- `POST /mkdir/{path}` - Create directory

## Preferences Configuration

The server supports the following preferences:
```json
{
  "max_file_size_mb": 10,
  "allowed_paths": ["/path/to/allowed/directory"],
  "read_only": false,
  "exclude_patterns": ["*.pyc", "__pycache__", ".git"]
}
```

### Preferences Options
- `max_file_size_mb`: Maximum allowed file size in megabytes
- `allowed_paths`: List of allowed filesystem paths
- `read_only`: Enable read-only mode
- `exclude_patterns`: Patterns to exclude from operations

## Security Notes

1. Path Security:
   - All paths are validated against allowed directories
   - Symlinks are checked to prevent access outside allowed paths
   - Parent directory access is controlled

2. Access Control:
   - Use allowed_paths to restrict filesystem access
   - Enable read_only mode to prevent modifications
   - Configure exclude_patterns to protect sensitive files

3. Best Practices:
   - Run in a controlled environment
   - Use the preferences system to enforce security policies
   - Regularly update dependencies for security patches

## Error Handling

The server provides detailed error messages with appropriate HTTP status codes:
- 400: Bad Request (invalid parameters)
- 403: Forbidden (access denied)
- 404: Not Found (file/directory not found)
- 500: Internal Server Error (unexpected errors)

Each error response includes a detailed message to help diagnose the issue.
