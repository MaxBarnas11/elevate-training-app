# Sprawdza, co obciaza komputer i ile kopii aplikacji dziala. Nic nie zmienia, nie czyta plikow z danymi ani kluczami.
$wyj = Join-Path $PSScriptRoot 'wynik_wydajnosci.txt'
$o = New-Object System.Collections.Generic.List[string]
$os = Get-CimInstance Win32_OperatingSystem
$o.Add(("Data: {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm')))
$o.Add(("Pamiec RAM: wolne {0:N1} GB z {1:N1} GB" -f ($os.FreePhysicalMemory / 1MB), ($os.TotalVisibleMemorySize / 1MB)))
$o.Add(("Od uruchomienia komputera: {0:N1} godz." -f ((Get-Date) - $os.LastBootUpTime).TotalHours))
$cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
$o.Add("Obciazenie procesora teraz: $cpu %")
$o.Add("")
$o.Add("=== Procesy python / streamlit (kazda kopia aplikacji to osobny proces) ===")
$py = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|streamlit' }
if (-not $py) { $o.Add("(brak)") }
foreach ($x in $py) {
  $p = Get-Process -Id $x.ProcessId -ErrorAction SilentlyContinue
  $cmd = [string]$x.CommandLine
  if ($cmd.Length -gt 170) { $cmd = $cmd.Substring(0, 170) + '...' }
  $start = if ($p) { $p.StartTime.ToString('MM-dd HH:mm') } else { '?' }
  $ram = if ($p) { [math]::Round($p.WorkingSet64 / 1MB) } else { 0 }
  $cs = if ($p) { [math]::Round($p.CPU, 0) } else { 0 }
  $o.Add(("PID {0} | start {1} | RAM {2} MB | CPU {3} s | {4}" -f $x.ProcessId, $start, $ram, $cs, $cmd))
}
$o.Add("")
$o.Add("=== Porty aplikacji (8501-8520) ===")
$l = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8501 -and $_.LocalPort -le 8520 }
if (-not $l) { $o.Add("(nic nie nasluchuje)") }
foreach ($x in $l) { $o.Add(("port {0} na adresie {1}, proces {2}" -f $x.LocalPort, $x.LocalAddress, $x.OwningProcess)) }
$e = @(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -ge 8501 -and $_.LocalPort -le 8520 })
$o.Add(("Otwarte polaczenia z przegladarek/telefonu do aplikacji: {0}" -f $e.Count))
$o.Add("")
$o.Add("=== 10 procesow z najwiekszym zuzyciem procesora (lacznie od startu) ===")
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
  $o.Add(("{0} (PID {1}) | CPU {2} s | RAM {3} MB" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU, 0), [math]::Round($_.WorkingSet64 / 1MB)))
}
$o.Add("")
$o.Add(("Okna konsoli (cmd/powershell) otwarte teraz: {0}" -f @(Get-Process cmd, powershell, pwsh -ErrorAction SilentlyContinue).Count))
$o | Out-File -FilePath $wyj -Encoding utf8
$o | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Zapisano: $wyj"
