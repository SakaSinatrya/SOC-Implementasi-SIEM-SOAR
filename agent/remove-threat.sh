#!/bin/bash
# Membaca data alert berformat JSON dari Wazuh Manager
read INPUT_JSON

# Ekstrak path file (Otomatis mencari di log VirusTotal ATAU Syscheck biasa)
FILE_PATH=$(echo "$INPUT_JSON" | jq -r '.parameters.alert.data.virustotal.source.file // .parameters.alert.syscheck.path // empty')

# Validasi dan eksekusi penghapusan
if [ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ]; then
    rm -f "$FILE_PATH"
    echo "$(date) - [SOAR] SUKSES menghapus malware: $FILE_PATH" >> /var/ossec/logs/active-responses.log
else
    # Jika gagal, catat JSON mentahnya agar kita bisa periksa
    echo "$(date) - [SOAR] GAGAL. File tidak ditemukan. JSON: $INPUT_JSON" >> /var/ossec/logs/active-responses.log
fi
