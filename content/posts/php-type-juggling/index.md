+++
type   = "post"
title  = "PHP Type Juggling — what it is and why it matters"
author = "conflict"
date   = "2023-01-07"
language = "en"
tags   = ["php", "web", "educative", "type-juggling"]
pinned = false
+++

## What is type juggling?

PHP is a loosely-typed language. When you compare two values with `==` (loose comparison), PHP tries to coerce them to the same type before comparing. This is called **type juggling** and it has produced some of the most cursed authentication bypass bugs in web security history.

## The comparison table

The key thing to understand is how PHP evaluates `==` between different types.

| Expression | Result |
|---|---|
| `"0" == false` | `true` |
| `"" == false` | `true` |
| `"0" == null` | `false` |
| `"php" == 0` | `true` (in PHP < 8) |
| `"1" == true` | `true` |
| `"01" == "1"` | `true` |
| `"10" == "1e1"` | `true` |
| `100 == "1e2"` | `true` |

## Classic auth bypass

Suppose you have this login check:

```php
<?php
$password_hash = "0e123456789012345678901234567890";

if ($_POST['password'] == $password_hash) {
    echo "Access granted";
}
```

The hash starts with `0e` — PHP interprets this as scientific notation: `0 * 10^123... = 0`. Any input that also evaluates to `0` under `==` will pass.

Sending `password=0` bypasses this entirely.

```terminal
$ curl -X POST http://target.com/login \
  -d 'username=admin&password=0'
Access granted
```

## The magic hashes

There is a known list of MD5 and SHA1 hashes that start with `0e` and whose remaining characters are all digits — they all evaluate to `0` under loose comparison.

```
MD5("240610708")  = 0e462097431906509019562988736854
MD5("QNKCDZO")   = 0e830400451993494058024219903391
MD5("aabg74560")  = 0e087386482136013740957780965295
```

## The fix

Always use strict comparison (`===`) when comparing security-sensitive values:

```php
<?php
if ($_POST['password'] === $stored_hash) {
    // safe
}
```

Or better, use `password_verify()` which is constant-time and uses `===` internally.

```php
<?php
if (password_verify($_POST['password'], $stored_hash)) {
    // correct and safe
}
```

## PHP 8 changes

PHP 8 changed the behavior of `0 == "string"` to return `false`, which removes a large class of these vulnerabilities. But `"0e123" == "0e456"` still returns `true`, so the magic hash problem persists.

> Always use `===` and `password_verify()`. Never roll your own comparison for credentials.
