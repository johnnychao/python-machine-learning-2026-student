$ErrorActionPreference = 'Stop'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\environment\requirements.txt
Write-Host 'Environment ready. Activate with: .\.venv\Scripts\activate'
