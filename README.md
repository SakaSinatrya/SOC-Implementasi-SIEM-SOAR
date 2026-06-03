# Wazuh SIEM & SOAR — Deteksi DDoS dan Malware di Azure

> Implementasi arsitektur SIEM terdistribusi berbasis Wazuh di Microsoft Azure dengan skenario Proof of Concept (PoC) serangan DDoS multi-vektor dan deteksi malware, dilengkapi **Wazuh Active Response** sebagai mekanisme SOAR untuk pemblokiran otomatis IP penyerang secara real-time.

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

Proyek ini mengimplementasikan sistem keamanan berlapis (*Defense in Depth*) melalui deployment **Wazuh SIEM** (Security Information and Event Management) pada infrastruktur cloud **Microsoft Azure for Students**. Sistem diuji ketahanannya menggunakan simulasi serangan **Distributed Denial of Service (DDoS)** multi-vektor — TCP SYN Flood (Layer 4) dan HTTP Flood (Layer 7). Selain deteksi, sistem juga dilengkapi **Wazuh Active Response** sebagai komponen SOAR yang secara otomatis memblokir IP penyerang melalui `iptables` di agent target begitu anomali terdeteksi secara *real-time*.

---

## Arsitektur Sistem

### Topologi

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Azure Cloud (rg-wazuh-lab)                      │
│                                                                          │
│  ┌─────────────────────┐  VNet Peering  ┌────────────────────────────┐   │
│  │    wazuh-agent2     │◄──────────────►│     wazuh-manager-vnet     │   │
│  │    East Asia        │                │     Indonesia Central      │   │
│  │    104.214.184.244  │                │                            │   │
│  │                     │                │  ┌──────────────────────┐  │   │
│  │  [Attacker]         │  DDoS Attack   │  │   wazuh-manager      │  │   │
│  │  hping3 · ab        ├──────────────────►│   70.153.136.38      │  │   │
│  │  ddos_poc.py        │                │  │   SIEM · Dashboard   │  │   │
│  │                     |                │  │   Indexer            │  │   │
│  │   IP Blocked        │                |  └──────────┬───────────┘  |   | 
│  │  (iptables DROP)    │◄ ─ ─ ─ ─ ─ ─ ─ | ─ ─ ─ ─ ─ ─ │ Active Resp  │   │   
│  └─────────────────────┘  firewall-drop │             │ logs         │   │
│                                         │  ┌──────────▼───────────┐  │   │
│                                         │  │   wazuh-agent1       │  │   │
│                                         │  │   70.153.137.47      │  │   │
│                                         │  │   Apache2 · Target   │  │   │
│                                         │  │   iptables DROP      │  │   │
│                                         │  └──────────────────────┘  │   │
│                                         └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Spesifikasi VM

| Hostname | Region | Size VM | vCPU / RAM | IP Publik | Peran |
|----------|--------|---------|------------|-----------|-------|
| `wazuh-manager` | Indonesia Central | Standard_B2as_v2 | 2 vCPU, 8 GB | 70.153.136.38 | SIEM Manager · Dashboard · Indexer |
| `wazuh-agent1` | Indonesia Central | Standard_B2als_v2 | 2 vCPU, 4 GB | 70.153.137.47 | **Target** — Apache2 web server |
| `wazuh-agent2` | East Asia | Standard_B2als_v2 | 2 vCPU, 4 GB | 104.214.184.244 | **Attacker** — hping3, ab, ddos_poc.py |

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

---

## Hasil Deteksi

| Rule ID | Level | Alert | Kondisi |
|---------|-------|-------|---------|
| 202 | 7 | Agent event queue is 90% full | Traffic mulai membebani agen |
| 203 | 9 | Agent event queue is full. Events may be lost | Buffer agen mencapai batas |
| **204** | **12** | **Agent event queue is flooded** | **DDoS terdeteksi — Critical** |
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
Manager kirim perintah firewall-drop ke agent1 (via port 1514)
        │
        ▼
wazuh-execd di agent1 jalankan firewall-drop
        │
        ▼
iptables DROP untuk IP penyerang (104.214.184.244)
— packet dari agent2 dibuang sebelum sampai ke Apache
```

### Konfigurasi Active Response (`/var/ossec/etc/ossec.conf` di Manager)

```xml
<ossec_config>
  <active-response>
    <command>firewall-drop</command>
    <location>local</location>
    <rules_id>31151</rules_id>
  </active-response>
</ossec_config>
```
 
| Parameter | Nilai | Keterangan |
|-----------|-------|------------|
| `command` | `firewall-drop` | Script built-in Wazuh untuk iptables DROP |
| `location` | `local` | Eksekusi langsung di agent yang mendeteksi anomali (agent1) |
| `rules_id` | `31151` | Trigger: multiple HTTP 400 errors from same source IP |

### Verifikasi di agent1

```bash
# Cek rule iptables yang ditambahkan Wazuh
sudo iptables -L INPUT -n --line-numbers | grep DROP

# Cek log active response
sudo tail -f /var/ossec/logs/active-responses.log
```

---

