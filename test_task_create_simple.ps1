# Wait for server to start
Start-Sleep -Seconds 5

Write-Host "Testing task creation page..."

try {
    # Login
    $loginData = @{
        username = "admin"
        password = "admin123"
    }
    
    $loginResponse = Invoke-WebRequest -Uri "http://localhost:5001/login" -Method POST -Body $loginData -SessionVariable session
    
    # Access task creation page
    $taskPageResponse = Invoke-WebRequest -Uri "http://localhost:5001/tasks/create" -WebSession $session
    
    if ($taskPageResponse.Content -match "创建任务") {
        Write-Host "[PASS] Task creation page loaded successfully"
    } else {
        Write-Host "[FAIL] Task creation page did not load correctly"
    }
    
} catch {
    Write-Host "[FAIL] Error: $_"
}
