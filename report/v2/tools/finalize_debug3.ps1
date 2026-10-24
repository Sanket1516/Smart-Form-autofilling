param([switch]$Styles, [switch]$Opts, [switch]$NoUpdate, [int]$Passes = 3)
$dir = "C:\Drive D\Projects\Smart Form autofilling\report\v2"
$src = Join-Path $dir "Smart_Form_Black_Book_2026-27_v2.docx"
$log = Join-Path $dir "tools\fin_debug.log"; "" | Set-Content $log
function L($m) { "$((Get-Date).ToString('HH:mm:ss')) $m" | Add-Content $log }
Get-ChildItem -Force $dir -Filter '~$*.docx' | Remove-Item -Force
$w = New-Object -ComObject Word.Application; $w.Visible = $false; $w.DisplayAlerts = 0
if ($Opts) { $w.Options.Pagination = $false; $w.Options.BackgroundSave = $false; $w.Options.CheckSpellingAsYouType = $false; $w.Options.CheckGrammarAsYouType = $false }
try {
  $d = $w.Documents.Open($src); L "opened styles=$Styles opts=$Opts noupdate=$NoUpdate"
  if ($Styles) {
    foreach ($s in @(@(-20, 12, $true), @(-21, 12, $false), @(-22, 11, $false))) {
      $st = $d.Styles.Item($s[0]); $st.Font.Bold = $s[2]; $st.Font.Size = $s[1]; $st.Font.Name = 'Times New Roman'
      $st.ParagraphFormat.LineSpacingRule = 0; $st.ParagraphFormat.SpaceAfter = 2
    }
    L "styles"
  }
  if (-not $NoUpdate) {
    for ($pass = 0; $pass -lt $Passes; $pass++) { $d.Repaginate(); foreach ($t in $d.TablesOfContents) { $t.Update() | Out-Null }; L "pass $pass" }
  }
  $d.Repaginate(); L ("pages " + $d.ComputeStatistics(2))
  $d.ExportAsFixedFormat((Join-Path $dir "tools\dbg_copy.pdf"), 17); L "exported"
  $d.SaveAs2((Join-Path $dir "tools\dbg_copy.docx"), 16); L "saveas"
  $d.Close($false); L "closed"
} catch { L ("ERR " + $_) } finally { $w.Quit(); L "quit" }
