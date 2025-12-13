# -*- coding: utf-8 -*-
import grpc
import time
import sys
from datetime import datetime, timedelta, timezone

import auction_pb2
import auction_pb2_grpc

FIXED_WINDOWS_HOST_IP = "172.26.48.1"
SERVER_ADDRESS = f"{FIXED_WINDOWS_HOST_IP}:50051"

def time_op(stub, method_name, request):
    start_time = time.perf_counter()
    status_code = "OK"
    
    try:
        if method_name == 'Register':
            response = stub.Register(request)
        elif method_name == 'Login':
            response = stub.Login(request)
        elif method_name == 'GetAuctions':
            response = stub.GetAuctions(request)
        elif method_name == 'PlaceBid':
            response = stub.PlaceBid(request)
        elif method_name == 'CreateLot':
            response = stub.CreateLot(request)
        else:
            raise ValueError("Unknown gRPC method")
        
        if hasattr(response, 'status') and response.status != "ok":
             status_code = f"FAIL_{response.status}"
             
    except grpc.RpcError as e:
        status_code = f"ERROR_{e.code().name}"
        
    except Exception as e:
        status_code = f"EXCEPTION_{type(e).__name__}"

    latency_ms = (time.perf_counter() - start_time) * 1000
    
    print(f"GRPC_{method_name}_Latency: {latency_ms:.3f}ms")
    print(f"GRPC_{method_name}_Status: {status_code}")
    
    return status_code == "OK"

def get_current_iso_time(offset_minutes=5):
    dt_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return dt_utc.isoformat().replace('+00:00', 'Z').split('.')[0] + "Z"

def run_grpc_benchmarks(username, password, lot_id_to_bid):

    channel = grpc.insecure_channel(SERVER_ADDRESS)
    stub = auction_pb2_grpc.AuctionServiceStub(channel)
    
    time_op(stub, 'Register', auction_pb2.AuthRequest(username=username, password=password))

    time_op(stub, 'Login', auction_pb2.AuthRequest(username=username, password=password))
    
    time_op(stub, 'GetAuctions', auction_pb2.Empty())
    
    start_time_past = get_current_iso_time(offset_minutes=-1) 
    
    time_op(stub, 'CreateLot', auction_pb2.CreateLotRequest(
        title=f"Bench Lot {username}",
        description="Benchmark test lot.",
        creator=username,
        startingPrice=100.00,
        startTime=start_time_past,
        durationMinutes=5
    ))

    time_op(stub, 'PlaceBid', auction_pb2.PlaceBidRequest(
        lotId=lot_id_to_bid, 
        user=username, 
        amount=1000.00 + (hash(username) % 100) / 100.0
    ))
    
    channel.close()
    
if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python grpc_benchmark_core.py <username> <password> <lot_id_to_bid>")
        sys.exit(1)
        
    user = sys.argv[1]
    passwd = sys.argv[2]
    lot = int(sys.argv[3])
    
    run_grpc_benchmarks(user, passwd, lot)
