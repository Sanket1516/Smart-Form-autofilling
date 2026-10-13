$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $workspaceRoot 'docker-compose.test.yml'
$testBackendPort = if ($env:TEST_BACKEND_PORT) { $env:TEST_BACKEND_PORT } else { '8011' }
$previousBackendUrl = $env:E2E_BACKEND_URL
$testExitCode = 0

Push-Location $workspaceRoot
try {
    docker compose -f $composeFile up --build -d
    if ($LASTEXITCODE -ne 0) {
        $testExitCode = $LASTEXITCODE
    } else {
        $env:E2E_BACKEND_URL = "http://127.0.0.1:$testBackendPort"
        npm --prefix extension run test:e2e
        $testExitCode = $LASTEXITCODE
    }
} finally {
    if ($null -ne $previousBackendUrl) {
        $env:E2E_BACKEND_URL = $previousBackendUrl
    } else {
        Remove-Item Env:E2E_BACKEND_URL -ErrorAction SilentlyContinue
    }
    docker compose -f $composeFile down --volumes --remove-orphans
    if ($LASTEXITCODE -ne 0 -and $testExitCode -eq 0) {
        $testExitCode = $LASTEXITCODE
    }
    Pop-Location
}

exit $testExitCode
