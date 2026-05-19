# agent-ui VS Code Extension

## What It Does
- Adds a VS Code command that sends your requirement to the local agent API.
- Provides a context menu entry and a keyboard shortcut for quick access.

## Usage
1. Start the backend API in the workspace root:
	- `python server.py`
2. In VS Code, trigger the command:
	- Command Palette: `agent-ui: 生成代码`
	- Shortcut: `Ctrl+Alt+G` (Windows/Linux), `Cmd+Alt+G` (macOS)
	- Editor context menu: `生成代码`

## API Endpoint
The extension calls `http://127.0.0.1:8000/generate` with a JSON body containing `requirement`.

## Settings
- `agent-ui.baseUrl`: override the backend base URL if the service is not on `127.0.0.1:8000`.
- `agent-ui.timeoutMs`: request timeout in milliseconds (default: 15000).