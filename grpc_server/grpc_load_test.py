# -*- coding: utf-8 -*-

import grpc.aio as grpc_aio 
import asyncio
import time
import random
import sys
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
import grpc 

import auction_pb2
import auction_pb2_grpc

SERVER_ADDRESS = '127.0.0.1:50051'
CHANNEL_OPTIONS = [('grpc.max_receive_message_length', 1024 * 1024 * 5)]

NUMBER_OF_TOTAL_USERS = 50 
DURATION_OF_TEST_SECONDS = 60 
BASE_USERNAME = "load_user_"
TEST_LOT_DURATION_MINUTES = 5 

ALL_RESPONSE_TIMES = []
BID_ATTEMPTS = 0
BID_SUCCESS = 0
LOCK = asyncio.Lock() 

def get_formatted_time(offset_seconds=0):
    dt = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return dt.isoformat().replace('+00:00', 'Z').split('.')[0] + "Z"


async def create_active_test_lot(stub): 
    start_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    start_time_str = start_time.isoformat().replace('+00:00', 'Z').split('.')[0] + "Z"

    lot_request = auction_pb2.CreateLotRequest(
        title=f"Stress Test Lot {int(time.time())}",
        description=f"Lot for {NUMBER_OF_TOTAL_USERS} users betting for {DURATION_OF_TEST_SECONDS}s.",
        creator="LoadTestCreator",
        startingPrice=100.00,
        startTime=start_time_str,
        durationMinutes=TEST_LOT_DURATION_MINUTES,
    )
    
    try:
        start = time.perf_counter()
        response = await stub.CreateLot(lot_request) 
        duration = (time.perf_counter() - start) * 1000
        async with LOCK: ALL_RESPONSE_TIMES.append(('CreateLot (Setup)', duration))
        
        print(f"\n[SETUP] Successfully created Lot ID: {response.id}")
        return response.id
    except grpc_aio.AioRpcError as e:
        print(f"[SETUP ERROR] Failed to create lot: {e.details()}")
        async with LOCK: ALL_RESPONSE_TIMES.append(('CreateLot (Setup Error)', 9999))
        return None

async def setup_users(stub, count):
    print(f"\n[SETUP] Starting registration of {count} users...")
    
    registration_tasks = []
    for i in range(1, count + 1):
        username = f"{BASE_USERNAME}{i}"
        password = "password123"
        registration_tasks.append(register_user_async(stub, username, password))
    
    results = await asyncio.gather(*registration_tasks)
    success_count = sum(results)
    
    print(f"[SETUP] Finished user setup. {success_count} users ready.")
    return success_count == count

async def register_user_async(stub, username, password):
    start = time.perf_counter()
    try:
        await stub.Register(auction_pb2.AuthRequest(username=username, password=password))
        duration = (time.perf_counter() - start) * 1000
        async with LOCK: ALL_RESPONSE_TIMES.append(('Register (Setup)', duration))
        return 1
        
    except grpc_aio.AioRpcError as e:
        duration = (time.perf_counter() - start) * 1000
        
        if e.code() == grpc.StatusCode.ALREADY_EXISTS: 
            async with LOCK: ALL_RESPONSE_TIMES.append(('Register (Setup, Exists)', duration))
            return 1 
        else:
            print(f"[AUTH ERROR] Failed to register {username}: {e.details()}")
            return 0 
    except Exception as e:
        print(f"[AUTH ERROR] Unexpected error during registration of {username}: {e}")
        return 0



async def scenario_write_heavy(user_id, lot_id_to_bid_on, duration): 
    global BID_ATTEMPTS, BID_SUCCESS
    username = f"{BASE_USERNAME}{user_id}"
    password = "password123"
    
    async with grpc_aio.insecure_channel(SERVER_ADDRESS, options=CHANNEL_OPTIONS) as channel:
        stub = auction_pb2_grpc.AuctionServiceStub(channel)
    
        start_login = time.perf_counter()
        try:
            await stub.Login(auction_pb2.AuthRequest(username=username, password=password))
            duration_login = (time.perf_counter() - start_login) * 1000
            async with LOCK: ALL_RESPONSE_TIMES.append(('Login', duration_login))
        except grpc_aio.AioRpcError as e:
            print(f"[AUTH FAILED] User {username} login failed: {e.details()}")
            return 

        current_max_bid = 100.00
        end_time_test = time.time() + duration
        
        while time.time() < end_time_test:
            
            try:
                start_read = time.perf_counter()
                response = await stub.GetAuctions(auction_pb2.Empty()) 
                duration_read_ms = (time.perf_counter() - start_read) * 1000
                
                async with LOCK: ALL_RESPONSE_TIMES.append(('GetAuctions', duration_read_ms))
                
                found_lot = next((lot for lot in response.lots if lot.id == lot_id_to_bid_on), None)
                
                if not found_lot or found_lot.status != "active": 
                     break 
                     
                if found_lot.bids:
                    current_max_bid = max(current_max_bid, found_lot.bids[0].amount)

            except grpc_aio.AioRpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                     pass
                await asyncio.sleep(random.uniform(0.5, 1.0))
                continue

            new_bid = current_max_bid + random.uniform(0.01, 0.50)
            
            async with LOCK: BID_ATTEMPTS += 1
            
            start_write = time.perf_counter()

            try:
                await stub.PlaceBid(auction_pb2.PlaceBidRequest(
                    lotId=lot_id_to_bid_on,
                    user=username,
                    amount=new_bid
                ))
                duration_write_ms = (time.perf_counter() - start_write) * 1000
                
                async with LOCK:
                    ALL_RESPONSE_TIMES.append(('PlaceBid', duration_write_ms))
                    BID_SUCCESS += 1
                
            except grpc_aio.AioRpcError as e:
                duration_write_ms = (time.perf_counter() - start_write) * 1000
                if e.code() == grpc.StatusCode.INVALID_ARGUMENT or e.code() == grpc.StatusCode.FAILED_PRECONDITION:
                    pass 
                elif e.code() == grpc.StatusCode.UNAVAILABLE:
                     pass
                else:
                     pass
                pass 

            await asyncio.sleep(random.uniform(0.05, 0.2))


async def main_load_test_async(): 
    async with grpc_aio.insecure_channel(SERVER_ADDRESS, options=CHANNEL_OPTIONS) as channel:
        stub_setup = auction_pb2_grpc.AuctionServiceStub(channel)

        lot_id_to_bid = await create_active_test_lot(stub_setup)
        if not lot_id_to_bid:
            print("Setup failed. Exiting.")
            return
        
        if not await setup_users(stub_setup, NUMBER_OF_TOTAL_USERS):
            print("User setup failed. Exiting.")
            return

    print(f"\n[START] Starting UNIFIED ASYNC Load Test ({NUMBER_OF_TOTAL_USERS} VUs) against {SERVER_ADDRESS}")
    
    load_tasks = [asyncio.create_task(scenario_write_heavy(i, lot_id_to_bid, DURATION_OF_TEST_SECONDS))
                  for i in range(1, NUMBER_OF_TOTAL_USERS + 1)]
        
    await asyncio.gather(*load_tasks) 

    print("\nTest Finished. Calculating Results ")

    if not ALL_RESPONSE_TIMES:
        print("No requests recorded.")
        return

    data_by_method = {}
    total_requests_recorded = 0
    
    for method, duration in ALL_RESPONSE_TIMES:
        if '(Error)' not in method and 'Setup, Exists' not in method:
            if method not in data_by_method:
                data_by_method[method] = []
            data_by_method[method].append(duration)
            total_requests_recorded += 1

    print("\n" + "="*70)
    print("gRPC Performance Summary (ms) - Heavy Write Load")
    print("="*70 + "\n")
    print(f"Total Requests Recorded (R+W): {total_requests_recorded}")
    print(f"Virtual Users (VUs): {NUMBER_OF_TOTAL_USERS}")
    print(f"Test Duration: {DURATION_OF_TEST_SECONDS} seconds\n")

    print(f"{'Method':<20} {'Count':<10} {'Avg (ms)':<10} {'Med (ms)':<10} {'P95 (ms)':<10} {'StdDev':<10}")
    print("-" * 70)

    method_order = ['CreateLot (Setup)', 'Register (Setup)', 'Login', 'GetAuctions', 'PlaceBid']
    
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

        print(f"{method:<20} {count:<10} {avg:.2f} {med:.2f} {p95:.2f} {std_dev:.2f}")
    
    print("\n" + "="*70)
    print("Raw Bid Metrics")
    print("="*70)
    print(f"{'Successful Bid Requests (Status OK)':<40} {BID_SUCCESS:<10}")
    print(f"{'Total Bid Attempts':<40} {BID_ATTEMPTS:<10}")
    
    if BID_ATTEMPTS > 0:
        success_rate = (BID_SUCCESS / BID_ATTEMPTS) * 100
        print(f"{'Bid Success Rate':<40} {success_rate:.2f}%")


if __name__ == "__main__":
    try:
        asyncio.run(main_load_test_async())
    except KeyboardInterrupt:
        print("\nTest stopped manually.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Test failed unexpectedly: {e}")