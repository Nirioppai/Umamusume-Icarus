param(
    [int]$DelaySeconds = 1,
    [int]$Limit = 0
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Refreshing Game8 trainee profiles..."
if ($Limit -gt 0) {
    python tools/game8_character_profile_scraper.py --root . --delay $DelaySeconds --limit $Limit
} else {
    python tools/game8_character_profile_scraper.py --root . --delay $DelaySeconds
}

Write-Host "Validating profile coverage..."
python tools/validate_trainee_profiles.py --root .

Write-Host "Done."
