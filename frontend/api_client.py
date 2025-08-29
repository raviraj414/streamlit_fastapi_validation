# frontend/api_client.py
import requests
from typing import Optional, Any, Dict

API_URL = "http://127.0.0.1:8000"
TIMEOUT = 6

def signup_user(name: str, email: str, password: str, role: str) -> bool:
    payload = {"name": name, "email": email, "password": password, "role": role}
    res = requests.post(f"{API_URL}/signup", json=payload, timeout=TIMEOUT)
    return res.ok

def login_user(email: str, password: str) -> Optional[Dict[str,Any]]:
    payload = {"email": email, "password": password}
    res = requests.post(f"{API_URL}/login", json=payload, timeout=TIMEOUT)
    if res.ok:
        return res.json()
    return None

def get_commands_with_contexts():
    res = requests.get(f"{API_URL}/commands", timeout=TIMEOUT)
    return res.json() if res.ok else []

def insert_dynamic_command(user_id: int, cmd_id: int, command_text: str):
    payload = {"user_id": user_id, "command_id": cmd_id, "command_text": command_text}
    res = requests.post(f"{API_URL}/mark_dynamic", json=payload, timeout=TIMEOUT)
    return res.ok

def insert_static_command(user_id: int, cmd_id: int, command_text: str):
    payload = {"user_id": user_id, "command_id": cmd_id, "command_text": command_text}
    res = requests.post(f"{API_URL}/mark_static", json=payload, timeout=TIMEOUT)
    return res.ok

def get_last_processed_cmd_id(user_id: int) -> int:
    res = requests.get(f"{API_URL}/last_cmd/{user_id}", timeout=TIMEOUT)
    if res.ok:
        return res.json().get("last_cmd_id", 0)
    return 0

def update_last_processed_cmd(user_id: int, last_cmd_id: int):
    payload = {"user_id": user_id, "last_cmd_id": last_cmd_id}
    res = requests.post(f"{API_URL}/update_last_cmd", json=payload, timeout=TIMEOUT)
    return res.ok

def get_all_validators():
    res = requests.get(f"{API_URL}/validators", timeout=TIMEOUT)
    return res.json() if res.ok else []

def get_validator_stats(user_id: int):
    res = requests.get(f"{API_URL}/validator_stats/{user_id}", timeout=TIMEOUT)
    return res.json() if res.ok else {"dynamic":0,"static":0,"processed":0,"remaining":0,"total":0}

def get_user_counts_by_role():
    res = requests.get(f"{API_URL}/user_counts", timeout=TIMEOUT)
    return res.json() if res.ok else {"validator_count":0,"viewer_count":0,"validator_names":[],"viewer_names":[]}

def get_recently_active_validators():
    res = requests.get(f"{API_URL}/recent_active", timeout=TIMEOUT)
    return res.json() if res.ok else []

def fetch_user_history(user_id: int, start_iso: Optional[str], end_iso: Optional[str], cmd_id: Optional[int], action_type: str = "All"):
    params = {}
    if start_iso:
        params["start"] = start_iso
    if end_iso:
        params["end"] = end_iso
    if cmd_id:
        params["cmd_id"] = cmd_id
    if action_type:
        params["type"] = action_type
    res = requests.get(f"{API_URL}/history/{user_id}", params=params, timeout=TIMEOUT)
    return res.json() if res.ok else []

def fetch_contexts_for_command(command_id: int):
    res = requests.get(f"{API_URL}/contexts/{command_id}", timeout=TIMEOUT)
    return res.json() if res.ok else []
