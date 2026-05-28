$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\run_daily_jobs.py"
$TaskName = "ConferenceMapDailyJobs"

if (!(Test-Path $Python)) {
  throw "Python virtualenv not found: $Python"
}

$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument "`"$Script`" --lookahead-years 1 --geocode-limit 250 --geocode-sleep 1.0 --llm-limit 5" `
  -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -Daily -At 3:10am
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Refresh conference registry, rolling instances, deadlines, and geocoding cache daily." `
  -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
