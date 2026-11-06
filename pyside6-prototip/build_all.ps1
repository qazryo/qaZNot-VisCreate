# qaZNot derleme: klasörlü exe (dist_qt), kurucu (dist_kurulum), tek dosyalık paylaşım exe'si (dist_paylas)
# Kullanım:  powershell -ExecutionPolicy Bypass -File build_all.ps1
$ErrorActionPreference = 'Stop'
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $proj
Set-Location $proj
$ex = @('--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtWebEngineWidgets','--exclude-module','PySide6.QtWebEngineQuick',
        '--exclude-module','PySide6.QtQml','--exclude-module','PySide6.QtQuick','--exclude-module','PySide6.Qt3DCore','--exclude-module','PySide6.QtCharts',
        '--exclude-module','PySide6.QtMultimedia','--exclude-module','PySide6.QtPdf','--exclude-module','PySide6.QtSql',
        '--exclude-module','PySide6.QtDataVisualization','--exclude-module','tkinter','--exclude-module','pyflakes')
$abi = Join-Path (Split-Path -Parent (Get-Command python).Source) 'abi3t-compat\python3t.dll'
$common = @('--noconfirm','--clean','--windowed','--name','qaZNot','--icon',"$root\icon.ico",'--version-file',"$proj\version_info.txt",
            '--paths','.','--hidden-import','qanvas','--hidden-import','qv_engine','--hidden-import','cryptography') + $ex
if (Test-Path $abi) { $common += @('--add-binary', "$abi;.") }

Write-Host '1/3 klasörlü exe (dist_qt)…'
python -m PyInstaller @common --distpath "$root\dist_qt" --workpath "$root\build_qt" --specpath "$root\build_qt" qaznote_qt.py | Select-Object -Last 1

Write-Host '2/3 kurucu (dist_kurulum)…'
$iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe" }
if (Test-Path $iscc) { & $iscc /Q "$proj\installer.iss" } else { Write-Host 'Inno Setup bulunamadı, kurucu atlandı.' }

Write-Host '3/3 tek dosyalık exe (dist_paylas)…'
python -m PyInstaller @common --onefile --distpath "$root\dist_paylas" --workpath "$root\build_paylas" --specpath "$root\build_paylas" qaznote_qt.py | Select-Object -Last 1
Write-Host 'Bitti.'
