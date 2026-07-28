param(
    [string]$ProjectPath = "C:\Users\ramic\Desktop\Data_Governance_Accuracy_Project",
    [int]$IntervalMinutes = 15
)

# Requires admin rights to register a scheduled task
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script must be run as Administrator. Restarting..."
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`" -ProjectPath `"$ProjectPath`" -IntervalMinutes $IntervalMinutes"
    exit
}

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
$StartTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$Trigger = New-ScheduledTaskTrigger -Once -At $StartTime -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration ([TimeSpan]::FromDays(365))
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
    Write-Host "Scheduled task '$TaskName' created. Runs every $IntervalMinutes minutes."
} catch {
    Write-Host "Error creating scheduled task: $_"
    exit 1
}
