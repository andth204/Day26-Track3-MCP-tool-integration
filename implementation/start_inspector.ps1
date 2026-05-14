# Launch MCP Inspector pointing at this server.
# Requires Node.js (npx). Inspector is web UI for testing tools without an LLM.

$ErrorActionPreference = "Stop"

$python = (Get-Command python).Source
$server = Join-Path $PSScriptRoot "mcp_server.py"

Write-Host "Python:  $python"
Write-Host "Server:  $server"
Write-Host ""

npx -y "@modelcontextprotocol/inspector" $python $server
