# run_prd.ps1
param(
    [Parameter(Mandatory = $true)]
    [string]$PrdFile,
    [string]$OutputDir = "prd_results"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "PRD Run Started" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not (Test-Path -Path $PrdFile)) {
    Write-Host "❌ PRD 文件不存在: $PrdFile" -ForegroundColor Red
    exit 1
}

Remove-Item -Path $OutputDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "Testing Language: Python" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

$langOutputDir = "$OutputDir/Python"

python main.py --input $PrdFile --output $langOutputDir --language Python

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PASS" -ForegroundColor Green
} else {
    Write-Host "❌ FAIL" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "PRD Run Completed" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
