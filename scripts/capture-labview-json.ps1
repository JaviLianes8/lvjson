# Capture genuine Flatten To JSON output from a local LabVIEW install.
#
# Loads the shipped example "examples\Strings\Unflatten From JSON.vi" through LabVIEW's ActiveX
# VI Server, optionally sets its 'Input' control, runs it unmodified and saves the bytes of its
# 'JSON' indicator, which the example wires straight from Flatten To JSON.
#
#   pwsh scripts/capture-labview-json.ps1 -Mode nonfinite -OutDir tests/fixtures/labview2026
#
# Modes: default (the example's own input), nonfinite, strings, escapes, formats.
# -ViPath is required: copy "Unflatten From JSON.vi" and JSON_Example_Input.ctl from the
# install's examples\Strings folder to a scratch folder and point -ViPath at the copy, so the
# installed example is never touched. Quit LabVIEW when you are done.
param(
    [Parameter(Mandatory = $true)][string]$ViPath,
    [string]$OutDir = ".",
    [ValidateSet("default", "nonfinite", "strings", "escapes", "formats")][string]$Mode = "default"
)
$ErrorActionPreference = "Stop"
$BF = [System.Reflection.BindingFlags]
$CO = [System.__ComObject]

function Invoke-Com($obj, [string]$name, [object[]]$argv) {
    return $CO.InvokeMember($name, $BF::InvokeMethod, $null, $obj, $argv)
}
function Get-ComProperty($obj, [string]$name) {
    return $CO.InvokeMember($name, $BF::GetProperty, $null, $obj, $null)
}

# Late-bound IDispatch: PowerShell's own COM adapter does not bind LabVIEW.Application reliably.
$app = [Activator]::CreateInstance([Type]::GetTypeFromProgID("LabVIEW.Application"))
$vi = Invoke-Com $app "GetVIReference" @($ViPath, "", $false, 0)
$inp = Invoke-Com $vi "GetControlValue" @("Input")

if ($Mode -ne "default") {
    $data = $inp[1]
    $data[0, 0] = [double]::NaN
    $data[0, 1] = [double]::PositiveInfinity
    $data[0, 2] = [double]::NegativeInfinity
    $data[0, 3] = 0.0
    $data[1, 0] = 0.1
    $data[1, 1] = 1e300
    $data[1, 2] = -2.5e-310
    $data[1, 3] = 3.141592653589793
    $data[2, 0] = 1.7976931348623157e308
    $data[2, 1] = 5e-324
    $data[2, 2] = 123456789.125
    $data[2, 3] = -0.0
    if ($Mode -eq "formats") {
        # Values where C's %g switches between fixed and exponent form, and 2-digit exponents.
        $formats = @(
            1e-5, 0.0001, 0.00012345, 1e-300,
            1e19, 1e20, 1e21, 9007199254740992.0,
            1.2345678901234568e20, 1.5, -1e-10, 65536.0
        )
        for ($i = 0; $i -lt 12; $i++) { $data[[math]::Floor($i / 4), ($i % 4)] = $formats[$i] }
        $inp[0][0] = "formats"
    }
    $inp[1] = $data
    if ($Mode -eq "strings") { $inp[0][0] = 'Inf -Inf NaN "quoted" back\slash' }
    if ($Mode -eq "escapes") {
        $inp[0][0] = "tab`tnl`ncr`rctl" + [char]1 + " slash/ e-acute " + [char]0xE9 + " Infinity"
    }
    Invoke-Com $vi "SetControlValue" @("Input", $inp) | Out-Null
}

Invoke-Com $vi "Run" @($true) | Out-Null
$deadline = (Get-Date).AddSeconds(60)
# ExecState 1 is idle: the run has finished.
while ((Get-ComProperty $vi "ExecState") -ne 1 -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 200
}
if ((Get-ComProperty $vi "ExecState") -ne 1) {
    Invoke-Com $vi "Abort" @() | Out-Null
    throw "the example VI did not finish within 60 seconds"
}

# LabVIEW crosses the ActiveX boundary through the ANSI code page; undo that to get its bytes.
$json = Invoke-Com $vi "GetControlValue" @("JSON")
$bytes = [System.Text.Encoding]::GetEncoding(1252).GetBytes($json)
$out = Join-Path $OutDir ("flatten_to_json_" + $Mode + ".json")
[System.IO.File]::WriteAllBytes($out, $bytes)
"wrote $out ($($bytes.Length) bytes)"
