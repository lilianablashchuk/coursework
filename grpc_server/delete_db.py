# delete_lot_49_range.py
import asyncio
import aiosqlite
import os

DB_FILE = "auction_grpc.db"

LOT_ID_RANGE_START = 16
LOT_ID_RANGE_END = 20

async def delete_lots_by_range(start_id, end_id):

    if not os.path.exists(DB_FILE):
        print(f"Помилка: Файл бази даних '{DB_FILE}' не знайдено.")
        return

    conn = None
    try:
        conn = await aiosqlite.connect(DB_FILE)
        
        delete_bids_query = """
            DELETE FROM bids 
            WHERE lotId BETWEEN ? AND ?
        """
        await conn.execute(delete_bids_query, (start_id, end_id))
        
        delete_lots_query = """
            DELETE FROM lots 
            WHERE id BETWEEN ? AND ?
        """
        await conn.execute(delete_lots_query, (start_id, end_id))
        
    
        await conn.commit()
   
        print(f"Успішно виконано видалення лотів (та пов'язаних ставок) з ID від {start_id} до {end_id}.")
            
    except Exception as e:
        print(f"Помилка при доступі до БД: {e}")
        if conn:
            await conn.rollback()
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    print(f"Спроба видалити лоти в діапазоні ID: від {LOT_ID_RANGE_START} до {LOT_ID_RANGE_END}")
    asyncio.run(delete_lots_by_range(LOT_ID_RANGE_START, LOT_ID_RANGE_END))