param(
    [Parameter(Mandatory = $true)]
    [string]$Image,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedSha256
)

$actual = (Get-FileHash -Path $Image -Algorithm SHA256).Hash.ToLowerInvariant()
$expected = $ExpectedSha256.ToLowerInvariant()

Write-Host "expected=$expected"
Write-Host "actual=$actual"

if ($actual -ne $expected) {
    throw "candidate image hash mismatch"
}

Write-Host "candidate image identity verified"
