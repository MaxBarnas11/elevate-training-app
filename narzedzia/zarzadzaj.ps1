# Pomocnik dla AKTUALIZUJ.bat.
#   zamknij : zamyka stara karte Struo w przegladarce, aplikacje i WSZYSTKIE okna konsoli START.bat
#             (takze osierocone po poprzednich uruchomieniach)
#   otworz  : po starcie serwera otwiera aplikacje w przegladarce
param([string]$Tryb = "zamknij")
$ErrorActionPreference = "SilentlyContinue"
$port = 8501
$przegladarki = "chrome", "msedge", "firefox", "brave", "opera", "vivaldi"
# Tytul karty STRUO (albo dawny OVRLD / ELEVATE): "STRUO", "Treningi <kropka> STRUO" itp. (np. strona repozytorium na GitHubie sie nie zalicza)
$sep = "[" + [char]0x00B7 + "|\-]"
$wzorzec = "^(.+ $sep )?(STRUO|OVRLD|ELEVATE)( $sep .+)?$"

function Karty-Struo {
    Get-Process -Name $przegladarki | Where-Object {
        $t = $_.MainWindowTitle -replace ' - (Google Chrome|Microsoft.? Edge|Mozilla Firefox|Brave|Opera|Vivaldi)$', ''
        $_.MainWindowHandle -ne 0 -and $t -cmatch $wzorzec
    }
}

if ($Tryb -eq "zamknij") {
    # 1) stara karta (okno, w ktorym Struo jest aktywna karta) zamykana skrotem Ctrl+W
    $sh = New-Object -ComObject WScript.Shell
    foreach ($p in @(Karty-Struo)) {
        if ($sh.AppActivate($p.Id)) {
            Start-Sleep -Milliseconds 400
            $sh.SendKeys("^w")
            Start-Sleep -Milliseconds 400
        }
    }
    # 2) okna konsoli START.bat razem z procesami potomnymi, potem wszystko, co slucha na porcie aplikacji
    Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" |
        Where-Object { $_.CommandLine -match 'START\.bat|GOSC\.bat' } |
        ForEach-Object { & taskkill /F /T /PID $_.ProcessId | Out-Null }
    Get-NetTCPConnection -LocalPort $port -State Listen |
        ForEach-Object { & taskkill /F /T /PID $_.OwningProcess | Out-Null }
    exit 0
}

if ($Tryb -eq "otworz") {
    # Aplikacja nasluchuje na adresie Tailscale (albo 127.0.0.1), wiec sprawdzamy oba i otwieramy ten, ktory odpowiada
    $adresy = @()
    $exe = Get-Command tailscale | Select-Object -First 1 -ExpandProperty Source
    if (-not $exe -and (Test-Path "$env:ProgramFiles\Tailscale\tailscale.exe")) { $exe = "$env:ProgramFiles\Tailscale\tailscale.exe" }
    if ($exe) {
        $ip = (& $exe ip -4 | Select-Object -First 1)
        if ($ip -match '^100\.') { $adresy += $ip }
    }
    $adresy += "127.0.0.1"
    for ($i = 0; $i -lt 60; $i++) {
        foreach ($a in $adresy) {
            try {
                $c = New-Object Net.Sockets.TcpClient
                $c.Connect($a, $port)
                $c.Close()
                # Logowanie Google dziala tylko pod "localhost" (nie pod 127.0.0.1), wiec tak otwieramy adres lokalny
                $nazwa = if ($a -eq "127.0.0.1") { "localhost" } else { $a }
                Start-Process "http://${nazwa}:$port"
                exit 0
            } catch { }
        }
        Start-Sleep -Milliseconds 500
    }
}
