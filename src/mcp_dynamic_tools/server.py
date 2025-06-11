#!/usr/bin/env python3
"""
MCP Dynamic Tools Server

A dynamic MCP server that automatically discovers Python files and exposes them as MCP tools.
Drop Python files in a directory, and they instantly become available as MCP tools to any 
compatible AI client.

Created through collaboration between Ben Wilson and Claude (Anthropic).
"""

import argparse
import json
import logging
import os
import sys
import ast
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set up logging (stderr only, don't interfere with stdio)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("mcp-dynamic-tools")


class DynamicMCPServer:
    """Dynamic MCP server that discovers Python files as tools"""
    
    def __init__(self, tools_dir: str):
        """Initialize the server with a tools directory
        
        Args:
            tools_dir: Directory path containing Python tool files
        """
        self.tools_dir = Path(tools_dir).resolve()
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.tools = self.discover_tools()
        logger.info(f"Initialized MCP server for tools directory: {self.tools_dir}")
    
    def discover_tools(self) -> Dict[str, Dict[str, Any]]:
        """Discover all tools in the workspace directory"""
        tools = {}
        total_files = 0
        valid_tools = 0
        
        for py_file in self.tools_dir.glob("*.py"):
            total_files += 1
            
            if py_file.name.startswith("_"):
                logger.info(f"Skipping private file: {py_file.name}")
                continue
            
            try:
                tool_info = self.analyze_tool_file(py_file)
                if tool_info:
                    tools[tool_info['name']] = tool_info
                    valid_tools += 1
                    logger.info(f"✓ Loaded tool: {tool_info['name']}")
                else:
                    logger.warning(f"✗ Invalid tool: {py_file.name}")
            except Exception as e:
                logger.error(f"✗ Failed to analyze {py_file.name}: {e}")
        
        logger.info(f"Tool discovery complete: {valid_tools}/{total_files} files are valid tools")
        
        if total_files > 0 and valid_tools == 0:
            logger.warning("No valid tools found! Check that your Python files have an 'invoke(arguments)' function")
        
        return tools
    
    def get_builtin_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get the built-in CRUD tools for managing MCP tools"""
        return {
            'write_tool': {
                'name': 'write_tool',
                'description': 'Create a new dynamic MCP tool by writing Python code to a file',
                'inputSchema': {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string", 
                            "description": "Name of the tool (without .py extension)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Python code content for the tool with proper invoke(arguments) function"
                        }
                    },
                    "required": ["name", "content"]
                },
                'invoke_func': self._write_tool_impl
            }
        }
    
    def _write_tool_impl(self, arguments: Dict[str, Any]) -> str:
        """Implementation for the write_tool builtin function"""
        try:
            name = arguments.get('name')
            content = arguments.get('content')
            
            if not name:
                return "Error: 'name' parameter is required"
            if not content:
                return "Error: 'content' parameter is required"
            
            # Validate tool name (should be valid Python identifier)
            if not name.replace('_', '').isalnum():
                return f"Error: Tool name '{name}' must be a valid identifier (letters, numbers, underscores only)"
            
            # Ensure .py extension
            if not name.endswith('.py'):
                filename = f"{name}.py"
            else:
                filename = name
                name = name[:-3]  # Remove .py for tool name
            
            # Write the tool file
            tool_file = self.tools_dir / filename
            
            try:
                with open(tool_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Created new tool: {filename}")
                
                # Refresh tools to pick up the new one
                self.tools = self.discover_tools()
                
                return f"Successfully created tool '{name}' at {tool_file}"
                
            except Exception as e:
                return f"Error writing tool file: {str(e)}"
                
        except Exception as e:
            return f"Error in write_tool: {str(e)}"
    
    def analyze_tool_file(self, py_file: Path) -> Optional[Dict[str, Any]]:
        """Analyze a Python file to extract tool information using AST"""
        try:
            # Read and parse the file
            with open(py_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse AST and check for syntax errors
            try:
                tree = ast.parse(source_code, filename=str(py_file))
            except SyntaxError as e:
                logger.error(f"Syntax error in {py_file.name} at line {e.lineno}: {e.msg}")
                return None
            
            # Find the invoke function
            invoke_func = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == 'invoke':
                    invoke_func = node
                    break
            
            if not invoke_func:
                logger.warning(f"Tool {py_file.name} missing 'invoke' function - skipping")
                return None
            
            # Validate function signature
            if len(invoke_func.args.args) != 1:
                logger.error(f"Tool {py_file.name} invoke() must take exactly 1 parameter (arguments), got {len(invoke_func.args.args)}")
                return None
            
            # Extract docstring
            docstring = ast.get_docstring(invoke_func)
            if not docstring:
                description = f"Dynamic tool: {py_file.stem}"
                properties = {}
                required = []
            else:
                # Parse docstring manually since we're not using docstring_parser
                lines = docstring.strip().split('\n')
                description = lines[0] if lines else f"Tool: {py_file.stem}"
                
                properties = {}
                required = []
                in_params = False
                
                for line in lines[1:]:
                    line = line.strip()
                    if line.lower().startswith('parameters'):
                        in_params = True
                        continue
                    elif line and not line.startswith('-') and in_params:
                        break  # End of parameters section
                    elif in_params and line.startswith('- '):
                        # Parse parameter line: "- name: description"
                        param_line = line[2:].strip()
                        if ':' in param_line:
                            param_name, param_desc = param_line.split(':', 1)
                            param_name = param_name.strip()
                            param_desc = param_desc.strip()
                            
                            # Determine if parameter is required (simple heuristic)
                            is_required = 'default' not in param_desc.lower() and 'optional' not in param_desc.lower()
                            
                            properties[param_name] = {
                                "type": "string",
                                "description": param_desc
                            }
                            if is_required:
                                required.append(param_name)
            
            # Load and validate the module
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if not spec or not spec.loader:
                logger.error(f"Could not create module spec for {py_file.name}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            
            try:
                spec.loader.exec_module(module)
            except ImportError as e:
                logger.error(f"Import error in {py_file.name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error executing {py_file.name}: {e}")
                return None
            
            # Get the actual function for execution
            if not hasattr(module, 'invoke'):
                logger.error(f"Tool {py_file.name} missing 'invoke' function after module load")
                return None
            
            actual_invoke_func = getattr(module, 'invoke')
            if not callable(actual_invoke_func):
                logger.error(f"Tool {py_file.name} has 'invoke' but it's not callable")
                return None
            
            return {
                'name': py_file.stem,
                'description': description,
                'inputSchema': {
                    "type": "object",
                    "properties": properties,
                    "required": required
                },
                'invoke_func': actual_invoke_func
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {py_file}: {e}")
            return None
    
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request"""
        method = request.get('method')
        params = request.get('params', {})
        
        logger.info(f"Handling request: {method}")
        
        if method == 'initialize':
            logger.info("Processing initialize request")
            return {
                'protocolVersion': '2024-11-05',
                'capabilities': {
                    'tools': {
                        'listChanged': True
                    }
                },
                'serverInfo': {
                    'name': 'mcp-dynamic-tools',
                    'version': '0.1.0'
                }
            }
        
        elif method == 'notifications/initialized':
            logger.info("Processing initialized notification")
            return {}  # No response needed for notifications
        
        elif method == 'ping':
            logger.info("Processing ping request")
            return {}  # Simple pong response
        
        elif method == 'tools/list':
            logger.info("Processing tools/list request")
            # Always refresh tools on each list request for dynamic discovery (like lit-server)
            self.tools = self.discover_tools()
            logger.info(f"Discovered {len(self.tools)} tools")
            
            tools_list = []
            
            # Add built-in CRUD tools first
            builtin_tools = self.get_builtin_tools()
            for tool_name, tool_info in builtin_tools.items():
                tools_list.append({
                    'name': tool_name,
                    'description': tool_info['description'],
                    'inputSchema': tool_info['inputSchema']
                })
            
            # Add discovered tools
            for tool_name, tool_info in self.tools.items():
                tools_list.append({
                    'name': tool_name,
                    'description': tool_info['description'],
                    'inputSchema': tool_info['inputSchema']
                })
            
            logger.info(f"Returning {len(tools_list)} total tools ({len(builtin_tools)} built-in + {len(self.tools)} discovered)")
            return {
                'tools': tools_list
            }
        
        elif method == 'tools/call':
            logger.info(f"Processing tools/call request for: {params.get('name', 'unknown')}")
            tool_name = params.get('name', '')
            arguments = params.get('arguments', {})
            
            # Check built-in tools first
            builtin_tools = self.get_builtin_tools()
            if tool_name in builtin_tools:
                tool = builtin_tools[tool_name]
                invoke_func = tool['invoke_func']
            elif tool_name in self.tools:
                tool = self.tools[tool_name]
                invoke_func = tool['invoke_func']
            else:
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': f"Tool '{tool_name}' not found"
                        }
                    ]
                }
            
            try:
                # Validate arguments structure
                if not isinstance(arguments, dict):
                    error_msg = f"Error: Tool arguments must be a dictionary, got {type(arguments).__name__}"
                    return {
                        'content': [
                            {
                                'type': 'text',
                                'text': error_msg
                            }
                        ]
                    }
                
                result = invoke_func(arguments)
                
                # Convert to string
                if isinstance(result, (dict, list)):
                    result_text = json.dumps(result, indent=2)
                else:
                    result_text = str(result)
                
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': result_text
                        }
                    ]
                }
                
            except TypeError as e:
                # Handle function signature mismatches
                error_msg = f"Parameter error in {tool_name}: {str(e)}"
                if "argument" in str(e).lower():
                    error_msg += "\nCheck that your invoke() function takes exactly one 'arguments' parameter"
                logger.error(error_msg)
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': error_msg
                        }
                    ]
                }
                
            except KeyError as e:
                # Handle missing required parameters
                error_msg = f"Missing required parameter in {tool_name}: {str(e)}"
                error_msg += f"\nAvailable parameters: {list(arguments.keys())}"
                logger.error(error_msg)
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': error_msg
                        }
                    ]
                }
                
            except ValueError as e:
                # Handle invalid parameter values
                error_msg = f"Invalid parameter value in {tool_name}: {str(e)}"
                logger.error(error_msg)
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': error_msg
                        }
                    ]
                }
                
            except ImportError as e:
                # Handle missing dependencies
                error_msg = f"Missing dependency in {tool_name}: {str(e)}"
                error_msg += "\nInstall required packages or update your tool code"
                logger.error(error_msg)
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': error_msg
                        }
                    ]
                }
                
            except Exception as e:
                # Handle all other errors with detailed information
                import traceback
                tb = traceback.format_exc()
                error_msg = f"Runtime error in {tool_name}: {str(e)}\n\nFull traceback:\n{tb}"
                logger.error(f"Error executing {tool_name}: {e}\n{tb}")
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': error_msg
                        }
                    ]
                }
        
        else:
            logger.warning(f"Unknown method: {method}")
            raise ValueError(f"Unknown method: {method}")
    
    def run(self):
        """Run the MCP server with stdio communication"""
        logger.info(f"MCP Dynamic Tools Server starting, monitoring: {self.tools_dir}")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response_data = self.handle_request(request)
                    
                    # Don't send response for notifications
                    if request.get('method', '').startswith('notifications/'):
                        continue
                    
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': response_data
                    }
                    
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id') if 'request' in locals() else None,
                        'error': {
                            'code': -1,
                            'message': str(e)
                        }
                    }
                
                # Send response
                print(json.dumps(response), flush=True)
                sys.stdout.flush()
                
        except EOFError:
            logger.info("MCP Server: stdin closed, shutting down")
        except KeyboardInterrupt:
            logger.info("MCP Server shutting down")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            logger.info("MCP Server stopped")


def main():
    """Main entry point for standalone usage"""
    parser = argparse.ArgumentParser(description="MCP Dynamic Tools Server")
    parser.add_argument("--tools-dir", required=True, 
                       help="Directory containing Python tool files")
    args = parser.parse_args()
    
    server = DynamicMCPServer(args.tools_dir)
    server.run()


if __name__ == "__main__":
    main()
