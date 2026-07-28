param(
    [string]$ProjectPath = "C:\Users\ramic\Desktop\Data_Governance_Accuracy_Project",
    [int]$IntervalMinutes = 15
)

$TaskName = "DataGov_DQ_ETL"
$ScriptPath = "$ProjectPath\scripts\run_etl.bat"
$PythonPath = (Get-Command python).Source

@"
@echo off
cd /d "$ProjectPath"
"$PythonPath" main.py >> "$ProjectPath\logs\etl_$(Get-Date -Format 'yyyyMMdd').log" 2>&1
"@ | Set-Content -Path $ScriptPath -Encoding ASCII

if (-not (Test-Path "$ProjectPath\logs")) {
    New-Item -ItemType Directory -Path "$ProjectPath\logs" -Force | Out-Null
}

$Action = New-ScheduledTaskAction -Execute $ScriptPath
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -At (Get-Date).AddMinutes(1) -RepetitionDuration ([TimeSpan]::MaxValue)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
    Write-Host "Scheduled task '$TaskName' created. Runs every $IntervalMinutes minutes."
} catch {
    Write-Host "Error creating scheduled task: $_"
    exit 1
}
