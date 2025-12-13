# -*- coding: utf-8 -*-
import requests
import threading
import time
import random
import sys
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev

SERVER_URL = 'http://127.0.0.1:5000' 

USERS_A = 30
DURATION_A = 30 
USERS_B = 20
DURATION_B = 30

NUMBER_OF_TOTAL_USERS = USERS_A + USERS_B 
BASE_USERNAME = "rest_load_user_"
TEST_LOT_DURATION_MINUTES = 5 

ALL_RESPONSE_TIMES = []
BID_ATTEMPTS = 0
BID_SUCCESS = 0
LOCK = threading.Lock()


def get_formatted_time(offset_seconds=0):
    dt = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return dt.isoformat().replace('+00:00', 'Z').split('.')[0] + "Z"

def measure_request(method_name, url, method='GET', data=None, headers=None, status_code_expected=200, is_bid_status=False):

    global ALL_RESPONSE_TIMES
    
    start = time.perf_counter()
    response = None
    
    try:
        response = requests.request(method, url, json=data, headers=headers, timeout=10)
            
        duration = (time.perf_counter() - start) * 1000
        
        if method_name == 'ListAuctions': 
            method_name = 'GetAuctions'
        if is_bid_status:
            method_name = 'GetLotStatus'
        
        if (response and response.status_code == status_code_expected) or \
           (method_name in ['Register', 'Login (Fallback)'] and response and response.status_code != 200):
            
            if method_name == 'Register' and response.status_code != 200:
                 with LOCK: ALL_RESPONSE_TIMES.append(('Register', duration))
            elif method_name == 'Login (Fallback)':
                 with LOCK: ALL_RESPONSE_TIMES.append(('Login (Fallback)', duration))
            elif method_name not in ['Register', 'Login (Fallback)']:
                 with LOCK: ALL_RESPONSE_TIMES.append((method_name, duration))

            return response
            
        else:
            return response 

    except requests.exceptions.RequestException:
        return None

def register_user(username, password):
    
    start = time.perf_counter()
    response = None
    try:
        response = requests.request(
            'POST', 
            f'{SERVER_URL}/auth/register/', 
            json={'username': username, 'password': password},
            timeout=10
        )
        duration = (time.perf_counter() - start) * 1000
        
        with LOCK: ALL_RESPONSE_TIMES.append(('Register', duration))
        
        if response and response.status_code == 200:
            return response.json().get('token')
        
    except requests.exceptions.RequestException:
        pass
    
    return None

def login_user(username, password):
    
    start = time.perf_counter()
    response = None
    try:
        response = requests.request(
            'POST', 
            f'{SERVER_URL}/auth/login/', 
            json={'username': username, 'password': password},
            timeout=10
        )
        duration = (time.perf_counter() - start) * 1000
        
        with LOCK: ALL_RESPONSE_TIMES.append(('Login (Fallback)', duration))
        
        if response and response.status_code == 200:
            return response.json().get('token')
            
    except requests.exceptions.RequestException:
        pass
        
    return None

def register_or_login(username, password):
    
    token = register_user(username, password)
    
    if not token:
        token = login_user(username, password)
            
    return token

def create_active_test_lot():
    creator_username = "LoadTestCreator"
    creator_password = "SecurePassword123"
    
    token = register_or_login(creator_username, creator_password)
    if not token:
        print("[SETUP] Failed to get token for lot creator.")
        return None, None
        
    headers = {'Authorization': f'Bearer {token}'}
    start_time_str = get_formatted_time(offset_seconds=-5)

    lot_data = {
        "title": f"REST Stress Test Lot {int(time.time())}",
        "description": "Lot created for REST performance testing.",
        "startingPrice": 100.00,
        "startTime": start_time_str,
        "durationMinutes": TEST_LOT_DURATION_MINUTES,
    }
    
    response = measure_request(
        'CreateLot (Setup)',
        f'{SERVER_URL}/auctions/',
        method='POST',
        data=lot_data,
        headers=headers,
        status_code_expected=201 
    )
    
    if response and response.status_code == 201:
        lot_id = response.json()['lot']['id']
        print(f"\n[SETUP] Successfully created REST Lot ID: {lot_id}")
        return lot_id, token
    else:
        return None, None

def get_lot_status(lot_id, headers):
    response = measure_request(
        'GetAuctions', 
        f'{SERVER_URL}/auctions/', 
        method='GET', 
        headers=headers,
        status_code_expected=200,
        is_bid_status=True 
    )
    if response and response.status_code == 200:
        data = response.json()
        for lot in data:
            if lot.get('id') == lot_id:
                status = 'active'
                max_bid = lot.get('startingPrice', 100.00)
                if lot.get('bids'):
                    max_bid = lot['bids'][0]['amount']
                return status, max_bid 
    return None, None


def scenario_auth_read_heavy(user_id, duration):
    username = f"{BASE_USERNAME}{user_id}"
    password = "password123"
    
    token = register_or_login(username, password)
    if not token: return
        
    headers = {'Authorization': f'Bearer {token}'}
    end_time_test = time.time() + duration
    
    while time.time() < end_time_test:
        measure_request(
            'ListAuctions', 
            f'{SERVER_URL}/auctions/', 
            method='GET',
            headers=headers,
            status_code_expected=200
        )
        
        time.sleep(random.uniform(0.1, 0.5)) 

def scenario_write_heavy(user_id, lot_id_to_bid_on, duration):
    global BID_ATTEMPTS, BID_SUCCESS
    username = f"{BASE_USERNAME}{user_id}"
    password = "password123"
    
    token = register_or_login(username, password)
    if not token: return
        
    headers = {'Authorization': f'Bearer {token}'}
    end_time_test = time.time() + duration
    current_max_bid = 100.00
    
    while time.time() < end_time_test:
        
        status, max_bid = get_lot_status(lot_id_to_bid_on, headers)
        
        if max_bid is not None:
            current_max_bid = max(current_max_bid, max_bid)
            
        if status != 'active':
            break 
            
        new_bid = current_max_bid + random.uniform(0.01, 0.50)
        
        with LOCK: BID_ATTEMPTS += 1
        
        bid_data = {
            "lotId": lot_id_to_bid_on,
            "amount": new_bid
        }
        
        response = measure_request(
            'PlaceBid',
            f'{SERVER_URL}/bids/',
            method='POST',
            data=bid_data,
            headers=headers,
            status_code_expected=200 
        )
        
        if response and response.status_code == 200:
            with LOCK: BID_SUCCESS += 1
            current_max_bid = new_bid 
        
        time.sleep(random.uniform(0.05, 0.2)) 


def print_and_save_results(data_by_method, total_requests_recorded):
    
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rest_load_test_summary_{current_datetime}.txt"
    
    output_buffer = []

    def buffer_print(text=""):
        output_buffer.append(text)
        print(text)

    buffer_print("\n" + "="*50)
    buffer_print("REST API Performance Summary (ms)") 
    buffer_print("="*50 + "\n")
    buffer_print(f"Total Requests Recorded: {total_requests_recorded}")
    buffer_print(f"Test Duration (max): {max(DURATION_A, DURATION_B)} seconds")
    buffer_print(f"File Saved: {filename}\n")

    header = f"{'Method':<20} {'Count':<8} {'Avg (ms)':<10} {'Med (ms)':<10} {'P95 (ms)':<10} {'StdDev':<8}"
    separator = "-" * 70
    buffer_print(header)
    buffer_print(separator) 

    method_order = ['CreateLot (Setup)', 'Register', 'Login (Fallback)', 'GetAuctions', 'GetLotStatus', 'PlaceBid']
    
    for method in method_order:
        durations = data_by_method.get(method)
        if not durations: continue
        
        durations.sort()
        count = len(durations)
        
        avg = mean(durations)
        med = durations[count // 2]
        p95 = durations[int(count * 0.95)]
        
        try:
            std_dev = stdev(durations)
        except:
            std_dev = 0 

        line = f"{method:<20} {count:<8} {avg:.2f} {med:.2f} {p95:.2f} {std_dev:.2f}"
        buffer_print(line)
    
    buffer_print("\n" + "="*50)
    buffer_print("Raw Bid Metrics")
    buffer_print("="*50)
    buffer_print(f"{'Metric':<40} {'Value':<10}")
    buffer_print("-" * 50)
    buffer_print(f"{'Successful Bid Requests (Status OK)':<40} {BID_SUCCESS:<10}")
    buffer_print(f"{'Total Bid Attempts':<40} {BID_ATTEMPTS:<10}")

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_buffer))
        print(f"\n[INFO] Results successfully saved to: {filename}")
    except Exception as e:
        print(f"\n[ERROR] Failed to save results to file: {e}")


def main_load_test():
    
    print(f"\n[SETUP] Initializing REST Load Test...")
    lot_id_to_bid, creator_token = create_active_test_lot()
    
    if not lot_id_to_bid:
        print("[CRITICAL ERROR] Failed to create test lot. Ensure server is running on http://127.0.0.1:5000.")
        return

    threads = []
    
    print(f"\n[START] Starting Consolidated Load Test ({NUMBER_OF_TOTAL_USERS} VUs) ")
    
    for i in range(1, USERS_A + 1):
        thread = threading.Thread(target=scenario_auth_read_heavy, args=(i, DURATION_A))
        threads.append(thread)
        thread.start()
        
    for i in range(USERS_A + 1, NUMBER_OF_TOTAL_USERS + 1):
        thread = threading.Thread(target=scenario_write_heavy, args=(i, lot_id_to_bid, DURATION_B))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\nTest Finished. Calculating Results ")
    
    if creator_token:
        headers = {'Authorization': f'Bearer {creator_token}'}
        measure_request(
            'DeleteLot (Cleanup)',
            f'{SERVER_URL}/auctions/{lot_id_to_bid}/',
            method='DELETE',
            headers=headers,
            status_code_expected=200
        )
    
    if not ALL_RESPONSE_TIMES:
        print("No requests recorded.")
        return

    data_by_method = {}
    total_requests_recorded = 0
    
    for method, duration in ALL_RESPONSE_TIMES:
        if '(Error)' not in method and '(Cleanup)' not in method:
            if method not in data_by_method:
                data_by_method[method] = []
            data_by_method[method].append(duration)
            total_requests_recorded += 1

    print_and_save_results(data_by_method, total_requests_recorded)


if __name__ == "__main__":
    main_load_test()