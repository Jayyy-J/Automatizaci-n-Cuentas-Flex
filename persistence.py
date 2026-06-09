from telegram.ext import BasePersistence, PersistenceInput
from database import get_connection
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)

class PostgresPersistence(BasePersistence):
    def __init__(self):
        super().__init__(store_data=PersistenceInput(bot_data=False, chat_data=False, user_data=True, callback_data=False))

    async def get_user_data(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id, data FROM estados_bot")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            user_data = defaultdict(dict)
            for user_id, data_json in rows:
                if data_json:
                    user_data[user_id] = json.loads(data_json)
            return user_data
        except Exception as e:
            logger.error(f"Error loading user_data: {e}")
            return defaultdict(dict)

    async def get_conversations(self, name):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id, state FROM estados_bot")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            conversations = {}
            for user_id, state in rows:
                if state is not None:
                    try:
                        conversations[(user_id, user_id)] = int(state)
                    except ValueError:
                        conversations[(user_id, user_id)] = state
            return conversations
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            return {}

    async def update_conversation(self, name, key, new_state):
        user_id = key[1]
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO estados_bot (user_id, state)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    state = EXCLUDED.state;
            """, (user_id, str(new_state) if new_state is not None else None))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")

    async def update_user_data(self, user_id, data):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO estados_bot (user_id, data)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    data = EXCLUDED.data;
            """, (user_id, json.dumps(data)))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating user_data: {e}")

    # Métodos no utilizados pero requeridos
    async def get_chat_data(self): return defaultdict(dict)
    async def update_chat_data(self, chat_id, data): pass
    async def get_bot_data(self): return {}
    async def update_bot_data(self, data): pass
    async def get_callback_data(self): return None
    async def update_callback_data(self, data): pass
    async def flush(self): pass
