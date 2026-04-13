param(
    [string]$VenvPath = ".\venv_django"
)

$absVenv = Resolve-Path $VenvPath -ErrorAction Stop
$activate = Join-Path $absVenv 'Scripts\Activate.ps1'
if (-not (Test-Path $activate)) {
    Write-Error "Virtualenv activate script not found at $activate"
    exit 1
}

$root = Resolve-Path .
$djangoCommand = "Set-Location '$root'; & '$activate'; python .\Frontend\manage.py runserver 127.0.0.1:8000"
$flaskCommand = "Set-Location '$root'; & '$activate'; python .\backend\app.py"

Start-Process powershell -ArgumentList '-NoExit', '-Command', $djangoCommand
Start-Process powershell -ArgumentList '-NoExit', '-Command', $flaskCommand

Write-Host "Starting Django and Flask using one virtualenv: $absVenv"