param([string]$Name = "Smart_Form_Black_Book_2026-27")
# Opens the generated DOCX in Word, updates every field (TOC, figure and table lists, page numbers) twice,
# saves the DOCX and exports the PDF. Requires Microsoft Word.
$dir = $PSScriptRoot
$src = Join-Path $dir "$Name.docx"
$pdf = Join-Path $dir "$Name.pdf"
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($src)
  # TOC styles: chapter entries bold, single spacing, Times New Roman
  foreach ($s in @(@(-20,12,$true),@(-21,12,$false),@(-22,11,$false))) {
    $st = $d.Styles.Item($s[0]); $st.Font.Bold = $s[2]; $st.Font.Size = $s[1]; $st.Font.Name = 'Times New Roman'; $st.ParagraphFormat.LineSpacingRule = 0
  }
  for ($pass = 0; $pass -lt 3; $pass++) {
    $d.Repaginate()
    foreach ($t in $d.TablesOfContents) { $t.Update() | Out-Null }
    $d.Fields.Update() | Out-Null
  }
  $d.Repaginate()
  "pages: " + $d.ComputeStatistics(2)
  $d.Save()
  $d.ExportAsFixedFormat($pdf, 17)
  $d.Close($false)
} finally {
  $w.Quit()
}
"done: $pdf"
