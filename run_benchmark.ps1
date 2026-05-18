# run_benchmark.ps1
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Benchmark Started" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Remove-Item -Path benchmark_results -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path benchmark_results -Force | Out-Null

$testCases = @(
    @{Name="two_sum"; File="tests/requirements/req_two_sum.txt"},
    @{Name="palindrome"; File="tests/requirements/req_palindrome.txt"},
    @{Name="reverse_string"; File="tests/requirements/req_reverse_string.txt"},
    @{Name="atoi"; File="tests/requirements/req_atoi.txt"},
    @{Name="longest_palindrome"; File="tests/requirements/req_longest_palindrome.txt"}
)

$results = @{}

foreach ($test in $testCases) {
    Write-Host "`n==========================================" -ForegroundColor Yellow
    Write-Host "Testing: $($test.Name)" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    
    $outputDir = "benchmark_results/$($test.Name)"
    
    python main.py --input $test.File --output $outputDir
    
    if ($LASTEXITCODE -eq 0) {
        $results[$test.Name] = "PASS"
        Write-Host "PASS" -ForegroundColor Green
    } else {
        $results[$test.Name] = "FAIL"
        Write-Host "FAIL" -ForegroundColor Red
    }
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Benchmark Results Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

foreach ($test in $testCases) {
    Write-Host "$($results[$test.Name])  $($test.Name)"
}

$passed = ($results.Values | Where-Object { $_ -eq "PASS" }).Count
Write-Host "`nSuccess Rate: $passed/$($testCases.Count)"