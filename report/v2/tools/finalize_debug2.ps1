$dir = "C:\Drive D\Projects\Smart Form autofilling\report\v2"
$src = Join-Path $dir "Smart_Form_Black_Book_2026-27_v2.docx"
$log = Join-Path $dir "tools\fin_debug.log"; "" | Set-Content $log
function L($m) { "$((Get-Date).ToString('HH:mm:ss')) $m" | Add-Content $log }
$w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($src); L "opened"
  foreach ($s in @(@(-20, 12, $true), @(-21, 12, $false), @(-22, 11, $false))) {
    $st = $d.Styles.Item($s[0]); $st.Font.Bold = $s[2]; $st.Font.Size = $s[1]; $st.Font.Name = 'Times New Roman'
    $st.ParagraphFormat.LineSpacingRule = 0; $st.ParagraphFormat.SpaceAfter = 2
  }
  L "styles"
  for ($pass = 0; $pass -lt 3; $pass++) { $d.Repaginate(); foreach ($t in $d.TablesOfContents) { $t.Update() | Out-Null }; L "pass $pass" }
  $d.Repaginate(); L ("pages " + $d.ComputeStatistics(2))
  $d.ExportAsFixedFormat((Join-Path $dir "tools\dbg_copy.pdf"), 17); L "exported"
  $d.SaveAs2((Join-Path $dir "tools\dbg_copy.docx"), 16); L "saveas"
  $d.Close($false); L "closed"
} finally { $w.Quit() }
