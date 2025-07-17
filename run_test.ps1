# Run sequence 50 times
for ($i = 1; $i -le 50; $i++) {
    Write-Host "Iteration $i of 50"
    Write-Host "Turning volume..."
    python ./press_button.py --turn volume
    
    Write-Host "Pressing like..."
    python ./press_button.py --press like
    
    Write-Host "Turning bass..."
    python ./press_button.py --turn bass
    
    Write-Host "Completed iteration $i"
    Write-Host "------------------------"
}

Write-Host "All 50 iterations completed!"