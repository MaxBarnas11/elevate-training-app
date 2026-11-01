#!/bin/bash
# Codzienna kopia baz Struo. Uzywa "sqlite3 .backup", wiec kopia jest spojna nawet gdy aplikacja akurat zapisuje.
# Uruchamianie raz dziennie: crontab -e  ->  30 3 * * * /home/struo/app/serwer/kopia.sh
# Kopie trafiaja do /home/struo/kopie (lokalnie). PAMIETAJ: prawdziwa kopia zapasowa musi lezec POZA serwerem
# (np. rclone na Twoj dysk w chmurze albo pobranie na komputer), bo awaria dysku zabiera obie rzeczy naraz.
set -euo pipefail
APP=/home/struo/app
CEL=/home/struo/kopie/$(date +%Y-%m-%d)
mkdir -p "$CEL"
chmod 700 /home/struo/kopie "$CEL"
while IFS= read -r -d '' plik; do
  nazwa=$(echo "${plik#$APP/}" | tr '/' '_')
  sqlite3 "$plik" ".backup '$CEL/$nazwa'"
done < <(find "$APP" -name '*.db' -not -path '*/.venv/*' -print0)
# Zostaw kopie z ostatnich 14 dni
find /home/struo/kopie -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
