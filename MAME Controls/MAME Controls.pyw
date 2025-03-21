<#
    .SYNOPSIS

    PSApppDeployToolkit - This script performs the installation or uninstallation of an application(s).

    .DESCRIPTION

    - The script is provided as a template to perform an install or uninstall of an application(s).
    - The script either performs an "Install" deployment type or an "Uninstall" deployment type.
    - The install deployment type is broken down into 3 main sections/phases: Pre-Install, Install, and Post-Install.

    The script dot-sources the AppDeployToolkitMain.ps1 script which contains the logic and functions required to install or uninstall an application.

    PSApppDeployToolkit is licensed under the GNU LGPLv3 License - (C) 2023 PSAppDeployToolkit Team (Sean Lillis, Dan Cunningham and Muhammad Mashwani).

    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the
    Free Software Foundation, either version 3 of the License, or any later version. This program is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
    for more details. You should have received a copy of the GNU Lesser General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

    .PARAMETER DeploymentType

    The type of deployment to perform. Default is: Install.

    .PARAMETER DeployMode

    Specifies whether the installation should be run in Interactive, Silent, or NonInteractive mode. Default is: Interactive. Options: Interactive = Shows dialogs, Silent = No dialogs, NonInteractive = Very silent, i.e. no blocking apps. NonInteractive mode is automatically set if it is detected that the process is not user interactive.

    .PARAMETER AllowRebootPassThru

    Allows the 3010 return code (requires restart) to be passed back to the parent process (e.g. SCCM) if detected from an installation. If 3010 is passed back to SCCM, a reboot prompt will be triggered.

    .PARAMETER TerminalServerMode

    Changes to "user install mode" and back to "user execute mode" for installing/uninstalling applications for Remote Desktop Session Hosts/Citrix servers.

    .PARAMETER DisableLogging

    Disables logging to file for the script. Default is: $false.

    .EXAMPLE

    powershell.exe -Command "& { & '.\Deploy-Application.ps1' -DeployMode 'Silent'; Exit $LastExitCode }"

    .EXAMPLE

    powershell.exe -Command "& { & '.\Deploy-Application.ps1' -AllowRebootPassThru; Exit $LastExitCode }"

    .EXAMPLE

    powershell.exe -Command "& { & '.\Deploy-Application.ps1' -DeploymentType 'Uninstall'; Exit $LastExitCode }"

    .EXAMPLE

    Deploy-Application.exe -DeploymentType "Install" -DeployMode "Silent"

    .INPUTS

    None

    You cannot pipe objects to this script.

    .OUTPUTS

    None

    This script does not generate any output.

    .NOTES

    Toolkit Exit Code Ranges:
    - 60000 - 68999: Reserved for built-in exit codes in Deploy-Application.ps1, Deploy-Application.exe, and AppDeployToolkitMain.ps1
    - 69000 - 69999: Recommended for user customized exit codes in Deploy-Application.ps1
    - 70000 - 79999: Recommended for user customized exit codes in AppDeployToolkitExtensions.ps1

    .LINK

    https://psappdeploytoolkit.com
#>


[CmdletBinding()]
Param (
    [Parameter(Mandatory = $false)]
    [ValidateSet('Install', 'Uninstall', 'Repair')]
    [String]$DeploymentType = 'Install',
    [Parameter(Mandatory = $false)]
    [ValidateSet('Interactive', 'Silent', 'NonInteractive')]
    [String]$DeployMode = 'Interactive',
    [Parameter(Mandatory = $false)]
    [switch]$AllowRebootPassThru = $false,
    [Parameter(Mandatory = $false)]
    [switch]$TerminalServerMode = $false,
    [Parameter(Mandatory = $false)]
    [switch]$DisableLogging = $false
)

Try {
    ## Set the script execution policy for this process
    Try {
        Set-ExecutionPolicy -ExecutionPolicy 'ByPass' -Scope 'Process' -Force -ErrorAction 'Stop'
    }
    Catch {
    }

    ##*===============================================
    ##* VARIABLE DECLARATION
    ##*===============================================
    ## Variables: Application
    [String]$appVendor = ''
    [String]$appName = 'New Zealand Language Pack V2'
    [String]$appVersion = ''
    [String]$appArch = 'x64'
    [String]$appLang = 'EN'
    [String]$appRevision = '01'
    [String]$appScriptVersion = '1.0.0'
    [String]$appScriptDate = '2025-03-07'
    [String]$appScriptAuthor = 'Blair Hayes'
    ##*===============================================
    ## Variables: Install Titles (Only set here to override defaults set by the toolkit)
    [String]$installName = ''
    [String]$installTitle = ''

    ##* Do not modify section below
    #region DoNotModify

    ## Variables: Exit Code
    [Int32]$mainExitCode = 0

    ## Variables: Script
    [String]$deployAppScriptFriendlyName = 'Deploy Application'
    [Version]$deployAppScriptVersion = [Version]'3.9.3'
    [String]$deployAppScriptDate = '02/05/2023'
    [Hashtable]$deployAppScriptParameters = $PsBoundParameters

    ## Variables: Environment
    If (Test-Path -LiteralPath 'variable:HostInvocation') {
        $InvocationInfo = $HostInvocation
    }
    Else {
        $InvocationInfo = $MyInvocation
    }
    [String]$scriptDirectory = Split-Path -Path $InvocationInfo.MyCommand.Definition -Parent

    ## Dot source the required App Deploy Toolkit Functions
    Try {
        [String]$moduleAppDeployToolkitMain = "$scriptDirectory\AppDeployToolkit\AppDeployToolkitMain.ps1"
        If (-not (Test-Path -LiteralPath $moduleAppDeployToolkitMain -PathType 'Leaf')) {
            Throw "Module does not exist at the specified location [$moduleAppDeployToolkitMain]."
        }
        If ($DisableLogging) {
            . $moduleAppDeployToolkitMain -DisableLogging
        }
        Else {
            . $moduleAppDeployToolkitMain
        }
    }
    Catch {
        If ($mainExitCode -eq 0) {
            [Int32]$mainExitCode = 60008
        }
        Write-Error -Message "Module [$moduleAppDeployToolkitMain] failed to load: `n$($_.Exception.Message)`n `n$($_.InvocationInfo.PositionMessage)" -ErrorAction 'Continue'
        ## Exit the script, returning the exit code to SCCM
        If (Test-Path -LiteralPath 'variable:HostInvocation') {
            $script:ExitCode = $mainExitCode; Exit
        }
        Else {
            Exit $mainExitCode
        }
    }

    #endregion
    ##* Do not modify section above
    ##*===============================================
    ##* END VARIABLE DECLARATION
    ##*===============================================

    If ($deploymentType -ine 'Uninstall' -and $deploymentType -ine 'Repair') {
        ##*===============================================
        ##* PRE-INSTALLATION
        ##*===============================================
        [String]$installPhase = 'Pre-Installation'

        ## Show Welcome Message, close Internet Explorer if required, allow up to 3 deferrals, verify there is enough disk space to complete the install, and persist the prompt
        #Show-InstallationWelcome -CloseApps 'iexplore' -AllowDefer -DeferTimes 3 -CheckDiskSpace -PersistPrompt

        ## Show Progress Message (with the default message)
        Show-InstallationProgress

        ## <Perform Pre-Installation tasks here>

        ##*=============================================== 
        ##* INSTALLATION
        ##*===============================================
        [String]$installPhase = 'Installation'

        ## Handle Zero-Config MSI Installations
        If ($useDefaultMsi) {
            [Hashtable]$ExecuteDefaultMSISplat = @{ Action = 'Install'; Path = $defaultMsiFile }; If ($defaultMstFile) {
                $ExecuteDefaultMSISplat.Add('Transform', $defaultMstFile)
            }
            Execute-MSI @ExecuteDefaultMSISplat; If ($defaultMspFiles) {
                $defaultMspFiles | ForEach-Object { Execute-MSI -Action 'Patch' -Path $_ }
            }
        }

        ## <Perform Installation tasks here>

        # PSADT Install Section for Australian English Language Configuration

        # Define variables
        $LanguageSetting = "en-NZ"
        $GeoId = 183
        $KeyboardLayout = "1409:00001409" # Define New Zealand keyboard layout ID (matches keyboard used in New Zealand)
        $RebootRequired = $false

        # Log environment information
        Write-Log -Message "Is 64bit PowerShell: $([Environment]::Is64BitProcess)"
        Write-Log -Message "Is 64bit OS: $([Environment]::Is64BitOperatingSystem)"

        # Check if running as 32-bit process on 64-bit OS and relaunch as 64-bit process
        If ($ENV:PROCESSOR_ARCHITEW6432 -eq "AMD64") {
            Write-Log -Message "Running 32-bit PowerShell on 64-bit OS, restarting in 64-bit mode..." -Source "PreInstallation"
            $Invocation = $PSCommandPath
            Restart-Process -FilePath "$ENV:WINDIR\SysNative\WindowsPowershell\v1.0\PowerShell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$Invocation`" $commandArgs"
            Exit
        }

        # Import required modules
        Import-Module International -ErrorAction SilentlyContinue
        Import-Module LanguagePackManagement -ErrorAction SilentlyContinue

        # Check if modules were imported successfully
        if (-not (Get-Module -Name International)) {
            Write-Log -Message "Failed to import International module. This may affect language configuration." -Severity 2
        }
        if (-not (Get-Module -Name LanguagePackManagement)) {
            Write-Log -Message "Failed to import LanguagePackManagement module. This may affect language pack installation." -Severity 2
        }

        # Simply install en-NZ language pack
        Write-Log -Message "Installing language $LanguageSetting"
        try {
            Install-Language -Language $LanguageSetting -CopyToSettings
            $RebootRequired = $true
            Write-Log -Message "Language $LanguageSetting installed successfully."
        }
        catch {
            Write-Log -Message "Failed to install language $LanguageSetting. Error: $($_.Exception.Message)" -Severity 3
        }

        # Set system locale if needed
        if ($(Get-WinSystemLocale).Name -ne $LanguageSetting) {
            Write-Log -Message "Setting system locale to $LanguageSetting"
            try {
                Set-WinSystemLocale -SystemLocale $LanguageSetting
                $RebootRequired = $true
                Write-Log -Message "System locale set successfully."
            }
            catch {
                Write-Log -Message "Failed to set system locale. Error: $($_.Exception.Message)" -Severity 2
            }
        }

        # Set culture if needed
        if ($(Get-Culture).Name -ne $LanguageSetting) {
            Write-Log -Message "Setting system culture to $LanguageSetting"
            try {
                Set-Culture $LanguageSetting
                $RebootRequired = $true
                Write-Log -Message "System culture set successfully."
            }
            catch {
                Write-Log -Message "Failed to set system culture. Error: $($_.Exception.Message)" -Severity 2
            }
        }

        # Set geographical location if needed
        if ($(Get-WinHomeLocation).GeoId -ne $GeoId) {
            Write-Log -Message "Setting home location to New Zealand (GeoId: $GeoId)"
            try {
                Set-WinHomeLocation -GeoId $GeoId
                $RebootRequired = $true
                Write-Log -Message "Home location set successfully."
            }
            catch {
                Write-Log -Message "Failed to set home location. Error: $($_.Exception.Message)" -Severity 2
            }
        }

        # Set user language list and keyboard layout if needed
        if ($(Get-WinUserLanguageList | Select-Object -First 1).LanguageTag -ne $LanguageSetting) {
            Write-Log -Message "Setting user language list to $LanguageSetting with New Zealand keyboard layout"
            try {
                # Create new language list with New Zealand language and keyboard
                $NewLanguageList = New-WinUserLanguageList $LanguageSetting
                # Set keyboard layout for the language
                $NewLanguageList[0].InputMethodTips.Clear()
                $NewLanguageList[0].InputMethodTips.Add($KeyboardLayout) # Add New Zealand keyboard layout
                
                # Apply the new language list
                Set-WinUserLanguageList $NewLanguageList -Force
                $RebootRequired = $true
                Write-Log -Message "User language list and keyboard layout set successfully."
            }
            catch {
                Write-Log -Message "Failed to set user language list and keyboard layout. Error: $($_.Exception.Message)" -Severity 2
            }
        }

        # Set UI language if needed
        if ($(Get-SystemPreferredUILanguage) -ne $LanguageSetting) {
            Write-Log -Message "Setting UI language to $LanguageSetting"
            try {
                Set-SystemPreferredUILanguage -Language $LanguageSetting
                $RebootRequired = $true
                Write-Log -Message "UI language set successfully."
            }
            catch {
                Write-Log -Message "Failed to set UI language. Error: $($_.Exception.Message)" -Severity 2
            }
        }

        # Handle reboot requirement
        if ($RebootRequired -eq $true) {
            Write-Log -Message "Language changes require a reboot."
            # Set main exit code for reboot required so it persists to the end of the script
            $script:mainExitCode = 3010
            Write-Log -Message "Set exit code to 3010 to signal reboot requirement"
        }
        else {
            Write-Log -Message "Language configuration completed successfully. No reboot required."
        }

        ##*===============================================
        ##* POST-INSTALLATION
        ##*===============================================
        [String]$installPhase = 'Post-Installation'

        ## <Perform Post-Installation tasks here>

        ## Display a message at the end of the install
        If (-not $useDefaultMsi) {
            Show-InstallationPrompt -Message 'You can customize text to appear at the end of an install or remove it completely for unattended installations.' -ButtonRightText 'OK' -Icon Information -NoWait
        }
    }
    ElseIf ($deploymentType -ieq 'Uninstall') {
        ##*===============================================
        ##* PRE-UNINSTALLATION
        ##*===============================================
        [String]$installPhase = 'Pre-Uninstallation'

        ## Show Welcome Message, close Internet Explorer with a 60 second countdown before automatically closing
        Show-InstallationWelcome -CloseApps 'iexplore' -CloseAppsCountdown 60

        ## Show Progress Message (with the default message)
        Show-InstallationProgress

        ## <Perform Pre-Uninstallation tasks here>


        ##*===============================================
        ##* UNINSTALLATION
        ##*===============================================
        [String]$installPhase = 'Uninstallation'

        ## Handle Zero-Config MSI Uninstallations
        If ($useDefaultMsi) {
            [Hashtable]$ExecuteDefaultMSISplat = @{ Action = 'Uninstall'; Path = $defaultMsiFile }; If ($defaultMstFile) {
                $ExecuteDefaultMSISplat.Add('Transform', $defaultMstFile)
            }
            Execute-MSI @ExecuteDefaultMSISplat
        }

        ## <Perform Uninstallation tasks here>
        ElseIf ($deploymentType -ieq 'Uninstall') {
            # Check if running as 32-bit process on 64-bit OS and relaunch as 64-bit process
            If ($ENV:PROCESSOR_ARCHITEW6432 -eq "AMD64") {
                Write-Log -Message "Running 32-bit PowerShell on 64-bit OS, restarting in 64-bit mode..." -Source "PreInstallation"
                $Invocation = $PSCommandPath
                Restart-Process -FilePath "$ENV:WINDIR\SysNative\WindowsPowershell\v1.0\PowerShell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$Invocation`" $commandArgs"
                Exit
            }
        
            Write-Log -Message "Uninstalling New Zealand language pack" -Source "Uninstallation"
            
            Try {
                # Get the current language list
                $languageList = Get-WinUserLanguageList
                Write-Log -Message "Current languages: $($languageList.LanguageTag -join ', ')" -Source "Uninstallation"
                
                # Remove en-NZ if it exists
                $nzLang = $languageList | Where-Object {$_.LanguageTag -eq "en-NZ"}
                if ($nzLang) {
                    Write-Log -Message "Removing en-NZ from language list" -Source "Uninstallation"
                    $languageList.Remove($nzLang)
                    Set-WinUserLanguageList $languageList -Force
                } else {
                    Write-Log -Message "en-NZ not found in language list" -Source "Uninstallation"
                }
                
                # For en-GB (as NZ shows up as GB in system)
                $gbLang = $languageList | Where-Object {$_.LanguageTag -eq "en-GB"}
                if ($gbLang) {
                    Write-Log -Message "Removing en-GB from language list" -Source "Uninstallation"
                    $languageList.Remove($gbLang)
                    Set-WinUserLanguageList $languageList -Force
                }
                
                Write-Log -Message "Language pack removal completed" -Source "Uninstallation"
                Exit-Script -ExitCode 0
            }
            Catch {
                Write-Log -Message "Error uninstalling language pack: $_" -Source "Uninstallation" -Severity 3
                Exit-Script -ExitCode 1
            }
        }

        ##*===============================================
        ##* POST-UNINSTALLATION
        ##*===============================================
        [String]$installPhase = 'Post-Uninstallation'

        ## <Perform Post-Uninstallation tasks here>


    }
    ElseIf ($deploymentType -ieq 'Repair') {
        ##*===============================================
        ##* PRE-REPAIR
        ##*===============================================
        [String]$installPhase = 'Pre-Repair'

        ## Show Welcome Message, close Internet Explorer with a 60 second countdown before automatically closing
        Show-InstallationWelcome -CloseApps 'iexplore' -CloseAppsCountdown 60

        ## Show Progress Message (with the default message)
        Show-InstallationProgress

        ## <Perform Pre-Repair tasks here>

        ##*===============================================
        ##* REPAIR
        ##*===============================================
        [String]$installPhase = 'Repair'

        ## Handle Zero-Config MSI Repairs
        If ($useDefaultMsi) {
            [Hashtable]$ExecuteDefaultMSISplat = @{ Action = 'Repair'; Path = $defaultMsiFile; }; If ($defaultMstFile) {
                $ExecuteDefaultMSISplat.Add('Transform', $defaultMstFile)
            }
            Execute-MSI @ExecuteDefaultMSISplat
        }
        ## <Perform Repair tasks here>

        ##*===============================================
        ##* POST-REPAIR
        ##*===============================================
        [String]$installPhase = 'Post-Repair'

        ## <Perform Post-Repair tasks here>


    }
    ##*===============================================
    ##* END SCRIPT BODY
    ##*===============================================

    ## Call the Exit-Script function to perform final cleanup operations
    Exit-Script -ExitCode $mainExitCode
}
Catch {
    [Int32]$mainExitCode = 60001
    [String]$mainErrorMessage = "$(Resolve-Error)"
    Write-Log -Message $mainErrorMessage -Severity 3 -Source $deployAppScriptFriendlyName
    Show-DialogBox -Text $mainErrorMessage -Icon 'Stop'
    Exit-Script -ExitCode $mainExitCode
}