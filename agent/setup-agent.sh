//untuk agent1 (target)

#!/bin/bash
echo "[*] Memulai instalasi dependensi endpoint..."
sudo apt-get update && sudo apt-get install -y jq php libapache2-mod-php

echo "[*] Mengonfigurasi skrip kustom Active Response..."
sudo cp remove-threat.sh /var/ossec/active-response/bin/
sudo chmod 750 /var/ossec/active-response/bin/remove-threat.sh
sudo chown root:wazuh /var/ossec/active-response/bin/remove-threat.sh

echo "[*] Melakukan restart layanan sistem..."
sudo systemctl restart apache2
sudo systemctl restart wazuh-agent

echo "[+] Deployment selesai dengan sukses!"
