<#
.SYNOPSIS
    CheckMK Agent Plugin Template for Windows (PowerShell)
    
.DESCRIPTION
    This template demonstrates a complete Windows agent plugin with:
    - Configuration file support
    - Multiple output sections
    - Error handling
    - WMI and Registry queries
    - Service and process monitoring
    - Caching support
    
.NOTES
    Installation:
    1. Copy to C:\ProgramData\checkmk\agent\plugins\myapp.ps1
    2. Optional: Create config at C:\ProgramData\checkmk\agent\config\myapp.cfg
    
    For async execution, add to check_mk.user.yml:
    plugins:
      execution:
        - pattern: myapp.ps1
          async: yes
          cache_age: 300
          
.LINK
    https://docs.checkmk.com/latest/en/agent_windows.html
#>

# ============================================================================
# CONFIGURATION
# ============================================================================

# Config directory (set by agent, fallback for manual testing)
$script:ConfigDir = if ($env:MK_CONFDIR) { $env:MK_CONFDIR } else { "C:\ProgramData\checkmk\agent\config" }
$script:StateDir = if ($env:MK_STATEDIR) { $env:MK_STATEDIR } else { "C:\ProgramData\checkmk\agent\state" }
$script:TempDir = if ($env:MK_TEMPDIR) { $env:MK_TEMPDIR } else { $env:TEMP }

# Default configuration
$script:Config = @{
    Enabled = $true
    ServiceName = "MyAppService"
    ProcessName = "myapp"
    Timeout = 30
    Debug = $false
}

function Read-PluginConfig {
    <#
    .SYNOPSIS
        Read plugin configuration from INI-style file
    #>
    $configFile = Join-Path $script:ConfigDir "myapp.cfg"
    
    if (-not (Test-Path $configFile)) {
        return
    }
    
    $currentSection = ""
    
    Get-Content $configFile -ErrorAction SilentlyContinue | ForEach-Object {
        $line = $_.Trim()
        
        # Skip comments and empty lines
        if ($line -match '^[#;]' -or $line -eq "") {
            return
        }
        
        # Section header
        if ($line -match '^\[(.+)\]$') {
            $currentSection = $Matches[1].ToLower()
            return
        }
        
        # Key = Value (only in [myapp] section)
        if ($currentSection -eq "myapp" -and $line -match '^(\w+)\s*=\s*(.*)$') {
            $key = $Matches[1]
            $value = $Matches[2].Trim()
            
            # Type conversion
            switch -Regex ($value) {
                '^(true|yes|1)$' { $script:Config[$key] = $true }
                '^(false|no|0)$' { $script:Config[$key] = $false }
                '^\d+$' { $script:Config[$key] = [int]$value }
                default { $script:Config[$key] = $value }
            }
        }
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Section {
    <#
    .SYNOPSIS
        Write a CheckMK section header
    .PARAMETER Name
        Section name
    .PARAMETER Separator
        Optional separator character code (e.g., 124 for pipe, 59 for semicolon)
    .PARAMETER Cached
        Optional cache timestamp and max age for cached sections
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name,
        
        [int]$Separator = 0,
        
        [int]$CacheAge = 0
    )
    
    $header = "<<<$Name"
    
    if ($Separator -gt 0) {
        $header += ":sep($Separator)"
    }
    
    if ($CacheAge -gt 0) {
        $timestamp = [int][double]::Parse((Get-Date -UFormat %s))
        $header += ":cached($timestamp,$CacheAge)"
    }
    
    $header += ">>>"
    Write-Host $header
}

function Write-Debug {
    param([string]$Message)
    if ($script:Config.Debug) {
        Write-Host "# DEBUG: $Message" -ForegroundColor Yellow
    }
}

# ============================================================================
# DATA COLLECTION FUNCTIONS
# ============================================================================

function Get-ServiceInfo {
    <#
    .SYNOPSIS
        Collect Windows service information
    #>
    Write-Section -Name "myapp_service" -Separator 124  # Pipe separator
    
    $serviceName = $script:Config.ServiceName
    
    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop
        
        # Output: name|status|starttype|displayname
        Write-Host "$($service.Name)|$($service.Status)|$($service.StartType)|$($service.DisplayName)"
        
        # Additional WMI info for more details
        $wmiService = Get-WmiObject Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
        if ($wmiService) {
            Write-Section -Name "myapp_service_details" -Separator 124
            Write-Host "pid|$($wmiService.ProcessId)"
            Write-Host "path|$($wmiService.PathName)"
            Write-Host "account|$($wmiService.StartName)"
        }
    }
    catch {
        Write-Section -Name "myapp_service" -Separator 124
        Write-Host "$serviceName|NotFound|Unknown|Service not installed"
    }
}

function Get-ProcessInfo {
    <#
    .SYNOPSIS
        Collect process metrics
    #>
    Write-Section -Name "myapp_process" -Separator 124
    
    $processName = $script:Config.ProcessName
    $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue
    
    if (-not $processes) {
        Write-Host "$processName|NotRunning|0|0|0"
        return
    }
    
    foreach ($proc in $processes) {
        # Output: name|status|pid|cpu|memory_mb|threads
        $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 2)
        $cpuTime = [math]::Round($proc.CPU, 2)
        
        Write-Host "$($proc.ProcessName)|Running|$($proc.Id)|$cpuTime|$memMB|$($proc.Threads.Count)"
    }
}

function Get-PerformanceCounters {
    <#
    .SYNOPSIS
        Collect Windows performance counters
    #>
    Write-Section -Name "myapp_perfcounters" -Separator 124
    
    $counters = @(
        "\Processor(_Total)\% Processor Time"
        "\Memory\Available MBytes"
        "\Memory\% Committed Bytes In Use"
        "\LogicalDisk(_Total)\% Free Space"
    )
    
    foreach ($counter in $counters) {
        try {
            $value = (Get-Counter $counter -ErrorAction Stop).CounterSamples[0].CookedValue
            $name = $counter -replace '[\\()]', '_' -replace '\s+', '_' -replace '_+', '_'
            Write-Host "$name|$([math]::Round($value, 2))"
        }
        catch {
            Write-Debug "Counter failed: $counter"
        }
    }
}

function Get-EventLogErrors {
    <#
    .SYNOPSIS
        Collect recent application errors from Event Log
    #>
    Write-Section -Name "myapp_events" -Separator 0  # No separator = space
    
    $cutoffTime = (Get-Date).AddHours(-24)
    $appName = $script:Config.ProcessName
    
    try {
        $events = Get-WinEvent -FilterHashtable @{
            LogName = 'Application'
            Level = 1,2,3  # Critical, Error, Warning
            StartTime = $cutoffTime
        } -MaxEvents 10 -ErrorAction SilentlyContinue | 
        Where-Object { $_.ProviderName -like "*$appName*" }
        
        if ($events) {
            foreach ($event in $events) {
                # Output as JSON for easier parsing
                $eventData = @{
                    time = $event.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                    level = $event.LevelDisplayName
                    id = $event.Id
                    message = $event.Message.Substring(0, [Math]::Min(200, $event.Message.Length))
                } | ConvertTo-Json -Compress
                Write-Host $eventData
            }
        }
    }
    catch {
        Write-Debug "Event log query failed: $_"
    }
}

function Get-ApplicationMetrics {
    <#
    .SYNOPSIS
        Collect application-specific metrics (customize this!)
    #>
    Write-Section -Name "myapp_metrics" -Separator 59  # Semicolon separator
    
    # Example: Read from registry
    $regPath = "HKLM:\SOFTWARE\MyApp"
    if (Test-Path $regPath) {
        try {
            $regData = Get-ItemProperty -Path $regPath -ErrorAction Stop
            
            if ($regData.Version) { Write-Host "version;$($regData.Version)" }
            if ($regData.ConnectionCount) { Write-Host "connections;$($regData.ConnectionCount)" }
            if ($regData.LastBackup) { Write-Host "last_backup;$($regData.LastBackup)" }
        }
        catch {
            Write-Debug "Registry read failed: $_"
        }
    }
    
    # Example: Read from application status file
    $statusFile = "C:\ProgramData\MyApp\status.json"
    if (Test-Path $statusFile) {
        try {
            $status = Get-Content $statusFile -Raw | ConvertFrom-Json
            Write-Host "queue_size;$($status.queue_size)"
            Write-Host "processed_today;$($status.processed_today)"
            Write-Host "error_count;$($status.error_count)"
        }
        catch {
            Write-Debug "Status file read failed: $_"
        }
    }
    
    # Example: Query local REST API
    $apiUrl = "http://localhost:8080/api/health"
    try {
        $health = Invoke-RestMethod -Uri $apiUrl -TimeoutSec 5 -ErrorAction Stop
        Write-Host "api_status;$($health.status)"
        Write-Host "uptime_seconds;$($health.uptime)"
    }
    catch {
        Write-Host "api_status;unreachable"
    }
}

function Get-DatabaseConnections {
    <#
    .SYNOPSIS
        Check database connectivity (example for SQL Server)
    #>
    Write-Section -Name "myapp_database" -Separator 124
    
    # Skip if no SQL Server installed
    if (-not (Get-Service -Name "MSSQLSERVER" -ErrorAction SilentlyContinue)) {
        return
    }
    
    try {
        $connectionString = "Server=localhost;Database=MyAppDB;Integrated Security=True;Connection Timeout=5"
        $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
        $connection.Open()
        
        $command = $connection.CreateCommand()
        $command.CommandText = "SELECT COUNT(*) as cnt FROM sys.dm_exec_sessions WHERE database_id = DB_ID()"
        $command.CommandTimeout = 5
        
        $reader = $command.ExecuteReader()
        if ($reader.Read()) {
            Write-Host "MyAppDB|connected|$($reader['cnt'])"
        }
        $reader.Close()
        $connection.Close()
    }
    catch {
        Write-Host "MyAppDB|error|$($_.Exception.Message -replace '\|', ' ')"
    }
}

# ============================================================================
# MAIN
# ============================================================================

function Main {
    # Read configuration
    Read-PluginConfig
    
    # Check if plugin is enabled
    if (-not $script:Config.Enabled) {
        exit 0
    }
    
    Write-Debug "Starting myapp plugin"
    Write-Debug "Config: $($script:Config | ConvertTo-Json -Compress)"
    
    # Collect data - each function outputs its own section
    Get-ServiceInfo
    Get-ProcessInfo
    Get-ApplicationMetrics
    Get-PerformanceCounters
    Get-EventLogErrors
    Get-DatabaseConnections
    
    Write-Debug "Plugin completed"
}

# Run main function
Main
