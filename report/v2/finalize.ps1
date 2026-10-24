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
# Refuse to run while the target document is open in someone's Word window: saving would fail and the export would hang.
$lock = Join-Path $dir ('~$' + $Name.Substring(2) + '.docx')
if ((Test-Path -LiteralPath $lock) -and (Get-Process WINWORD -ErrorAction SilentlyContinue)) {
  "STOPPED: $Name.docx is open in Word. Close it and run again."
  exit 1
}
# Word processes that belong to the user; a timeout must never close these.
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object Id)
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
    # The first update ran before Word had laid out every page, so the saved field results could be wrong even though the
    # export (which lays out the whole document) printed correct numbers. Update again now that the layout is complete.
    $d.Range(0, $end).Fields.Update() | Out-Null
    $d.Save()
    $d.Close($false)
  } finally {
    $w.Quit()
  }
  "done: $pdf"
}
if (Wait-Job $job -Timeout $Timeout) { Receive-Job $job }
else {
  "TIMEOUT: Word did not finish"
  # close only the Word instance started by this script
  Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | Stop-Process -Force
}
Remove-Job $job -Force
