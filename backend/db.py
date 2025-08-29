# backend/db.py
import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.hashing import hash_password  # local helper if needed

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False
    )

def safe_dict_row(row, cursor):
    # convert tuple row + column names -> dict
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cols = [d[0] for d in cursor.description]
    return {cols[i]: row[i] for i in range(len(cols))}

# -------------------- AUTH --------------------
def create_user(name: str, email: str, plain_password: str, role: str = "validator") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        hashed = hash_password(plain_password)
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed, role)
        )
        conn.commit()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            return False
        user_id = row[0]

        # Create per-user tables for validators
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS dynamic_cmds_user_{user_id} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_id INT,
                command_text TEXT,
                processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS static_cmds_user_{user_id} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_id INT,
                command_text TEXT,
                processed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    except mysql.connector.Error as e:
        conn.rollback()
        print("create_user error:", e)
        return False
    finally:
        cursor.close()
        conn.close()

def authenticate_user(email: str, plain_password: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (hash_password(plain_password),)
            if False else (email, hash_password(plain_password))
        )
        # Note: preserve original semantics: email+hashed password match
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, hash_password(plain_password))
        )
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        conn.close()

# -------------------- COMMANDS & CONTEXTS --------------------
def get_commands_with_contexts() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                a.id AS argument_id,
                c.id AS command_id,
                a.full_command_line,
                ctx.context_lines
            FROM commands c
            JOIN arguments a ON c.id = a.command_id
            LEFT JOIN contexts ctx ON ctx.argument_id = a.id
            ORDER BY c.id;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        for row in results:
            if row.get("context_lines"):
                row["context_lines"] = row["context_lines"].replace("\\n", "\n").replace("\\\\", "\\")
        return results
    finally:
        cursor.close()
        conn.close()

def insert_dynamic_command(user_id: int, cmd_id: int, command_text: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO dynamic_cmds_user_{user_id} (command_id, command_text)
            VALUES (%s, %s)
        """, (cmd_id, command_text))
        update_last_seen(user_id)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def insert_static_command(user_id: int, cmd_id: int, command_text: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO static_cmds_user_{user_id} (command_id, command_text)
            VALUES (%s, %s)
        """, (cmd_id, command_text))
        update_last_seen(user_id)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# -------------------- HISTORY / CONTEXTS --------------------
def fetch_user_history(
    user_id: int,
    start_dt: Optional[datetime],
    end_dt: Optional[datetime],
    cmd_id: Optional[int],
    action_type: str = "All"
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        dyn_table = f"dynamic_cmds_user_{user_id}"
        sta_table = f"static_cmds_user_{user_id}"

        selects = []
        params_all: List[Any] = []

        if action_type in ("All", "Dynamic"):
            q = f"SELECT id AS command_id, command_text, 'Dynamic' AS action, processed_time FROM {dyn_table}"
            where = []
            if start_dt:
                where.append("processed_time >= %s"); params_all.append(start_dt)
            if end_dt:
                where.append("processed_time <= %s"); params_all.append(end_dt)
            if cmd_id is not None:
                where.append("command_id = %s"); params_all.append(cmd_id)
            if where:
                q += " WHERE " + " AND ".join(where)
            selects.append(q)

        if action_type in ("All", "Static"):
            q = f"SELECT id AS command_id, command_text, 'Static' AS action, processed_time FROM {sta_table}"
            where = []
            if start_dt:
                where.append("processed_time >= %s"); params_all.append(start_dt)
            if end_dt:
                where.append("processed_time <= %s"); params_all.append(end_dt)
            if cmd_id is not None:
                where.append("command_id = %s"); params_all.append(cmd_id)
            if where:
                q += " WHERE " + " AND ".join(where)
            selects.append(q)

        if not selects:
            return []

        final_query = " UNION ALL ".join(selects) + " ORDER BY command_id ASC, processed_time ASC LIMIT 2000"
        cursor.execute(final_query, tuple(params_all))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print("fetch_user_history error:", e)
        return []
    finally:
        cursor.close()
        conn.close()

def fetch_contexts_for_command(command_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                a.id AS argument_id,
                c.id AS command_id,
                a.full_command_line,
                ctx.context_lines
            FROM commands c
            JOIN arguments a ON c.id = a.command_id
            LEFT JOIN contexts ctx ON ctx.argument_id = a.id
            WHERE c.id = %s
            ORDER BY a.id;
        """
        cursor.execute(query, (command_id,))
        results = cursor.fetchall()
        for row in results:
            if row.get("context_lines"):
                row["context_lines"] = row["context_lines"].replace("\\n", "\n").replace("\\\\", "\\")
        return results
    finally:
        cursor.close()
        conn.close()

# -------------------- LAST PROCESSED & METRICS --------------------
def get_last_processed_cmd_id(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT last_processed_cmd_id FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else 0
    finally:
        cursor.close()
        conn.close()

def update_last_processed_cmd(user_id: int, cmd_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET last_processed_cmd_id = %s WHERE id = %s", (cmd_id, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def update_last_seen(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET last_seen = %s WHERE id = %s", (datetime.now(), user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# -------------------- ADMIN / STATS --------------------
def get_all_validators() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name FROM users WHERE role = 'validator'")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_user_counts_by_role():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='validator'")
        validator_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role='viewer'")
        viewer_count = cursor.fetchone()[0]

        cursor.execute("SELECT name FROM users WHERE role='validator'")
        validator_names = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT name FROM users WHERE role='viewer'")
        viewer_names = [row[0] for row in cursor.fetchall()]

        return validator_count, viewer_count, validator_names, viewer_names
    finally:
        cursor.close()
        conn.close()

def get_recently_active_validators():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT name, last_seen FROM users
            WHERE role = 'validator'
            ORDER BY last_seen DESC
            LIMIT 10
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_validator_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM dynamic_cmds_user_{user_id}")
            dynamic_count = cursor.fetchone()[0]
        except:
            dynamic_count = 0

        try:
            cursor.execute(f"SELECT COUNT(*) FROM static_cmds_user_{user_id}")
            static_count = cursor.fetchone()[0]
        except:
            static_count = 0

        processed = (dynamic_count or 0) + (static_count or 0)

        cursor.execute("SELECT COUNT(DISTINCT id) FROM commands")
        total_commands = cursor.fetchone()[0] or 0
        remaining = max(0, total_commands - processed)

        return {
            "dynamic": dynamic_count,
            "static": static_count,
            "processed": processed,
            "remaining": remaining,
            "total": total_commands
        }
    finally:
        cursor.close()
        conn.close()
