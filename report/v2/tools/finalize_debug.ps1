$dir = "C:\Drive D\Projects\Smart Form autofilling\report\v2"
$src = Join-Path $dir "Smart_Form_Black_Book_2026-27_v2.docx"
$log = "C:\Drive D\Projects\Smart Form autofilling\report\v2\tools\fin_debug.log"; "" | Set-Content $log
function L($m) { "$((Get-Date).ToString('HH:mm:ss')) $m" | Add-Content $log }
$w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($src); L "opened"
  $d.Repaginate(); L ("pages " + $d.ComputeStatistics(2))
  $d.SaveAs2("C:\Drive D\Projects\Smart Form autofilling\report\v2\tools\dbg_copy.docx", 16); L "saveas docx"
  $d.ExportAsFixedFormat("C:\Drive D\Projects\Smart Form autofilling\report\v2\tools\dbg_copy.pdf", 17); L "exported"
  $d.Close($false); L "closed"
} finally { $w.Quit() }

