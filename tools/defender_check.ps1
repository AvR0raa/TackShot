$ErrorActionPreference = "SilentlyContinue"
"=== Defender 检测历史（最近 10 条）==="
$t = Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending | Select-Object -First 10
if ($t) {
    foreach ($x in $t) {
        $x.InitialDetectionTime.ToString("MM-dd HH:mm") + "  " + $x.ThreatID + "  " + ($x.Resources -join ";")
    }
} else { "（没有检测记录）" }

""
"=== Defender 当前状态 ==="
$s = Get-MpComputerStatus
if ($s) {
    "RealTimeProtectionEnabled = " + $s.RealTimeProtectionEnabled
    "AntivirusEnabled          = " + $s.AntivirusEnabled
} else { "（读不到 Defender 状态，可能被第三方杀软接管）" }

""
"=== 第三方杀软（SecurityCenter2）==="
Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | ForEach-Object { $_.displayName }
