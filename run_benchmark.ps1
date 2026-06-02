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

# 支持的语言列表
$languages = @("Python", "Java")

foreach ($language in $languages) {
    Write-Host "`n==========================================" -ForegroundColor Green
    Write-Host "Testing Language: $language" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    
    $results = @{}
    
    foreach ($test in $testCases) {
        Write-Host "`n------------------------------------------" -ForegroundColor Yellow
        Write-Host "Testing: $($test.Name) with $language" -ForegroundColor Yellow
        Write-Host "------------------------------------------" -ForegroundColor Yellow
        
        $outputDir = "benchmark_results/$language/$($test.Name)"
        
        python main.py --input $test.File --output $outputDir --language $language
        
        if ($LASTEXITCODE -eq 0) {
            $results[$test.Name] = "PASS"
            Write-Host "✅ PASS" -ForegroundColor Green
        } else {
            $results[$test.Name] = "FAIL"
            Write-Host "❌ FAIL" -ForegroundColor Red
        }
    }
    
    Write-Host "`n==========================================" -ForegroundColor Cyan
    Write-Host "Results Summary for $language" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    
    foreach ($test in $testCases) {
        Write-Host "$($results[$test.Name])  $($test.Name)"
    }
    
    $passed = ($results.Values | Where-Object { $_ -eq "PASS" }).Count
    Write-Host "`nSuccess Rate for ${language}: $passed/$($testCases.Count)"
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "All Benchmarks Completed" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan