import subprocess
import time
import os
import csv
import glob
import socket
import psutil

# --- CONFIGURATION ---
SERVER_SCRIPT = "file_server_processpool.py"
CLIENT_SCRIPT = "file_stress_test_client.py"
SERVER_PORT = 6667
OUTPUT_FILE = f"FINAL_results_{SERVER_SCRIPT.split('.')[0]}.csv"

OPERATIONS = ["upload", "download"]
FILE_SIZES = [10, 50, 100]
CLIENT_POOLS = [1, 5, 50]
SERVER_POOLS = [1, 5, 50]

CSV_HEADER = [
    'Nomor', 'Operasi', 'Volume (MB)', 'Client Workers', 'Server Workers',
    'Waktu Avg (s)', 'Throughput Avg (B/s)', 'Client Sukses', 'Client Gagal'
]

# --- UTILITIES ---
def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def kill_existing_servers():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if SERVER_SCRIPT in ' '.join(proc.info['cmdline']):
                print(f"[INFO] Terminating existing server: PID {proc.pid}")
                proc.terminate()
        except Exception:
            continue

# --- INIT ---
if os.path.exists(OUTPUT_FILE):
    os.remove(OUTPUT_FILE)
with open(OUTPUT_FILE, 'w', newline='') as f:
    csv.writer(f).writerow(CSV_HEADER)

test_number = 1
for server_pool in SERVER_POOLS:
    print("="*60 + f"\nMEMULAI SERVER [pool: {server_pool}]\n" + "="*60)

    kill_existing_servers()
    time.sleep(2)

    server_process = subprocess.Popen(
        ["python", SERVER_SCRIPT, "--pool-size", str(server_pool), "--port", str(SERVER_PORT)]
    )
    time.sleep(3)

    if not is_port_open("172.16.16.101", SERVER_PORT):
        print(f"[ERROR] Server failed to start on port {SERVER_PORT}. Skipping tests for pool={server_pool}.")
        server_process.terminate()
        server_process.wait()
        continue

    for file_size in FILE_SIZES:
        for client_pool in CLIENT_POOLS:
            for operation in OPERATIONS:
                for f in glob.glob("stress_test_results_*.csv"):
                    os.remove(f)

                print(f"\n--- Tes #{test_number}: Op={operation}, Size={file_size}MB, Client={client_pool}, Server={server_pool} ---")
                
                try:
                    subprocess.run(
                        [
                            "python", CLIENT_SCRIPT, "--operation", operation, "--file-sizes", str(file_size),
                            "--client-pools", str(client_pool), "--server-pools", str(server_pool),
                            "--port", str(SERVER_PORT), "--executor", "thread"
                        ],
                        check=True, timeout=3600
                    )

                    result_files = glob.glob("stress_test_results_*.csv")
                    if not result_files:
                        raise FileNotFoundError("Client result CSV not found.")
                    
                    with open(result_files[0], 'r') as f:
                        reader = csv.DictReader(f)
                        client_result = next(reader)

                    try:
                        avg_duration = float(client_result['avg_duration'])
                        avg_throughput_Bps = float(client_result['avg_throughput']) * 1024 * 1024
                        success_count = int(client_result['success_count'])
                        fail_count = int(client_result['fail_count'])
                    except (KeyError, ValueError) as e:
                        raise ValueError(f"Invalid result values: {e}")

                    print(f"HASIL: Sukses={success_count}, Gagal={fail_count}, Waktu={avg_duration:.2f}s")
                    with open(OUTPUT_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            test_number, operation, file_size, client_pool, server_pool,
                            f"{avg_duration:.4f}", f"{avg_throughput_Bps:.2f}", success_count, fail_count
                        ])

                except subprocess.TimeoutExpired:
                    print(f"[TIMEOUT] Test #{test_number} took too long.")
                    with open(OUTPUT_FILE, 'a', newline='') as f:
                        writer = csv.writer(f).writerow([test_number, operation, file_size, client_pool, server_pool, "TIMEOUT", 0, 0, client_pool])
                except Exception as e:
                    print(f"[ERROR] Test #{test_number} failed: {e}")
                    with open(OUTPUT_FILE, 'a', newline='') as f:
                        writer = csv.writer(f).writerow([test_number, operation, file_size, client_pool, server_pool, "ERROR", 0, 0, client_pool])
                
                test_number += 1

    print("="*60 + f"\nMENGHENTIKAN SERVER [pool: {server_pool}]\n" + "="*60)
    server_process.terminate()
    server_process.wait()

print("\n\n✅ SEMUA PENGUJIAN SELESAI!")
print(f"📄 Hasil lengkap tersimpan di file: {OUTPUT_FILE}")

