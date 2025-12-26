# setup-project.ps1
# Run this from the root of your AgentServer repo to create the full directory structure

Write-Host "Creating AgentServer project structure..." -ForegroundColor Green

# Main package and core files
New-Item -ItemType Directory -Force -Path "agentserver" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\main.py"
New-Item -ItemType File -Force -Path "agentserver\agentserver.py"
New-Item -ItemType File -Force -Path "agentserver\message_bus.py"
New-Item -ItemType File -Force -Path "agentserver\llm_connection.py"

# Privileged commands
New-Item -ItemType Directory -Force -Path "agentserver\privileged" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\privileged\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\privileged\commands.py"

# Authentication
New-Item -ItemType Directory -Force -Path "agentserver\auth" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\auth\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\auth\totp.py"

# Agents
New-Item -ItemType Directory -Force -Path "agentserver\agents" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\agents\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\agents\base.py"

New-Item -ItemType Directory -Force -Path "agentserver\agents\examples" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\agents\examples\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\agents\examples\echo_chamber.py"

# Config
New-Item -ItemType Directory -Force -Path "agentserver\config" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\config\__init__.py"

New-Item -ItemType Directory -Force -Path "agentserver\config\organism_identity" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\config\organism_identity\README.txt" -Value "Place your permanent Ed25519 private.pem and public.pem here.`nPrivate key must be tightly guarded - never commit it."

New-Item -ItemType File -Force -Path "agentserver\config\initial_config.signed.xml" -Value "<!-- Signed boot-time configuration (LLM pools, initial agents, etc.) will go here -->"

# Utils
New-Item -ItemType Directory -Force -Path "agentserver\utils" | Out-Null
New-Item -ItemType File -Force -Path "agentserver\utils\__init__.py"
New-Item -ItemType File -Force -Path "agentserver\utils\xml_tools.py"
New-Item -ItemType File -Force -Path "agentserver\utils\logging_setup.py"

# Top-level supporting folders
New-Item -ItemType Directory -Force -Path "tests" | Out-Null
New-Item -ItemType File -Force -Path "tests\__init__.py"

New-Item -ItemType Directory -Force -Path "scripts" | Out-Null
New-Item -ItemType File -Force -Path "scripts\generate_organism_key.py" -Value "# One-time tool to generate the permanent Ed25519 organism identity`n# Run once, store private key offline/safely"

# .gitignore
$gitignoreContent = @'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/

# Secrets & config
agentserver/config/organism_identity/private.pem
agentserver/config/*.signed.xml

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
Thumbs.db
.DS_Store
'@

Set-Content -Path ".gitignore" -Value $gitignoreContent

Write-Host "Directory structure created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. git add ."
Write-Host "2. git commit -m 'chore: initial project skeleton with modular structure'"
Write-Host "3. git push"
Write-Host "4. In PyCharm: right-click 'agentserver' folder -> Mark Directory as -> Sources Root"
Write-Host ""
Write-Host "The organism now has its full skeletal system. Ready to breathe."
