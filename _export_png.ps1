$ErrorActionPreference = 'Stop'
$base = 'C:\Users\Manager_21\ZCodeProject\pdf-invoice-bot-master'
$pptx = (Get-ChildItem -LiteralPath $base -Filter '*.pptx' | Select-Object -First 1).FullName
Write-Output "PPTX: $pptx"
$out = Join-Path $base '_pres_png'
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Path $out | Out-Null
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($pptx, $true, $false, $false)
$pres.Export($out, 'PNG', 1496, 841)
$pres.Close()
$pp.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
Get-ChildItem $out | ForEach-Object { Write-Output $_.Name }
