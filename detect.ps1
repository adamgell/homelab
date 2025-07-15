# GlobalProtect Detection Script for Intune Win32 App - Enhanced with Pre-Logon Support
# Checks for GlobalProtect version 6.2.8 or higher and ensures pre-logon functionality

$RequiredVersion = '6.2.8'
$GlobalProtectFound = $false
$VersionMet = $false
$DetectedVersion = 'Unknown'
$PSADTDetected = $false  # Initialize as boolean

# Function to parse version strings with various formats
function Parse-Version {
    param([string]$VersionString)

    if ([string]::IsNullOrWhiteSpace($VersionString)) {
        return $null
    }

    # Clean version string - remove common suffixes and extract numeric version
    $cleanVersion = $VersionString -replace '[a-zA-Z\s\-_].*$', ''
    $cleanVersion = $cleanVersion.Trim()

    # Ensure we have at least 3 parts (major.minor.build)
    $parts = $cleanVersion.Split('.')
    while ($parts.Count -lt 3) {
        $parts += '0'
    }

    # Take only first 4 parts if more exist
    if ($parts.Count -gt 4) {
        $parts = $parts[0..3]
    }

    $finalVersion = $parts -join '.'

    try {
        return [Version]$finalVersion
    } catch {
        Write-Output "Failed to parse version from: $VersionString (cleaned: $finalVersion)"
        return $null
    }
}

# Registry paths to check
$RegistryPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

# Check registry for GlobalProtect
Write-Output '=== Starting GlobalProtect Detection ==='
Write-Output "Required Version: $RequiredVersion"

foreach ($RegistryPath in $RegistryPaths) {
    Write-Output "`nChecking registry path: $RegistryPath"

    try {
        $UninstallKeys = Get-ItemProperty -Path $RegistryPath -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like '*GlobalProtect*' -or
            $_.DisplayName -like '*Palo Alto Networks*' }

        foreach ($Key in $UninstallKeys) {
            if ($Key.DisplayName) {
                Write-Output "Found: $($Key.DisplayName)"
                $GlobalProtectFound = $true

                if ($Key.DisplayVersion) {
                    Write-Output "Raw Version: $($Key.DisplayVersion)"
                    $ParsedVersion = Parse-Version -VersionString $Key.DisplayVersion

                    if ($ParsedVersion) {
                        $DetectedVersion = $ParsedVersion.ToString()
                        $RequiredVersionObj = Parse-Version -VersionString $RequiredVersion

                        if ($ParsedVersion -ge $RequiredVersionObj) {
                            $VersionMet = $true
                            Write-Output "Version OK: $DetectedVersion >= $RequiredVersion"
                            break
                        } else {
                            Write-Output "Version Too Old: $DetectedVersion < $RequiredVersion"
                        }
                    }
                } else {
                    Write-Output 'No DisplayVersion found in registry'
                }
            }
        }
    } catch {
        Write-Output "Error accessing registry: $_"
    }

    if ($VersionMet) { break }
}

# PSADT Detection
Write-Output "`n=== PSADT Detection ==="
$regPath = "Registry::HKEY_LOCAL_MACHINE\SOFTWARE\InstalledApps\Palo_Alto_Networks_GlobalProtect_6.2.8"

try {
    if (Test-Path -Path $regPath) {
        Write-Output "Detected that PSADT installed GlobalProtect"
        $PSADTDetected = $true
    }
    else {
        Write-Output "PSADT did not detect GlobalProtect"
        $PSADTDetected = $false
    }
}
catch {
    Write-Output "Error checking PSADT registry: $_"
    $PSADTDetected = $false
}

# ================================================================================
# FINAL DETECTION RESULT
# ================================================================================

Write-Output "`n=== Detection Summary ==="
Write-Output "GlobalProtect Found: $GlobalProtectFound"
Write-Output "Version Requirement Met: $VersionMet"
Write-Output "Detected Version: $DetectedVersion"
Write-Output "PSADT Installation: $PSADTDetected"

if ($GlobalProtectFound -and $VersionMet -and $PSADTDetected) {
    Write-Output "`nDETECTION SUCCESS: GlobalProtect $RequiredVersion with pre-logon functionality is ready"
    exit 0
} elseif ($GlobalProtectFound -and -not $VersionMet) {
    Write-Output "`nDETECTION FAILED: GlobalProtect found but version ($DetectedVersion) is below $RequiredVersion"
    exit 1
} elseif ($GlobalProtectFound -and $VersionMet -and -not $PSADTDetected) {
    Write-Output "`nDETECTION FAILED: GlobalProtect $RequiredVersion found but not installed via PSADT"
    exit 1
} else {
    Write-Output "`nDETECTION FAILED: GlobalProtect not found"
    exit 1
}