# software-agent

## IDE Integration
This project provides a VS Code extension under the [extension](extension) folder. The extension registers a command that calls the local agent API, with a shortcut and editor context menu entry.

Quick start:
1. Start the backend: `python server.py`
2. In VS Code, run the command `agent-ui: 生成代码` (or `Ctrl+Alt+G`).