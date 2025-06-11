# MCP Dynamic Tools

**Drop Python files, get MCP tools instantly.**

A dynamic MCP server that automatically discovers Python files in a directory and exposes them as tools to any MCP-compatible AI client. Created through collaboration between Ben Wilson and Claude (Anthropic).

## ✨ The Magic

```python
# 1. Write a Python file
def invoke(arguments):
    """Generate a secure password
    
    Parameters:
    - length: Length of password (default: 12)
    - include_symbols: Include special characters (default: true)
    """
    import random, string
    length = int(arguments.get('length', 12))
    chars = string.ascii_letters + string.digits
    if arguments.get('include_symbols', 'true').lower() == 'true':
        chars += "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))
```

```bash
# 2. Save it to your tools directory
echo "# Above code" > tools/password_generator.py
```

```
# 3. AI can now use it immediately (after restart in Claude Desktop)
🤖 "Generate a 16-character password with symbols"
🔧 Tool: password_generator(length="16", include_symbols="true")
📤 Result: "K9#mP2$vR8@nQ3!x"
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/your-username/mcp-dynamic-tools
cd mcp-dynamic-tools
```

### 2. Create Tools Directory
```bash
mkdir tools
```

### 3. Configure Your MCP Client

**Claude Desktop** (`~/.config/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "mcp-dynamic-tools": {
      "command": "python3",
      "args": [
        "/path/to/mcp-dynamic-tools/src/mcp_dynamic_tools/server.py",
        "--tools-dir",
        "/path/to/tools"
      ]
    }
  }
}
```

### 4. Create Your First Tool
```python
# tools/hello.py
def invoke(arguments):
    """Say hello to someone
    
    Parameters:
    - name: The person to greet
    """
    name = arguments.get('name', 'World')
    return f"Hello, {name}! 👋"
```

### 5. Restart Your MCP Client
Your `hello` tool is now available to any AI using your MCP client!

## 🛠️ How It Works

1. **File Discovery**: Server monitors your tools directory
2. **Code Analysis**: Validates Python files have `invoke(arguments)` function  
3. **Schema Extraction**: Parses docstrings for parameter definitions
4. **MCP Integration**: Exposes tools via standard MCP protocol
5. **Error Handling**: Provides detailed feedback for debugging

## 📝 Writing Tools

### Function Signature
Every tool must have this exact signature:
```python
def invoke(arguments):
    # Your tool logic here
    return result
```

### Documentation Format
```python
def invoke(arguments):
    """Brief description of what the tool does
    
    Parameters:
    - param_name: Description of the parameter
    - another_param: Description with (default: value)
    """
```

### Example Tools

**Text Processor**:
```python
def invoke(arguments):
    """Transform text in various ways
    
    Parameters:
    - text: The text to transform
    - operation: Type of transformation (uppercase, lowercase, reverse)
    """
    text = arguments.get('text', '')
    operation = arguments.get('operation', 'uppercase')
    
    if operation == 'uppercase':
        return text.upper()
    elif operation == 'lowercase':
        return text.lower()
    elif operation == 'reverse':
        return text[::-1]
    else:
        return f"Unknown operation: {operation}"
```

**API Caller**:
```python
def invoke(arguments):
    """Fetch data from a REST API
    
    Parameters:
    - url: The API endpoint to call
    - method: HTTP method (default: GET)
    """
    import urllib.request
    import json
    
    url = arguments.get('url')
    method = arguments.get('method', 'GET')
    
    if not url:
        return "Error: URL is required"
    
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())
    except Exception as e:
        return f"Error: {str(e)}"
```

## 🔍 Robust Error Handling

The server provides detailed error messages to help you debug:

- **Syntax Errors**: Shows line numbers and specific issues
- **Import Errors**: Reports missing dependencies  
- **Function Signature**: Validates `invoke(arguments)` signature
- **Runtime Errors**: Captures and reports execution problems

## ⚠️ Known Limitations

### Claude Desktop 0.9.2
Claude Desktop currently doesn't support dynamic tool discovery ([see discussion](https://github.com/orgs/modelcontextprotocol/discussions/76)). This means:

- ✅ **Tools work perfectly** once discovered
- ❌ **Restart required** when adding new tools
- 🔄 **Future support planned** - our server is ready with `listChanged: true`

**Workaround**: Restart Claude Desktop after adding new tools.

### Tool Naming in Claude Desktop
Tools appear with server prefix: `local__mcp-dynamic-tools__your_tool_name`

## 🤝 Contributing

This project was created through human-AI collaboration. We welcome contributions!

1. Fork the repository
2. Create your feature branch
3. Add tests for new functionality  
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Ben Wilson** - Architecture and development
- **Claude (Anthropic)** - Co-development and testing
- **MCP Community** - Protocol development and feedback

---

**Made with ❤️ by humans and AI working together**
