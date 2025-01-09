# Save this script as "bump_and_push.ps1"
# Ensure you have the necessary permissions to run PowerShell scripts

# Function to execute a command and check for errors
function Execute-Command {
    param (
        [string]$Command
    )
    try {
        Write-Host "Executing: $Command" -ForegroundColor Cyan
        Invoke-Expression $Command
        Write-Host "Command executed successfully." -ForegroundColor Green
    } catch {
        Write-Error "Failed to execute: $Command"
        exit 1
    }
}

# Change directory to the repository root (optional)
# Set-Location "path_to_your_git_repo"

# Commands to execute
Execute-Command "bumpversion patch"
Execute-Command "git push origin master --tags"

Write-Host "All commands executed successfully!" -ForegroundColor Green
