import subprocess
import re
import csv
import sys
import time
from statistics import mean, stdev
from collections import defaultdict

REST_CLIENT_PATH = "../client2/client/build/rest_benchmark_app" 
GRPC_CLIENT_SCRIPT = "python3 ../client6/client_py/grpc_benchmark_core.py" 

TEST_COUNT = 20  
LOT_ID_TO_BID = 1  

BASE_USERNAME = "bench_user_"
BASE_PASSWORD = "password123"

OUTPUT_FILE = "comparison_results.csv"

METRIC_PATTERN = re.compile(r"(REST|GRPC)_(\w+)_Latency:\s*(\d+\.?\d*)ms")

def run_client_and_capture(command, user, passwd, lot_id):
    full_command = f"{command} {user} {passwd} {lot_id}"
    
    try:
        result = subprocess.run(
            full_command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=15, 
            check=False
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return "EXECUTION_TIMEOUT", ""
    except Exception as e:
        return f"EXECUTION_ERROR: {e}", ""

def run_benchmark_cycle(lot_id):
    raw_results = []
    
    print(f"\nRunning benchmark: {TEST_COUNT} iterations per client")
    
    for i in range(1, TEST_COUNT + 1):
        username = f"{BASE_USERNAME}{i}_{int(time.time())}" 
        
        stdout_rest, stderr_rest = run_client_and_capture(REST_CLIENT_PATH, username, BASE_PASSWORD, lot_id)
        
        stdout_grpc, stderr_grpc = run_client_and_capture(GRPC_CLIENT_SCRIPT, username, BASE_PASSWORD, lot_id)
        
        for client_type, output in [("REST", stdout_rest), ("GRPC", stdout_grpc)]:
            
            if "EXECUTION_ERROR" in output or "EXECUTION_TIMEOUT" in output:
                print(f"\n[{client_type}][ERROR] Execution failed for iteration {i}. Output: {output}")
                continue

            for line in output.splitlines():
                match = METRIC_PATTERN.search(line)
                if match:
                    raw_results.append({
                        'Client': client_type,
                        'Operation': match.group(2),
                        'Latency_ms': float(match.group(3)),
                        'Iteration': i
                    })
                
        if stderr_rest or stderr_grpc:
             print(f"\n[WARNING] Check server/client logs.")

        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.5) 

    return raw_results

def aggregate_and_save(raw_results):
    
    aggregated = defaultdict(lambda: defaultdict(list))
    
    for r in raw_results:
        key = (r['Client'], r['Operation'])
        aggregated[key]['Latency'].append(r['Latency_ms'])

    with open(OUTPUT_FILE, 'w', newline='') as csvfile:
        fieldnames = ['Client', 'Operation', 'Count', 'Avg_ms', 'Med_ms', 'P95_ms', 'StdDev_ms']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        print("\n\n Агреговані Результати")
        print(f"{'Client':<8} {'Operation':<15} {'Count':<8} {'Avg (ms)':<10} {'Med (ms)':<10} {'P95 (ms)':<10} {'StdDev (ms)':<12}")
        print("-" * 75)

        for (client, op), data in aggregated.items():
            latencies = sorted(data['Latency'])
            count = len(latencies)

            if count == 0: continue

            avg = mean(latencies)
            med = latencies[count // 2]
            p95 = latencies[int(count * 0.95)]
            std_dev = stdev(latencies) if count > 1 else 0

            writer.writerow({
                'Client': client,
                'Operation': op,
                'Count': count,
                'Avg_ms': f"{avg:.3f}",
                'Med_ms': f"{med:.3f}",
                'P95_ms': f"{p95:.3f}",
                'StdDev_ms': f"{std_dev:.3f}"
            })
            
            print(f"{client:<8} {op:<15} {count:<8} {avg:.3f} {med:.3f} {p95:.3f} {std_dev:.3f}")

    print("\nЗАВЕРШЕНО")
    print(f"Детальні результати збережено у {OUTPUT_FILE}")


if __name__ == '__main__':
    raw_data = run_benchmark_cycle(lot_id=LOT_ID_TO_BID) 
    aggregate_and_save(raw_data)