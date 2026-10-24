param([string]$Name = "Smart_Form_Black_Book_2026-27_v5", [int]$Timeout = 240)
# Opens the generated DOCX in Word, fills in the page numbers of the table of contents and the lists of figures and
# tables (PAGEREF fields in the preliminary pages), exports the PDF, saves the DOCX and prints the page count.
# Requires Microsoft Word. Explicit Document.Repaginate() calls were observed to make the later export hang,
# so only the fields before the bookmark "BodyStart" (Chapter 1) are updated; Word runs in a job with a timeout.
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
    $end = $d.Bookmarks.Item("BodyStart").Range.Start
    $d.Range(0, $end).Fields.Update() | Out-Null
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
