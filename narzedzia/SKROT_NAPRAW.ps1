# Naprawa skrotu "Struo aktualizacja": szuka starych skrotow zajmujacych ten sam klawisz, czysci je i tworzy skrot od nowa.
$ErrorActionPreference = 'Continue'
$app = Split-Path -Parent $PSScriptRoot
$cel = Join-Path $app 'AKTUALIZUJ.bat'
$klawisz = 'CTRL+ALT+U'
Write-Host "Folder aplikacji: $app"
if (-not (Test-Path $cel)) { Write-Host "BLAD: nie ma pliku $cel" -ForegroundColor Red; exit 1 }
$sh = New-Object -ComObject WScript.Shell
$miejsca = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'),
             [Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('CommonPrograms'), $app) | Select-Object -Unique
Write-Host ""
Write-Host "Skroty z klawiszem skrotu w tych miejscach:"
foreach ($m in $miejsca) {
  if (-not (Test-Path $m)) { continue }
  Get-ChildItem -Path $m -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    try { $l = $sh.CreateShortcut($_.FullName) } catch { return }
    if ($l.Hotkey) {
      $istnieje = Test-Path $l.TargetPath
      Write-Host (" - {0}`n     klawisz: {1}`n     cel: {2}  (istnieje: {3})" -f $_.FullName, $l.Hotkey, $l.TargetPath, $istnieje)
      if ($l.Hotkey -match 'F9' -or $_.Name -match 'ELEVATE|Struo') {
        $l.Hotkey = ''; try { $l.Save(); Write-Host "     -> klawisz wyczyszczony" -ForegroundColor Yellow } catch { Write-Host "     -> nie udalo sie zapisac: $($_.Exception.Message)" -ForegroundColor Red }
      }
    }
  }
}
$pulpit = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $pulpit 'Struo aktualizacja.lnk'
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = $cel; $s.WorkingDirectory = $app; $s.Hotkey = $klawisz; $s.Description = 'Struo: podmiana plikow i restart'
$s.Save()
Write-Host ""
Write-Host "Utworzono: $lnk  (klawisz $klawisz)" -ForegroundColor Green
Write-Host "WYLOGUJ SIE I ZALOGUJ PONOWNIE, wtedy Windows zacznie uzywac klawisza. Potem: Ctrl+Alt+U." -ForegroundColor Green
