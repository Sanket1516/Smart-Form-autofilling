param([string[]]$Names, [int]$Timeout = 45)
$dir = "C:\Drive D\Projects\Smart Form autofilling\report\v2\tools"
foreach ($n in $Names) {
  Get-ChildItem -Force $dir -Filter '~$*.docx' | Remove-Item -Force
  $t0 = Get-Date
  $job = Start-Job -ArgumentList $dir, $n {
    param($dir, $n)
    $w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
    $d = $w.Documents.Open("$dir\$n.docx"); $pg = $d.ComputeStatistics(2)
    $d.ExportAsFixedFormat("$dir\$n.pdf", 17); $d.Close($false); $w.Quit(); "pages $pg"
  }
  if (Wait-Job $job -Timeout $Timeout) { "$n OK $(Receive-Job $job) in $([int]((Get-Date)-$t0).TotalSeconds)s" }
  else { "$n TIMEOUT"; Get-Process WINWORD -EA SilentlyContinue | Stop-Process -Force; Start-Sleep 2 }
  Remove-Job $job -Force
}
