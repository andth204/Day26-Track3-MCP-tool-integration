# Launch MCP Inspector pointing at this server.
# Requires Node.js (npx). Inspector is web UI for testing tools without an LLM.

$ErrorActionPreference = "Stop"

# Always prefer the venv's python so fastmcp resolves correctly.
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = (Get-Command python).Source
}

$server = Join-Path $PSScriptRoot "mcp_server.py"

Write-Host ""
Write-Host "===== MCP Inspector launcher =====" -ForegroundColor Cyan
Write-Host "Python:  $python"
Write-Host "Server:  $server"
Write-Host ""
Write-Host "IMPORTANT: open the URL printed below that contains MCP_PROXY_AUTH_TOKEN."
Write-Host "Without the token in the URL, the UI will stay 'Disconnected'."
Write-Host ""

npx -y "@modelcontextprotocol/inspector" $python $server
