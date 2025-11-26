# =============================================================================
# CheckMK Local Check Template - PowerShell
# =============================================================================
#
# Installation:
#   C:\ProgramData\checkmk\agent\local\
#
# For async execution, configure in check_mk.user.yml:
#   local:
#     enabled: yes
#     execution:
#       - pattern: $CUSTOM_LOCAL_PATH$\my_check.ps1
#         async: yes
#         cache_age: 600
#
# Output format per line:
#   <STATUS> "<SERVICE_NAME>" <METRICS> <STATUS_TEXT>
#
# Status values:
#   0 = OK, 1 = WARN, 2 = CRIT, 3 = UNKNOWN, P = dynamic (from thresholds)
#
# =============================================================================

# Ensure UTF-8 output for CheckMK
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# =============================================================================
# Helper Functions
# =============================================================================

function Write-LocalCheck {
    <#
    .SYNOPSIS
    Outputs a local check result in CheckMK format.
    
    .PARAMETER Status
    0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN, or 'P' for dynamic
    
    .PARAMETER ServiceName
    Name of the service (will be shown in CheckMK)
    
    .PARAMETER Metrics
    Metrics string or '-' for no metrics
    
    .PARAMETER Text
    Status text
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Status,
        
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,
        
        [Parameter(Mandatory=$false)]
        [string]$Metrics = "-",
        
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-Host "$Status `"$ServiceName`" $Metrics $Text"
}

function Write-OK {
    param([string]$ServiceName, [string]$Metrics = "-", [string]$Text)
    Write-LocalCheck -Status 0 -ServiceName $ServiceName -Metrics $Metrics -Text $Text
}

function Write-WARN {
    param([string]$ServiceName, [string]$Metrics = "-", [string]$Text)
    Write-LocalCheck -Status 1 -ServiceName $ServiceName -Metrics $Metrics -Text $Text
}

function Write-CRIT {
    param([string]$ServiceName, [string]$Metrics = "-", [string]$Text)
    Write-LocalCheck -Status 2 -ServiceName $ServiceName -Metrics $Metrics -Text $Text
}

function Write-UNKNOWN {
    param([string]$ServiceName, [string]$Metrics = "-", [string]$Text)
    Write-LocalCheck -Status 3 -ServiceName $ServiceName -Metrics $Metrics -Text $Text
}

function Write-Dynamic {
    param([string]$ServiceName, [string]$Metrics, [string]$Text)
    Write-LocalCheck -Status "P" -ServiceName $ServiceName -Metrics $Metrics -Text $Text
}

# =============================================================================
# Example Checks - Customize or replace these
# =============================================================================

function Check-StaticExample {
    Write-OK -ServiceName "Static Example" -Text "This check is always OK"
}

function Check-WindowsService {
    <#
    .SYNOPSIS
    Checks if a Windows service is running.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,
        
        [string]$DisplayName = $ServiceName
    )
    
    try {
        $svc = Get-Service -Name $ServiceName -ErrorAction Stop
        
        switch ($svc.Status) {
            "Running" {
                Write-OK -ServiceName "Service $DisplayName" -Text "Service is running"
            }
            "Stopped" {
                Write-CRIT -ServiceName "Service $DisplayName" -Text "Service is stopped"
            }
            default {
                Write-WARN -ServiceName "Service $DisplayName" -Text "Service status: $($svc.Status)"
            }
        }
    }
    catch {
        Write-UNKNOWN -ServiceName "Service $DisplayName" -Text "Service not found"
    }
}

function Check-DiskSpace {
    <#
    .SYNOPSIS
    Checks disk space usage with dynamic thresholds.
    #>
    param(
        [string]$DriveLetter = "C",
        [int]$WarnPercent = 80,
        [int]$CritPercent = 90
    )
    
    try {
        $drive = Get-PSDrive -Name $DriveLetter -ErrorAction Stop
        $usedGB = [math]::Round(($drive.Used / 1GB), 2)
        $freeGB = [math]::Round(($drive.Free / 1GB), 2)
        $totalGB = $usedGB + $freeGB
        $usedPercent = [math]::Round(($usedGB / $totalGB) * 100, 1)
        
        $metrics = "usage=$usedPercent;$WarnPercent;$CritPercent;0;100"
        Write-Dynamic -ServiceName "Disk $DriveLetter" -Metrics $metrics `
            -Text "Used: $usedPercent% ($usedGB GB of $totalGB GB)"
    }
    catch {
        Write-UNKNOWN -ServiceName "Disk $DriveLetter" -Text "Cannot read drive: $_"
    }
}

function Check-CPUUsage {
    <#
    .SYNOPSIS
    Checks CPU usage with thresholds.
    #>
    param(
        [int]$WarnPercent = 80,
        [int]$CritPercent = 95
    )
    
    try {
        $cpu = Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction Stop
        $cpuPercent = [math]::Round($cpu.CounterSamples[0].CookedValue, 1)
        
        $metrics = "cpu=$cpuPercent;$WarnPercent;$CritPercent;0;100"
        Write-Dynamic -ServiceName "CPU Usage" -Metrics $metrics -Text "CPU: $cpuPercent%"
    }
    catch {
        Write-UNKNOWN -ServiceName "CPU Usage" -Text "Cannot read CPU counter: $_"
    }
}

function Check-MemoryUsage {
    <#
    .SYNOPSIS
    Checks memory usage with thresholds.
    #>
    param(
        [int]$WarnPercent = 80,
        [int]$CritPercent = 90
    )
    
    try {
        $os = Get-CimInstance -ClassName Win32_OperatingSystem
        $totalMB = [math]::Round($os.TotalVisibleMemorySize / 1024, 0)
        $freeMB = [math]::Round($os.FreePhysicalMemory / 1024, 0)
        $usedMB = $totalMB - $freeMB
        $usedPercent = [math]::Round(($usedMB / $totalMB) * 100, 1)
        
        $metrics = "memory=$usedPercent;$WarnPercent;$CritPercent;0;100"
        Write-Dynamic -ServiceName "Memory Usage" -Metrics $metrics `
            -Text "Memory: $usedPercent% ($usedMB MB of $totalMB MB)"
    }
    catch {
        Write-UNKNOWN -ServiceName "Memory Usage" -Text "Cannot read memory: $_"
    }
}

function Check-ProcessRunning {
    <#
    .SYNOPSIS
    Checks if a process is running and counts instances.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ProcessName,
        
        [int]$MinCount = 1,
        [int]$MaxCount = 100
    )
    
    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    $count = if ($processes) { @($processes).Count } else { 0 }
    
    $metrics = "count=$count"
    
    if ($count -lt $MinCount) {
        Write-CRIT -ServiceName "Process $ProcessName" -Metrics $metrics `
            -Text "Only $count instances (min: $MinCount)"
    }
    elseif ($count -gt $MaxCount) {
        Write-WARN -ServiceName "Process $ProcessName" -Metrics $metrics `
            -Text "Too many: $count instances (max: $MaxCount)"
    }
    else {
        Write-OK -ServiceName "Process $ProcessName" -Metrics $metrics `
            -Text "$count instances running"
    }
}

function Check-TCPPort {
    <#
    .SYNOPSIS
    Checks if a TCP port is reachable.
    #>
    param(
        [string]$Host = "localhost",
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [string]$ServiceName = "Port $Port",
        [int]$TimeoutMs = 3000
    )
    
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect($Host, $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        
        if ($wait -and $tcp.Connected) {
            $tcp.Close()
            Write-OK -ServiceName $ServiceName -Text "Port $Port is open on $Host"
        }
        else {
            $tcp.Close()
            Write-CRIT -ServiceName $ServiceName -Text "Port $Port is closed on $Host"
        }
    }
    catch {
        Write-CRIT -ServiceName $ServiceName -Text "Cannot connect to port $Port on $Host"
    }
}

function Check-EventLogErrors {
    <#
    .SYNOPSIS
    Checks for errors in Windows Event Log.
    #>
    param(
        [string]$LogName = "Application",
        [int]$HoursBack = 1,
        [int]$WarnCount = 5,
        [int]$CritCount = 20,
        [string]$ServiceName = "EventLog $LogName Errors"
    )
    
    try {
        $startTime = (Get-Date).AddHours(-$HoursBack)
        $events = Get-WinEvent -FilterHashtable @{
            LogName = $LogName
            Level = 1,2  # Critical and Error
            StartTime = $startTime
        } -ErrorAction SilentlyContinue
        
        $count = if ($events) { @($events).Count } else { 0 }
        
        $metrics = "errors=$count;$WarnCount;$CritCount"
        Write-Dynamic -ServiceName $ServiceName -Metrics $metrics `
            -Text "Found $count errors in last $HoursBack hour(s)"
    }
    catch {
        Write-UNKNOWN -ServiceName $ServiceName -Text "Cannot read event log: $_"
    }
}

function Check-FileAge {
    <#
    .SYNOPSIS
    Checks the age of a file.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$FilePath,
        
        [int]$WarnHours = 24,
        [int]$CritHours = 48,
        [string]$ServiceName = "File Age"
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-CRIT -ServiceName $ServiceName -Text "File not found: $FilePath"
        return
    }
    
    try {
        $file = Get-Item $FilePath
        $ageHours = [math]::Round(((Get-Date) - $file.LastWriteTime).TotalHours, 1)
        
        $metrics = "age=$ageHours;$WarnHours;$CritHours"
        Write-Dynamic -ServiceName $ServiceName -Metrics $metrics `
            -Text "File is $ageHours hours old"
    }
    catch {
        Write-UNKNOWN -ServiceName $ServiceName -Text "Cannot check file: $_"
    }
}

function Check-SQLServerConnection {
    <#
    .SYNOPSIS
    Checks SQL Server connectivity.
    #>
    param(
        [string]$ServerInstance = "localhost",
        [string]$Database = "master",
        [string]$ServiceName = "SQL Server Connection"
    )
    
    try {
        $connectionString = "Server=$ServerInstance;Database=$Database;Integrated Security=True;Connection Timeout=10"
        $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
        
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $connection.Open()
        $sw.Stop()
        $connection.Close()
        
        $responseMs = $sw.ElapsedMilliseconds
        $metrics = "response_time=$responseMs;1000;5000"
        
        Write-Dynamic -ServiceName $ServiceName -Metrics $metrics `
            -Text "Connected in ${responseMs}ms"
    }
    catch {
        Write-CRIT -ServiceName $ServiceName -Text "Connection failed: $_"
    }
}

function Check-CertificateExpiry {
    <#
    .SYNOPSIS
    Checks certificate expiry for a URL.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Url,
        
        [int]$WarnDays = 30,
        [int]$CritDays = 7,
        [string]$ServiceName = "Certificate Expiry"
    )
    
    try {
        $request = [Net.HttpWebRequest]::Create($Url)
        $request.Timeout = 10000
        $request.AllowAutoRedirect = $true
        
        try { $request.GetResponse() | Out-Null } catch {}
        
        $cert = $request.ServicePoint.Certificate
        if (-not $cert) {
            Write-UNKNOWN -ServiceName $ServiceName -Text "No certificate found for $Url"
            return
        }
        
        $expiryDate = [DateTime]::Parse($cert.GetExpirationDateString())
        $daysLeft = [math]::Round(($expiryDate - (Get-Date)).TotalDays, 0)
        
        $metrics = "days_left=$daysLeft;$WarnDays`:;$CritDays`:"
        Write-Dynamic -ServiceName $ServiceName -Metrics $metrics `
            -Text "Certificate expires in $daysLeft days ($($expiryDate.ToString('yyyy-MM-dd')))"
    }
    catch {
        Write-UNKNOWN -ServiceName $ServiceName -Text "Cannot check certificate: $_"
    }
}

# =============================================================================
# Main - Run your checks here
# =============================================================================

# Uncomment and customize the checks you need:

Check-StaticExample
# Check-WindowsService -ServiceName "Spooler" -DisplayName "Print Spooler"
# Check-WindowsService -ServiceName "W3SVC" -DisplayName "IIS"
# Check-DiskSpace -DriveLetter "C" -WarnPercent 80 -CritPercent 90
# Check-DiskSpace -DriveLetter "D" -WarnPercent 85 -CritPercent 95
# Check-CPUUsage -WarnPercent 80 -CritPercent 95
# Check-MemoryUsage -WarnPercent 80 -CritPercent 90
# Check-ProcessRunning -ProcessName "notepad" -MinCount 0 -MaxCount 10
# Check-TCPPort -Host "localhost" -Port 80 -ServiceName "HTTP"
# Check-TCPPort -Host "localhost" -Port 443 -ServiceName "HTTPS"
# Check-EventLogErrors -LogName "Application" -HoursBack 1 -WarnCount 5 -CritCount 20
# Check-FileAge -FilePath "C:\Backups\latest.bak" -WarnHours 24 -CritHours 48 -ServiceName "Backup Age"
# Check-SQLServerConnection -ServerInstance "localhost" -Database "master"
# Check-CertificateExpiry -Url "https://example.com" -WarnDays 30 -CritDays 7
