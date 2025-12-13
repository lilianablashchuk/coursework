# -*- coding: utf-8 -*-
import asyncio
import aiosqlite 
import grpc.aio as grpc_aio 
import grpc
import time
import os
import sys
from datetime import datetime, timedelta, timezone
import psutil
from passlib.hash import bcrypt
import threading
from statistics import mean
import auction_pb2
import auction_pb2_grpc
from server_data import lots as initial_lots 

RESPONSE_LOG = "response_log.txt"
PERF_LOG = "performance_log.txt"
ACTIONS_LOG = "actions_log.txt"
DB_FILE = "auction_grpc.db" 

for f in [RESPONSE_LOG, PERF_LOG, ACTIONS_LOG]:
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as file:
            if f == RESPONSE_LOG:
                file.write("gRPC Response Log\n")
            elif f == PERF_LOG:
                file.write("Time,CPU(%),RAM(MB)\n")
            else:
                file.write("gRPC Actions Log\n")


ACTIVE_VIEWERS = {}
ACTIVE_VIEWERS_LOCK = threading.Lock() 
DB_CONNECTION = None


def get_formatted_time():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z').split('.')[0] + "Z"

async def get_db_connection():
    global DB_CONNECTION
    if DB_CONNECTION is None:
        DB_CONNECTION = await aiosqlite.connect(DB_FILE)
        DB_CONNECTION.row_factory = aiosqlite.Row 
    return DB_CONNECTION

async def log_action(message: str):
    timestamp = get_formatted_time()
    line = f"[{timestamp}] {message}"
    print(line)
    await asyncio.to_thread(lambda: open(ACTIONS_LOG, "a", encoding="utf-8").write(line + "\n"))

async def log_response(method_name: str, duration_ms: float):
    timestamp = get_formatted_time()
    line = f"[{timestamp}] {method_name} - {duration_ms:.2f} ms"
    print(line)
    await asyncio.to_thread(lambda: open(RESPONSE_LOG, "a", encoding="utf-8").write(line + "\n"))


async def setup_db_tables():
    conn = await get_db_connection()
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS lots (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        creator TEXT,
        createdAt TEXT,
        startingPrice REAL NOT NULL,
        startTime TEXT,
        durationMinutes INTEGER
    )
    """)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lotId INTEGER,
        user TEXT,
        amount REAL,
        createdAt TEXT DEFAULT '',
        FOREIGN KEY (lotId) REFERENCES lots(id) ON DELETE CASCADE
    )
    """)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        createdAt TEXT DEFAULT ''
    )
    """)
    await conn.commit()
    await log_action("DB tables initialized.")

async def setup_initial_data():
    conn = await get_db_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT COUNT(*) AS count FROM lots")
        count = (await cursor.fetchone())['count']
        
        if count == 0:
            await log_action("Таблиця lots порожня. Заповнюємо початковими даними...")
            sql = """
                INSERT INTO lots
                (id, title, startingPrice, description, creator, createdAt, startTime, durationMinutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            try:
                data = [(
                    lot['id'], lot['title'], lot['startingPrice'], lot['description'],
                    lot['creator'], lot['createdAt'], lot['startTime'], lot['durationMinutes']
                ) for lot in initial_lots]
                
                await cursor.executemany(sql, data)
                await conn.commit()
                await log_action(f"Успішно додано {len(initial_lots)} початкових лотів.")
            except Exception as e:
                await conn.rollback()
                await log_action(f"Помилка при заповненні БД початковими даними: {e}")


async def monitor_perf():
    while True:
        try:
            process = psutil.Process(os.getpid())
            cpu = await asyncio.to_thread(psutil.cpu_percent, interval=None)
            ram = await asyncio.to_thread(lambda: process.memory_info().rss / 1024 / 1024)
            timestamp = get_formatted_time()
            line = f"{timestamp},{cpu:.1f},{ram:.1f}"
            
            await asyncio.to_thread(lambda: open(PERF_LOG, "a", encoding="utf-8").write(line + "\n"))
            print(f"[PERF] CPU={cpu:.1f}% RAM={ram:.1f}MB")
            
        except Exception as e:
            print(f"[PERF ERROR] {e}")
            
        await asyncio.sleep(5)


class AuctionService(auction_pb2_grpc.AuctionServiceServicer):
    
    def _check_auction_time(self, start_time_str, duration_minutes):
        """Синхронна перевірка статусу аукціону."""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            duration = timedelta(minutes=duration_minutes)
            end_time = start_time + duration
            current_time = datetime.now(timezone.utc)

            if current_time < start_time:
                return "not_started"
            elif current_time > end_time:
                return "ended"
            else:
                return "active"
        except ValueError:
            return "error"

    async def JoinAuction(self, request, context):
        start = time.perf_counter()
        lot_id = request.lotId
        user = request.username
        
        with ACTIVE_VIEWERS_LOCK:
            if lot_id not in ACTIVE_VIEWERS:
                ACTIVE_VIEWERS[lot_id] = set()
            ACTIVE_VIEWERS[lot_id].add(user)

        asyncio.create_task(log_action(f"VIEWER JOINED: Lot ID={lot_id}, User='{user}'. Total: {len(ACTIVE_VIEWERS[lot_id])}"))
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("JoinAuction", duration_ms))
        return auction_pb2.Empty()

    async def LeaveAuction(self, request, context):
        start = time.perf_counter()
        lot_id = request.lotId
        user = request.username

        with ACTIVE_VIEWERS_LOCK:
            if lot_id in ACTIVE_VIEWERS:
                try:
                    ACTIVE_VIEWERS[lot_id].remove(user)
                    remaining = len(ACTIVE_VIEWERS.get(lot_id, []))
                    if not ACTIVE_VIEWERS[lot_id]:
                        del ACTIVE_VIEWERS[lot_id]
                    asyncio.create_task(log_action(f"VIEWER LEFT: Lot ID={lot_id}, User='{user}'. Remaining: {remaining}"))
                except KeyError:
                    pass

        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("LeaveAuction", duration_ms))
        return auction_pb2.Empty()

    async def GetAuctions(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()
        lots_map = {}
        
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT 
                    l.id, l.title, l.description, l.creator, l.createdAt,
                    l.startingPrice, l.startTime, l.durationMinutes,
                    b.user, b.amount, b.createdAt
                FROM lots l
                LEFT JOIN bids b ON l.id = b.lotId
                ORDER BY l.id ASC, b.amount DESC
            """)
            rows = await cursor.fetchall()
        
        with ACTIVE_VIEWERS_LOCK:
            viewers_data = {lot_id: len(users) for lot_id, users in ACTIVE_VIEWERS.items()}
            
        for row in rows:
            lot_id = row['id']
            if lot_id not in lots_map:
                users_present_count = viewers_data.get(lot_id, 0)
                auction_status = self._check_auction_time(row['startTime'], row['durationMinutes'])
                
                lots_map[lot_id] = auction_pb2.AuctionLot(
                    id=lot_id, title=row['title'], description=row['description'],
                    creator=row['creator'], createdAt=row['createdAt'], startingPrice=row['startingPrice'],
                    startTime=row['startTime'], durationMinutes=row['durationMinutes'],
                    usersPresent=users_present_count, status=auction_status, bids=[]
                )
            
            if row['user']:
                lots_map[lot_id].bids.append(auction_pb2.Bid(user=row['user'], amount=row['amount'], time=row['createdAt']))
        
        response = auction_pb2.AuctionLots(lots=list(lots_map.values()))
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("GetAuctions", duration_ms))
        return response

    async def CreateLot(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()

        if not request.title or not request.creator or request.startingPrice <= 0:
            context.set_details("Missing or invalid lot details.")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return auction_pb2.AuctionLot()

        created_at = get_formatted_time()
        
        async with conn.cursor() as cursor:
            sql = """
                INSERT INTO lots(title, description, creator, createdAt, startingPrice, startTime, durationMinutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await cursor.execute(sql, (
                request.title, request.description, request.creator, created_at,
                request.startingPrice, request.startTime, request.durationMinutes
            ))
            await conn.commit()
            lot_id = cursor.lastrowid
        
        asyncio.create_task(log_action(f"LOT CREATED: ID={lot_id}, Title='{request.title}'"))
        
        response = auction_pb2.AuctionLot(
            id=lot_id, title=request.title, description=request.description, creator=request.creator,
            createdAt=created_at, startingPrice=request.startingPrice, startTime=request.startTime, 
            durationMinutes=request.durationMinutes, usersPresent=0, status="not_started", bids=[]
        )
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("CreateLot", duration_ms))
        return response

    async def PlaceBid(self, request, context):
        start = time.perf_counter()
        bid_time = get_formatted_time()
        conn = await get_db_connection()


        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT 
                    l.id, l.title, l.description, l.creator, l.createdAt, l.startingPrice, l.startTime, l.durationMinutes,
                    MAX(b.amount) as maxBid
                FROM lots l
                LEFT JOIN bids b ON l.id = b.lotId
                WHERE l.id = ?
                GROUP BY l.id
            """, (request.lotId,))
            
            lot_info = await cursor.fetchone()
            
            if not lot_info:
                context.set_details("Lot not found.")
                context.set_code(grpc_aio.StatusCode.NOT_FOUND)
                return auction_pb2.AuctionLot()

            lot_id, title, desc, creator, created_at, starting_price, start_time, duration_min, max_bid = lot_info
            max_bid = max_bid if max_bid is not None else starting_price
            auction_status = self._check_auction_time(start_time, duration_min)

            if auction_status != "active":
                context.set_details(f"Auction is {auction_status}.")
                context.set_code(grpc_aio.StatusCode.FAILED_PRECONDITION)
                return auction_pb2.AuctionLot()
            
            if request.amount <= max_bid:
                context.set_details(f"Bid amount {request.amount:.2f} must be higher than current max bid {max_bid:.2f}.")
                context.set_code(grpc_aio.StatusCode.INVALID_ARGUMENT)
                return auction_pb2.AuctionLot()

            try:
                await cursor.execute("INSERT INTO bids(lotId, user, amount, createdAt) VALUES(?, ?, ?, ?)",
                                     (request.lotId, request.user, request.amount, bid_time))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                context.set_details(f"Database error during bid placement: {e}")
                context.set_code(grpc_aio.StatusCode.INTERNAL)
                return auction_pb2.AuctionLot()

        asyncio.create_task(log_action(f"BID PLACED: Lot ID={request.lotId}, User='{request.user}', Amount={request.amount:.2f}"))

        with ACTIVE_VIEWERS_LOCK:
            users_present_count = len(ACTIVE_VIEWERS.get(lot_id, []))

        response = auction_pb2.AuctionLot(
            id=lot_id, title=title, description=desc, creator=creator, createdAt=created_at, 
            startingPrice=starting_price, startTime=start_time, durationMinutes=duration_min, 
            usersPresent=users_present_count, status="active", bids=[auction_pb2.Bid(user=request.user, amount=request.amount, time=bid_time)]
        )
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("PlaceBid", duration_ms))
        return response

    async def DeleteLot(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()
        lot_id = request.lotId
        current_username = request.deleterUsername


        async with conn.cursor() as cursor:
            await cursor.execute("SELECT creator FROM lots WHERE id = ?", [lot_id])
            lot = await cursor.fetchone()
            
            if not lot:
                context.set_details("Lot not found.")
                context.set_code(grpc_aio.StatusCode.NOT_FOUND)
                return auction_pb2.DeleteLotResponse()

            if lot['creator'] != current_username:
                context.set_details("Forbidden: Only the creator can delete the lot.")
                context.set_code(grpc_aio.StatusCode.PERMISSION_DENIED)
                return auction_pb2.DeleteLotResponse()

            try:
                await cursor.execute("DELETE FROM bids WHERE lotId = ?", [lot_id])
                await cursor.execute("DELETE FROM lots WHERE id = ?", [lot_id])
                await conn.commit()

                with ACTIVE_VIEWERS_LOCK:
                    if lot_id in ACTIVE_VIEWERS:
                        del ACTIVE_VIEWERS[lot_id]

                asyncio.create_task(log_action(f"LOT DELETED: ID={lot_id}, Deleter='{current_username}'"))
                response = auction_pb2.DeleteLotResponse(status="ok", message=f"Lot {lot_id} and its bids deleted successfully.")
            except Exception as e:
                await conn.rollback()
                context.set_details(f"Database error during lot deletion: {e}")
                context.set_code(grpc_aio.StatusCode.INTERNAL)
                response = auction_pb2.DeleteLotResponse()

        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("DeleteLot", duration_ms))
        return response

    async def GetWinningsByUser(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()
        username = request.username
        winnings = []

        async with conn.cursor() as cursor:
            sql = """
                SELECT
                    l.id, l.title, l.startTime, l.durationMinutes, MAX(b.amount) AS winningAmount, b.user AS winner
                FROM lots l
                LEFT JOIN bids b ON l.id = b.lotId
                GROUP BY l.id
                HAVING winner = ?
            """
            await cursor.execute(sql, (username,))
            candidate_winnings = await cursor.fetchall()
            
            for row in candidate_winnings:
                auction_status = self._check_auction_time(row['startTime'], row['durationMinutes'])
                
                if auction_status == "ended":
                    winnings.append(auction_pb2.WinningLotInfo(
                        lotId=row['id'], lotTitle=row['title'], winningAmount=row['winningAmount']
                    ))

        response = auction_pb2.WinningsList(winnings=winnings)
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("GetWinningsByUser", duration_ms))
        return response
    
    async def GetBidsByUser(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()
        username = request.username
        user_bids = []

        sql = """
            SELECT
                b.lotId, b.amount, b.createdAt, l.title as lotTitle
            FROM bids b
            JOIN lots l ON b.lotId = l.id
            WHERE b.user = ?
            ORDER BY b.id DESC
        """

        async with conn.cursor() as cursor:
            await cursor.execute(sql, (username,))
            rows = await cursor.fetchall()

        for row in rows:
            user_bids.append(auction_pb2.UserBidInfo(
                lotId=row['lotId'], lotTitle=row['lotTitle'], amount=row['amount'], time=row['createdAt']
            ))
        
        response = auction_pb2.BidsList(bids=user_bids)
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("GetBidsByUser", duration_ms))
        return response

    async def GetLotStatus(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()
        lot_id = request.lotId

        async with conn.cursor() as cursor:
            sql = """
                SELECT l.title, l.createdAt, l.startTime, l.durationMinutes, MAX(b.amount) AS winningAmount, b.user AS winner, l.startingPrice
                FROM lots l
                LEFT JOIN bids b ON l.id = b.lotId
                WHERE l.id = ?
                GROUP BY l.id
            """
            await cursor.execute(sql, [lot_id])
            result = await cursor.fetchone()

        if not result:
            context.set_details("Lot not found.")
            context.set_code(grpc_aio.StatusCode.NOT_FOUND)
            return auction_pb2.LotStatusResponse()

        (title, created_at, start_time_str, duration_minutes, winning_amount, winner, starting_price) = result
        final_price = winning_amount if winning_amount is not None else starting_price
        auction_status = self._check_auction_time(start_time_str, duration_minutes)
        
        if auction_status == "active" or auction_status == "not_started":
            status = "active" if auction_status == "active" else "not_started"
            message = "Auction is currently active." if auction_status == "active" else "Auction has not started yet."
            response = auction_pb2.LotStatusResponse(
                status=status, message=message, lotTitle=title, finalPrice=final_price, 
                winner=winner if winner else "", createdAt=created_at
            )
        else: 
            if winning_amount is None:
                response = auction_pb2.LotStatusResponse(
                    status="ended_no_bids", message="Auction ended without bids.", lotTitle=title, 
                    finalPrice=starting_price, winner="", createdAt=created_at
                )
            else:
                response = auction_pb2.LotStatusResponse(
                    status="ended_with_winner", message=f"Auction ended! Winner: {winner}", lotTitle=title, 
                    finalPrice=final_price, winner=winner, createdAt=created_at
                )

        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("GetLotStatus", duration_ms))
        return response

    async def Register(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()        
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE username=?", (request.username,))
            if await cursor.fetchone():
                context.set_details("User already exists")
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                return auction_pb2.AuthResponse()
            
            hashed = await asyncio.to_thread(bcrypt.hash, request.password)
            created_at = get_formatted_time()
            
            await cursor.execute("INSERT INTO users(username,password,createdAt) VALUES(?,?,?)", (request.username, hashed, created_at))
            await conn.commit()
            user_id = cursor.lastrowid

        asyncio.create_task(log_action(f"REGISTER success: {request.username}"))
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("Register", duration_ms))
        return auction_pb2.AuthResponse(status="ok", message="Registration successful", userId=str(user_id))

    async def Login(self, request, context):
        start = time.perf_counter()
        conn = await get_db_connection()        
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id, password FROM users WHERE username=?", (request.username,))
            row = await cursor.fetchone()

        if not row:
            asyncio.create_task(log_action(f"LOGIN failed (user not found): {request.username}"))
            context.set_details("Invalid credentials")
            context.set_code(grpc_aio.StatusCode.UNAUTHENTICATED)
            return auction_pb2.AuthResponse()
            
        user_id, hashed_password = row['id'], row['password']
        
        verified = await asyncio.to_thread(bcrypt.verify, request.password, hashed_password)

        if not verified:
            asyncio.create_task(log_action(f"LOGIN failed (password mismatch): {request.username}"))
            context.set_details("Invalid credentials")
            context.set_code(grpc_aio.StatusCode.UNAUTHENTICATED)
            return auction_pb2.AuthResponse()
        
        asyncio.create_task(log_action(f"LOGIN success: {request.username}"))
        duration_ms = (time.perf_counter() - start) * 1000
        asyncio.create_task(log_response("Login", duration_ms))
        return auction_pb2.AuthResponse(status="ok", message="Login successful", userId=str(user_id))



async def serve():    
    await setup_db_tables()
    await setup_initial_data()
    
    server = grpc_aio.server() 
    auction_pb2_grpc.add_AuctionServiceServicer_to_server(AuctionService(), server)
    server.add_insecure_port('0.0.0.0:50051')
    
    asyncio.create_task(monitor_perf())

    print("gRPC server running on port 50051")
    await server.start()
    
    await server.wait_for_termination()

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nServer stopped manually.")
       
        os._exit(0)