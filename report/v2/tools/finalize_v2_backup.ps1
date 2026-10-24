param([string]$Name = "Smart_Form_Black_Book_2026-27_v2", [int]$Timeout = 240)
# Opens the generated DOCX in Word, updates the TOC and the lists of figures and tables, exports the PDF,
# saves the DOCX and prints the page count. Requires Microsoft Word.
# Explicit Document.Repaginate() calls were observed to make the later export hang, so the TOC updates
# (which paginate by themselves) are the only layout passes; Word runs in a job with a timeout.
$dir = $PSScriptRoot
# A Word process killed earlier can leave an owner file (~$...) that blocks saving.
if (-not (Get-Process WINWORD -ErrorAction SilentlyContinue)) {
  Get-ChildItem -Force $dir -Filter '~$*.docx' | Remove-Item -Force
}
$job = Start-Job -ArgumentList (Join-Path $dir "$Name.docx"), (Join-Path $dir "$Name.pdf") {
  param($src, $pdf)
  $w = New-Object -ComObject Word.Application
  $w.Visible = $false
  $w.DisplayAlerts = 0
  try {
    $d = $w.Documents.Open($src)
    # TOC styles: Times New Roman, chapter entries bold, single spacing
    foreach ($s in @(@(-20, 12, $true), @(-21, 12, $false), @(-22, 11, $false), @(-23, 12, $false))) {
      $st = $d.Styles.Item($s[0]); $st.Font.Bold = $s[2]; $st.Font.Size = $s[1]; $st.Font.Name = 'Times New Roman'
      $st.ParagraphFormat.LineSpacingRule = 0; $st.ParagraphFormat.SpaceAfter = 2
    }
    # Two passes: the second picks up page numbers shifted by the first.
    for ($pass = 0; $pass -lt 2; $pass++) {
      foreach ($t in $d.TablesOfContents) { $t.Update() | Out-Null }
    }
    "pages (Word): " + $d.ComputeStatistics(2)
    $d.ExportAsFixedFormat($pdf, 17)
    $d.Save()
    $d.Close($false)
  } finally {
    $w.Quit()
  }
  "done: $pdf"
}
if (Wait-Job $job -Timeout $Timeout) { Receive-Job $job }
else { "TIMEOUT: Word did not finish"; Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force }
Remove-Job $job -Force
