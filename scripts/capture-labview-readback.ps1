# Capture what LabVIEW's Unflatten From JSON reads back from Flatten To JSON output.
#
# Runs the shipped example "examples\Strings\Unflatten From JSON.vi" unmodified through
# LabVIEW's ActiveX VI Server with chosen DBL values, then saves two things from one run:
#   readback_<mode>.json       the bytes of its 'JSON' indicator (Flatten To JSON output)
#   readback_<mode>.values.json the doubles its Unflatten From JSON nodes returned from that
#                              same string, as IEEE 754 bit patterns (16 hex digits each)
#
#   pwsh scripts/capture-labview-readback.ps1 -ViPath <copy of the example> -Mode nonfinite `
#       -OutDir tests/fixtures/labview2026
#
# -ViPath must point at a copy of "Unflatten From JSON.vi" (with JSON_Example_Input.ctl next to
# it), so the installed example is never touched. The example reads 'Unflattened First Data
# Row' (path Data[0]), 'Unflattened Cell' (path Data[1][3]) and 'Remaining Unflattened Data'
# (the eight values of rows 1 and 2) from the JSON string with the node's default settings.
param(
    [Parameter(Mandatory = $true)][string]$ViPath,
    [string]$OutDir = ".",
    [ValidateSet("nonfinite", "formats")][string]$Mode = "nonfinite"
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
function Get-Bits([double]$value) {
    return [BitConverter]::DoubleToInt64Bits($value).ToString("x16")
}

$values = @(
    [double]::NaN, [double]::PositiveInfinity, [double]::NegativeInfinity, 0.0,
    0.1, 1e300, -2.5e-310, 3.141592653589793,
    1.7976931348623157e308, 5e-324, 123456789.125, -0.0
)
if ($Mode -eq "formats") {
    $values = @(
        1e-5, 0.0001, 0.00012345, 1e-300,
        1e19, 1e20, 1e21, 9007199254740992.0,
        1.2345678901234568e20, 1.5, -1e-10, 65536.0
    )
}

$app = [Activator]::CreateInstance([Type]::GetTypeFromProgID("LabVIEW.Application"))
try {
    $vi = Invoke-Com $app "GetVIReference" @($ViPath, "", $false, 0)
    $inp = Invoke-Com $vi "GetControlValue" @("Input")
    $data = $inp[1]
    for ($i = 0; $i -lt 12; $i++) { $data[[math]::Floor($i / 4), ($i % 4)] = $values[$i] }
    $inp[1] = $data
    $inp[0][0] = "readback " + $Mode
    Invoke-Com $vi "SetControlValue" @("Input", $inp) | Out-Null

    Invoke-Com $vi "Run" @($true) | Out-Null
    $deadline = (Get-Date).AddSeconds(60)
    # ExecState 1 is idle: the run has finished.
    while ((Get-ComProperty $vi "ExecState") -ne 1 -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
    }
    if ((Get-ComProperty $vi "ExecState") -ne 1) { throw "the example VI did not finish in 60 s" }

    # LabVIEW crosses the ActiveX boundary through the ANSI code page; undo that to get its bytes.
    $json = Invoke-Com $vi "GetControlValue" @("JSON")
    $bytes = [System.Text.Encoding]::GetEncoding(1252).GetBytes($json)
    [System.IO.File]::WriteAllBytes((Join-Path $OutDir ("readback_" + $Mode + ".json")), $bytes)

    $row = Invoke-Com $vi "GetControlValue" @("Unflattened First Data Row")
    $cell = Invoke-Com $vi "GetControlValue" @("Unflattened Cell")
    $rest = Invoke-Com $vi "GetControlValue" @("Remaining Unflattened Data")
    # The indicator holds the eight values of Data rows 1 and 2, each in its own element.
    $remaining = @()
    foreach ($item in $rest) { foreach ($x in $item) { $remaining += Get-Bits $x } }
    $record = [ordered]@{
        "input_bits" = @($values | ForEach-Object { Get-Bits $_ })
        "unflattened_first_data_row" = @($row | ForEach-Object { Get-Bits $_ })
        "unflattened_cell" = Get-Bits $cell
        "remaining_unflattened_data" = $remaining
    }
    $text = ($record | ConvertTo-Json -Depth 5) -replace "`r`n", "`n"
    $target = Join-Path $OutDir ("readback_" + $Mode + ".values.json")
    [System.IO.File]::WriteAllText($target, $text + "`n", (New-Object System.Text.UTF8Encoding $false))
    "wrote readback_$Mode.json ($($bytes.Length) bytes) and readback_$Mode.values.json"
} finally {
    Invoke-Com $app "Quit" @() | Out-Null
}
