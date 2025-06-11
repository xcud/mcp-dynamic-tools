#!/bin/bash
# Wrapper script for mcp-dynamic-tools server using venv
cd "$(dirname "$0")"
exec ./venv/bin/python src/mcp_dynamic_tools/server.py "$@"
