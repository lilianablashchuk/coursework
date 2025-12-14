import os
import time
import json
import sqlite3
import logging
import contextlib 
from datetime import datetime, timedelta, timezone 
from functools import wraps
import jwt
import threading
import psutil
import collections 
from dotenv import load_dotenv

from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_talisman import Talisman 
import bcrypt


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PORT = 5000 
DB_NAME = 'auction.db'
RESPONSE_LOG = "response_log.txt"
PERF_CSV = "performance_log.txt"
AUTH_LOG = "auth_log.txt"

load_dotenv()
JWT_SECRET = os.getenv('JWT_SECRET', 'PLEASE_SET_THE_SECRET_KEY_IN_DOTENV_FILE')
SALT_ROUNDS = 10
ACCESS_TOKEN_EXPIRY_HOURS = 1
ACTIVE_VIEWERS = collections.defaultdict(set) 



def get_formatted_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log_to_file(filepath, content):
    try:
        with open(filepath, 'a') as f:
            f.write(content + '\n')
    except IOError as e:
        logging.error(f"Failed to write to log file {filepath}: {e}")


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        try:
            g.db.execute("PRAGMA journal_mode = WAL;") 
            g.db.execute("PRAGMA busy_timeout = 10000;") 
            logging.info("[DB INIT] SQLite PRAGMA configured.")
        except sqlite3.Error as e:
            logging.warning(f"[DB INIT] Could not configure SQLite DB object: {e}")
            
        g.db.row_factory = sqlite3.Row 
    return g.db

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            creator TEXT NOT NULL,
            createdAt TEXT NOT NULL,
            startingPrice REAL NOT NULL,
            startTime TEXT NOT NULL,
            durationMinutes INTEGER NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lotId INTEGER NOT NULL,
            user TEXT NOT NULL,
            amount REAL NOT NULL,
            createdAt TEXT NOT NULL,
            FOREIGN KEY(lotId) REFERENCES lots(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bids_lotId_amount ON bids (lotId, amount DESC);")
    db.commit()
    logging.info("[DB INIT] Database tables initialized.")

@contextlib.contextmanager
def execute_db_transaction(db):
    try:
        db.execute("BEGIN TRANSACTION;")
        yield db
        db.execute("COMMIT;")
    except Exception as e:
        db.execute("ROLLBACK;")
        raise e

def db_run(sql, params=()):
    db = get_db()
    try:
        cursor = db.execute(sql, params)
        db.commit()
        return {'lastID': cursor.lastrowid, 'changes': cursor.rowcount}
    except sqlite3.Error as e:
        raise Exception(f"DB Run Error: {e}")

def db_get(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    row = cursor.fetchone()
    return dict(row) if row else None

def db_all(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


_perf_timer = None
_start_time = time.time()
_total_requests = 0
_total_response_time = 0

def start_perf_logging():
    global _perf_timer
    if _perf_timer is not None:
        return
    
    logging.info("[PERF] Starting CPU/RAM logging.")
    
    def log_perf():
        global _perf_timer
        try:
            process = psutil.Process(os.getpid())
            cpu = process.cpu_percent(interval=0.1) 
            ram_mb = process.memory_info().rss / (1024 * 1024)
            
            log_csv = f"{get_formatted_time()},{cpu:.1f},{ram_mb:.1f}"
            log_to_file(PERF_CSV, log_csv)
            logging.info(f"[PERF LOGGED] CPU={cpu:.1f}% RAM={ram_mb:.1f}MB")
        except psutil.NoSuchProcess:
            logging.error("[PERF ERROR] Process not found for performance logging.")
            stop_perf_logging()
        except Exception as e:
            logging.error(f"[PERF ERROR] pidusage failed: {e}")
            
    def timer_function():
        global _perf_timer 
        if _perf_timer is not None:
            log_perf()
            _perf_timer = threading.Timer(5.0, timer_function)
            _perf_timer.start()

    _perf_timer = threading.Timer(5.0, timer_function)
    _perf_timer.start()

def stop_perf_logging():
    global _perf_timer
    if _perf_timer is not None:
        _perf_timer.cancel()
        _perf_timer = None
        logging.info("[PERF] Stopping CPU/RAM logging.")


app = Flask(__name__)


@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.before_request
def request_timing_middleware():
    g.start_time = time.perf_counter()

@app.after_request
def response_logging_middleware(response):
    global _total_requests, _total_response_time
    
    start_time = g.get('start_time') 
    
    if start_time is not None:
        duration = (time.perf_counter() - start_time) * 1000 
        _total_requests += 1
        _total_response_time += duration
        
        log_line = f"[{get_formatted_time()}] {request.method} {request.path} - {duration:.2f} ms - Status: {response.status_code}"
        log_to_file(RESPONSE_LOG, log_line)
        logging.info(log_line)
    
    return response

def auth_middleware(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"status": "error", "message": "Access Denied: No token provided."}), 401

        token = auth_header.split(' ')[1]

        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            g.user = decoded 
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Access Denied: Token has expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "message": "Access Denied: Invalid token."}), 401
        
        return f(*args, **kwargs)
    return decorated


@app.route('/auth/register/', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or len(username) < 3 or not password or len(password) < 6:
        return jsonify({"status": "error", "message": "Validation failed", 
                            "errors": [{"msg": "Username must be at least 3 chars long and password at least 6."}]}), 400

    try:
        existing_user = db_get("SELECT id FROM users WHERE username = ?", [username])
        if existing_user:
            return jsonify({"status": "error", "message": "User already exists"}), 400
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(SALT_ROUNDS)).decode('utf-8')
        
        result = db_run("INSERT INTO users(username, password) VALUES(?,?)", [username, hashed_password])
        last_id = result['lastID']

        log_event = f"[{get_formatted_time()}] REGISTER success: {username}"
        log_to_file(AUTH_LOG, log_event)
        logging.info(f"[AUTH] User registered: {username}")

        token = jwt.encode({'id': last_id, 'username': username}, JWT_SECRET, algorithm="HS256")

        return jsonify({"status": "ok", "userId": last_id, "token": token}), 200

    except Exception as err:
        logging.error(f"Auth error: {err}")
        return jsonify({"status": "error", "message": "Failed to register or internal error."}), 500


@app.route('/auth/login/', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or len(username) < 3 or not password or len(password) < 6:
        return jsonify({"status": "error", "message": "Validation failed", 
                            "errors": [{"msg": "Username must be at least 3 chars long and password at least 6."}]}), 400

    try:
        row = db_get("SELECT id, username, password FROM users WHERE username = ?", [username])

        if not row:
            log_event = f"[{get_formatted_time()}] LOGIN failed (user not found): {username}"
            log_to_file(AUTH_LOG, log_event)
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        match = bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8'))
        
        if match:
            log_event = f"[{get_formatted_time()}] LOGIN success: {username}"
            log_to_file(AUTH_LOG, log_event)
            logging.info(f"[AUTH] User logged in: {username}")
            
            token = jwt.encode({'id': row['id'], 'username': row['username']}, JWT_SECRET, algorithm="HS256")
            return jsonify({"status": "ok", "token": token}), 200
        else:
            log_event = f"[{get_formatted_time()}] LOGIN failed (password mismatch): {username}"
            log_to_file(AUTH_LOG, log_event)
            logging.info(f"[AUTH] Login failed for: {username}")
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    except Exception as err:
        logging.error(f"Auth error: {err}")
        return jsonify({"status": "error", "message": "Internal server error."}), 500


BASE_LOT_SELECT = "SELECT id, title, description, creator, createdAt, startingPrice, startTime, durationMinutes FROM lots"


@app.route('/auctions/', methods=['GET'])
def list_auctions():
    try:
        lots = db_all(f"{BASE_LOT_SELECT} ORDER BY id ASC")
        
        if not lots:
            return jsonify([])

        lot_ids = [lot['id'] for lot in lots]
        
    
        bids_sql = """
            SELECT lotId, user, amount, createdAt
            FROM bids
            WHERE lotId IN ({})
            ORDER BY lotId, amount DESC, createdAt DESC
        """.format(','.join('?' * len(lot_ids)))
        
        all_bids_data = db_all(bids_sql, lot_ids)
        
        bids_map = collections.defaultdict(list)
        for bid in all_bids_data:
            bids_map[bid['lotId']].append({
                'user': bid['user'],
                'amount': bid['amount'],
                'createdAt': bid['createdAt']
            })
        
        results = []
        for lot in lots:
            lot_data = dict(lot)
            lot_id = lot['id']
            
            lot_data['bids'] = bids_map[lot_id]

            lot_data['usersPresent'] = len(ACTIVE_VIEWERS.get(lot_id, set()))
            results.append(lot_data)
        
        return jsonify(results)

    except Exception as err:
        logging.error(f"DB error in /auctions (Modified): {err}")
        return jsonify({"status": "error", "message": str(err)}), 500

@app.route('/auctions/<int:id>/', methods=['GET'])
def get_auction(id):
    try:
        lot = db_get(f"{BASE_LOT_SELECT} WHERE id = ?", [id])
        if not lot:
            return jsonify({"status": "error", "message": "Lot not found."}), 404

        bids = db_all("SELECT user, amount, createdAt FROM bids WHERE lotId = ? ORDER BY amount DESC", [id])
        users_present = len(ACTIVE_VIEWERS.get(id, set()))
        
        lot_data = dict(lot)
        lot_data['bids'] = bids
        lot_data['usersPresent'] = users_present
        
        return jsonify(lot_data)

    except Exception as err:
        logging.error(f"DB error in /auctions/{id}: {err}")
        return jsonify({"status": "error", "message": str(err)}), 500

@app.route('/auctions/', methods=['POST'])
@auth_middleware
def create_auction():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    starting_price = data.get('startingPrice')
    start_time_str = data.get('startTime')
    duration_minutes = data.get('durationMinutes')
    creator = g.user['username']

    try:
        price = float(starting_price)
        duration = int(duration_minutes)
        if len(title) < 5 or price <= 0 or duration <= 0:
             raise ValueError("Validation failed.")
        datetime.fromisoformat(start_time_str.replace('Z', '+00:00')) 
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Validation failed: Check title length, startingPrice (positive float), startTime (ISO8601), and durationMinutes (positive integer)."}), 400

    try:
        created_at = get_formatted_time()
        sql = """
            INSERT INTO lots (title, description, creator, createdAt, startingPrice, startTime, durationMinutes) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        result = db_run(sql, [title, description, creator, created_at, price, start_time_str, duration])
        lot_id = result['lastID']

        log_event = f"[{get_formatted_time()}] LOT CREATED: ID={lot_id}, Title='{title}', Creator='{creator}', Start='{start_time_str}', Duration={duration} min"
        log_to_file(AUTH_LOG, log_event)
        logging.info(log_event)

        return jsonify({
            "status": "ok",
            "lot": {
                "id": lot_id, "title": title, "description": description, "creator": creator,
                "createdAt": created_at, "startingPrice": price, "startTime": start_time_str,
                "durationMinutes": duration, "bids": []
            }
        }), 201

    except Exception as err:
        logging.error(f"DB error in /auctions POST: {err}")
        return jsonify({"status": "error", "message": str(err)}), 500

@app.route('/auctions/<int:id>/', methods=['DELETE'])
@auth_middleware
def delete_auction(id):
    current_username = g.user['username']

    try:
        lot = db_get("SELECT creator FROM lots WHERE id = ?", [id])
        if not lot:
            return jsonify({"status": "error", "message": "Lot not found."}), 404
        if lot['creator'] != current_username:
            return jsonify({"status": "error", "message": "Forbidden: Only the creator can delete the lot."}), 403

        db = get_db()
        with execute_db_transaction(db) as tx:
            tx.execute("DELETE FROM bids WHERE lotId = ?", [id])
            result = tx.execute("DELETE FROM lots WHERE id = ?", [id])
            
            if result.rowcount == 0:
                 raise Exception("Lot not found or failed to delete.") 

        log_event = f"[{get_formatted_time()}] LOT DELETED: ID={id}, Deleter='{current_username}'"
        log_to_file(AUTH_LOG, log_event)
        logging.info(log_event)
        
        ACTIVE_VIEWERS.pop(id, None)

        return jsonify({"status": "ok", "message": f"Lot {id} and its bids deleted successfully."})

    except Exception as err:
        logging.error(f"DB error in /auctions DELETE: {err}")
        if "Lot not found" in str(err):
            return jsonify({"status": "error", "message": "Lot not found."}), 404
        return jsonify({"status": "error", "message": "Internal server error during transaction."}), 500


@app.route('/auctions/<int:id>/winner/', methods=['GET'])
def get_winner(id):
    try:
        sql = """
            SELECT 
                l.title, l.createdAt, l.startTime, l.durationMinutes, 
                MAX(b.amount) AS winningAmount, b.user AS winner, l.startingPrice
            FROM lots l
            LEFT JOIN bids b ON l.id = b.lotId
            WHERE l.id = ?
            GROUP BY l.id
        """
        result = db_get(sql, [id])
        
        if not result or not result.get('title'): 
            return jsonify({"status": "error", "message": "Lot not found."}), 404

        title = result['title']
        winning_amount = result['winningAmount']
        winner = result['winner']
        starting_price = result['startingPrice']
        created_at = result['createdAt']
        start_time_str = result['startTime']
        duration_minutes = result['durationMinutes']

        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = start_time + timedelta(minutes=duration_minutes)
        is_auction_ended = datetime.now(timezone.utc) > end_time 
        
        final_price = winning_amount if winning_amount else starting_price

        if is_auction_ended:
            if not winning_amount:
                return jsonify({
                    "status": "ended_no_bids", "message": "Auction ended without bids.",
                    "lotTitle": title, "finalPrice": starting_price, "winner": None, "createdAt": created_at
                })
            else:
                return jsonify({
                    "status": "ended_with_winner", "message": "Auction ended and winner determined.",
                    "lotTitle": title, "finalPrice": final_price, "winner": winner, "createdAt": created_at
                })
        
        return jsonify({
            "status": "active", "message": "Auction is currently active.",
            "lotTitle": title, "currentMaxBid": final_price, "winner": winner, "createdAt": created_at
        })

    except Exception as err:
        logging.error(f"DB error in /auctions/winner: {err}")
        return jsonify({"status": "error", "message": str(err)}), 500


def update_active_viewers(lot_id, username, action):
    lot_id_int = int(lot_id)
    if action == 'join':
        if lot_id_int not in ACTIVE_VIEWERS:
             ACTIVE_VIEWERS[lot_id_int] = set()
        ACTIVE_VIEWERS[lot_id_int].add(username)
        size = len(ACTIVE_VIEWERS[lot_id_int])
        logging.info(f"[VIEWER JOINED] Lot ID={lot_id_int}, User='{username}'. Total: {size}")
    elif action == 'leave':
        if lot_id_int in ACTIVE_VIEWERS:
            ACTIVE_VIEWERS[lot_id_int].discard(username)
            size = len(ACTIVE_VIEWERS[lot_id_int])
            if size == 0:
                del ACTIVE_VIEWERS[lot_id_int]
            logging.info(f"[VIEWER LEFT] Lot ID={lot_id_int}, User='{username}'. Remaining: {size}")
    return {"status": "ok"}

@app.route('/auctions/join/', methods=['POST'])
@auth_middleware
def join_auction():
    data = request.get_json()
    lot_id = data.get('lotId')
    user = g.user['username']
    
    try:
        return jsonify(update_active_viewers(lot_id, user, 'join'))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid lotId."}), 400

@app.route('/auctions/leave/', methods=['POST'])
@auth_middleware
def leave_auction():
    data = request.get_json()
    lot_id = data.get('lotId')
    user = g.user['username']
    
    try:
        return jsonify(update_active_viewers(lot_id, user, 'leave'))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid lotId."}), 400


@app.route('/bids/', methods=['POST'])
@auth_middleware
def place_bid():
    data = request.get_json()
    lot_id_int = data.get('lotId')
    bid_amount = data.get('amount')
    user = g.user['username']

    try:
        lot_id_int = int(lot_id_int)
        bid_amount = float(bid_amount)
        if lot_id_int <= 0 or bid_amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Missing or invalid parameters (lotId, amount must be positive numbers)."}), 400

    created_at = get_formatted_time()
    db = get_db()
    
    try:
        with execute_db_transaction(db) as tx:
            select_sql = """
                SELECT 
                    l.startingPrice, l.startTime, l.durationMinutes, 
                    MAX(b.amount) as maxBid
                FROM lots l
                LEFT JOIN bids b ON l.id = b.lotId
                WHERE l.id = ?
                GROUP BY l.id
            """
            row = tx.execute(select_sql, [lot_id_int]).fetchone()
            
            if not row:
                raise Exception("Lot not found.")
            
            row = dict(row) 
            
            start_time = datetime.fromisoformat(row['startTime'].replace('Z', '+00:00'))
            end_time = start_time + timedelta(minutes=row['durationMinutes'])
            
            current_time = datetime.now(timezone.utc)
            
            max_bid = row['maxBid'] if row['maxBid'] is not None else row['startingPrice']
            
            validation_error = None

            if current_time < start_time:
                validation_error = {"status": 400, "message": "Auction has not started yet."}
            elif current_time > end_time: 
                validation_error = {"status": 400, "message": "Auction has already ended."}
            elif bid_amount <= max_bid:
                validation_error = {"status": 400, "message": f"Bid amount {bid_amount:.2f} must be higher than current max bid {max_bid:.2f}."}
            elif user == db_get("SELECT creator FROM lots WHERE id = ?", [lot_id_int])['creator']:
                validation_error = {"status": 400, "message": "Creator cannot bid on their own lot."}


            if validation_error:
                raise Exception(f"VALIDATION_FAIL:{validation_error['message']}")

            insert_sql = "INSERT INTO bids(lotId, user, amount, createdAt) VALUES(?, ?, ?, ?)"
            tx.execute(insert_sql, [lot_id_int, user, bid_amount, created_at])
            
            
        log_event = f"[{created_at}] BID PLACED: Lot ID={lot_id_int}, User='{user}', Amount={bid_amount:.2f}"
        log_to_file(AUTH_LOG, log_event)
        logging.info(log_event)

        return jsonify({
            "status": "ok",
            "message": "Bid placed successfully.",
            "bid": {"lotId": lot_id_int, "user": user, "amount": bid_amount, "time": created_at}
        }), 200

    except Exception as err:
        logging.error(f"DB error or Validation fail in /bids POST: {err}")
        
        if str(err).startswith("VALIDATION_FAIL:"):
            msg = str(err).split("VALIDATION_FAIL:")[1]
            status_code = 400 if "Lot not found" not in msg else 404
            return jsonify({"status": "error", "message": msg}), status_code

        return jsonify({"status": "error", "message": str(err) if "Lot not found" not in str(err) else "Lot not found."}), 500


@app.route('/bids/user/<string:username>/', methods=['GET'])
def get_user_bids(username):
    try:
        sql = """
            SELECT b.lotId, l.title AS lotTitle, b.amount, b.createdAt 
            FROM bids b
            JOIN lots l ON b.lotId = l.id
            WHERE b.user = ?
            ORDER BY b.createdAt DESC
        """
        user_bids = db_all(sql, [username])
        return jsonify(user_bids)

    except Exception as err:
        logging.error(f"DB error in /bids/user: {err}")
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    uptime = time.time() - _start_time
    avg_response = _total_response_time / _total_requests if _total_requests else 0
    
    return jsonify({
        "totalRequests": _total_requests,
        "avgResponseTimeMs": f"{avg_response:.2f}",
        "uptimeSec": f"{uptime:.2f}"
    })


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"status": "error", "message": "Resource not found."}), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error caught: {error}")
    return jsonify({"status": "error", "message": "Internal server error."}), 500


with app.app_context(): 
    if not os.path.exists(RESPONSE_LOG):
        with open(RESPONSE_LOG, "w") as f: f.write("REST Response Log \n")
    if not os.path.exists(PERF_CSV):
        with open(PERF_CSV, "w") as f: f.write("Time,CPU(%),RAM(MB)\n")
    if not os.path.exists(AUTH_LOG):
        with open(AUTH_LOG, "w") as f: f.write("Auth Log\n")
        
    init_db() 

start_perf_logging()
