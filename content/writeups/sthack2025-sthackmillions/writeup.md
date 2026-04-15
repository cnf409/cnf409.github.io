+++
type               = "ctf"
title              = "Sthack'Millions"
description        = "great for gambling addicts"
author             = "conflict"
date               = "2025-05-27"
language           = "en"
tags               = ["reverse", "misc", "osint", "web", "gambling", "qr_code"]
event              = "Sthack 2025"
category           = "misc"
challenge_author   = ["hackdaddy", "hessman"]
challenge_author_url = ["https://x.com/etienne_sellan", "https://www.linkedin.com/in/anthony-domingue-930203162/"]
pinned             = true
difficulty         = "medium"
solves             = ?
rating             = 10
redirect_from      = ["/posts/2025/05/sthack-2025-sthack-millions/"]
+++

# Introduction

**Sthack'Millions** was a series of 4 challenges involving `OSINT`, `Reversing`, and `Misc`. It was very interesting, not only because of the challenges themselves (which were very fun to do), but also because the challmakers actually built the machine that went along with the challenge. So we had a physical support, which made the whole experience even cooler.

The said machine was a classic lottery machine: you could either click "Play" and make a grid (5 numbers and one bonus number), which would then print out a ticket with a QR code, or check your grid by scanning the QR code and see if you won.

The final goal of this series was to get the _Jackpot_, a.k.a. having the correct 5 numbers **and** the bonus number.

# 1/4 - OSINT

## Taking a look at the machine itself

The machine looked like an arcade machine, covered in satirical stickers.

![machine_large.png](https://i.ibb.co/x8jNC65R/IMG-1562.jpg)

Even though they were funny, most of them were useless, except for one.

![sticker.png](https://i.ibb.co/YBBLBTqG/2025-05-27-135909-153x260-scrot.png)

Here we have a very useful hint: this machine is powered by a software called _Lotogiciel_, and it's even trademarked!

## Searching up the web

Despite not being a dorking expert, I still tried to search up this keyword but without success. 

It then occurred to me that there aren't many websites that host source code for software, so I typed _Lotogiciel_ on GitHub, and found something.

![github.png](https://i.ibb.co/Y4cjrYMv/2025-05-27-140432-913x279-scrot.png)

Since the commit's author is `hessman`, we can assume this repo is linked to the CTF.

## Exploring the repository

We notice two files here that are probably compiled executables.

The repository has three commits, which is a bit too much for just uploading two files, and not enough for an actual programming project, so let's take a look at them.

![commit.png](https://i.ibb.co/23jmfHwX/2025-05-27-140916-1473x456-scrot.png)

The second commit, called _info_, held the flag for the first step of this series!

# 2/4 - Reverse

Now let's clone the repo and take a look at these two executables.

## Inspecting the executables

```bash
lotogiciel: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=c1977b3e031316cf2b2ef5366d65ae7793a01c03, for GNU/Linux 4.4.0, not stripped
```

![meme](https://i.imgflip.com/9vbuj9.jpg)

One of the two executables is compiled for `aarch64` and the other for `x86-64`, but they seem to both originate from the same source code (based on the strings).

## Static analysis

After renaming most of the variables, here is how the code articulates itself:

- Reads the seed from `index.txt`

```c
  seed_file = fopen("index.txt","r");
  if (seed_file != (FILE *)0x0) {
    read_result = fgets(seed_buffer,0x20,seed_file);
    if (read_result == (char *)0x0) {
      fclose(seed_file);
    }
    else {
      fclose(seed_file);
```

- Gets time info, controls and normalizes the seed

```c
    else {
      fclose(seed_file);
      counter = __isoc23_strtol(seed_buffer,0,10);
      draw_time = time((time_t *)0x0);
      draw_time_info = localtime(&draw_time);
      current_seed = 0;
      if (-1 < counter) {
        current_seed = counter;
      }
```

- Generates the numbers

```c
      if (current_seed + 10U < 3001) {
        num_pointer = winning_numbers;
        draw_minutes = draw_time_info->tm_min;
        i = 0;
        numbers_ptr = num_pointer;
        while( true ) {
          while( true ) {
            number = ((char)(&pi_decimals)[i * 2 + current_seed] + -0x30 +
                      ((char)(&pi_decimals_2)[i * 2 + current_seed] * 5 + -0xf0) * 2 + draw_minutes)
                     % 49 + 1;
            *numbers_ptr = number;
            puVar2 = num_pointer;
            if (i != 0) break;
            numbers_ptr = numbers_ptr + 1;
            i = 1;
          }
          while( true ) {
            if (*puVar2 == number) {
              do {
                number = (int)number % 0x31 + 1;
                *numbers_ptr = number;
              } while (number == *puVar2);
            }
            puVar2 = puVar2 + 1;
            if (numbers_ptr == puVar2) break;
            number = *numbers_ptr;
          }
          i = i + 1;
          if (i == 5) break;
          numbers_ptr = numbers_ptr + 1;
        }
```

> The seed can't be higher than 3000.

> Numbers can't be higher than 49.

> There can be no duplicates.

> Uses the current time to pick numbers from _pi_ decimals.

- Prints out the winning numbers

```c
        do {
          number = *num_pointer;
          num_pointer = num_pointer + 1;
          printf(" %02d",(ulong)number);
        } while (end_marker != num_pointer);
```

- Increments the seed

```c
        seed_file = fopen("index.txt","w");
        if (seed_file != (FILE *)0x0) {
          fprintf(seed_file,"%ld\n",(current_seed + 10U) % 3000);
          fclose(seed_file);
          uVar1 = 0;
          goto LAB_00101304;
        }
```

> The seed is simply incremented by 10.

## Putting it all together

There are multiple interesting things here that show that the randomness of this generator can be predicted.

We can run the program with a simple seed `1234` to check that we understood how it works.

![first_draw.png](https://i.ibb.co/ynS8cKkT/2025-05-27-143952-616x44-scrot.png)

We indeed get a set of 5 numbers, so that confirms our understanding.

Some key takeaways:

- The next seed is predictable since the program only increments it by 10 on each draw.
    
- Seeds can't be higher than _3000_, which is not a lot and can be bruteforced.
    
- The program uses the current time (and the seed) to pick numbers.

## Getting the current seed

If we want to predict the next draw's result on the machine, we need to know what seed the last draw used. So let's go check what the last draw was.

![current_draw.png](https://i.ibb.co/kg5WGmG5/IMG-1570.jpg)

We'll make a script to list all the possible draws at this exact time using `faketime`.

```bash
DATE_STR="2025-05-23 01:11:54" 
START_SEED=0
END_SEED=3000

for SEED in $(seq "$START_SEED" "$END_SEED"); do
    echo "$SEED" > "index.txt"
    RESULT=$(faketime "$DATE_STR" "./lotogiciel" 2>/dev/null)
    printf "%d %s\n" "$SEED" "$RESULT" >> "results.txt"
done
```

Now, we have a `results.txt` file that should contain the draw that happened on the machine at `01:11` -> [_21_, _11_, _3_, _26_, _16_]

```text
root@e945e59da411:/app# grep "21 11 03 26 16" results.txt
2360  21 11 03 26 16
```

Great, we know the seed at `01:11` was `2360`!

## Predicting the draws

Now we'll make a script that takes the time of a draw, calculates the corresponding seed, and gives us the result!

```bash
# usage : ./automate.sh HH:MM:SS

REF_DATE="2025-05-23"
REF_TIME="01:11:54"
REF_SEED=2360

STEP_SEC=$((5*60))
SEED_STEP=10
MODULO=3000

[[ $# -lt 1 ]] && { echo "Usage: $0 HH:MM:SS"; exit 1; }

TIME_STR="$1"
DATE_STR="${2:-$REF_DATE}"

t_target=$(date -d "$DATE_STR $TIME_STR" +%s)
t_ref=$(date   -d "$REF_DATE $REF_TIME"  +%s)
diff=$((t_target - t_ref))

steps=$((diff / STEP_SEC))
(( diff < 0 && diff % STEP_SEC )) && (( steps-- ))

seed=$(( (REF_SEED + steps * SEED_STEP) % MODULO ))
(( seed < 0 )) && seed=$(( seed + MODULO ))

echo "$seed" > index.txt
draw=$(faketime "$DATE_STR $TIME_STR" ./lotogiciel 2>/dev/null)

printf "Heure  : %s %s\nSeed   : %d\nTirage : %s\n" \
       "$DATE_STR" "$TIME_STR" "$seed" "$draw"
```

![winning_draw.png](https://i.ibb.co/Fq0g14vY/2025-05-27-150653-472x88-scrot.png)

Let's verify that our script works by playing this grid on the machine and scanning the ticket after the draw.

![ticket](https://i.ibb.co/JDZBsqd/IMG-1572.jpg)

# 3/4 - Misc

We don't have much else to work on now that we can predict the draws, so let's dive into the last thing we didn't look at: the QR code.

## Analysing the QR code

The ticket's QR code holds JSON that looks like this:

```json
{
  "data": {
    "time": "2025-05-23 20:58:11",
    "draw": "2025-05-23 21:00",
    "numbers": [1, 2, 3, 4, 5],
    "chance": 1
  },
  "signature": "157e336c88301790fb9058001182257e57fb151f3fdc85492ef0802464827a9e",
  "prize": "flag.txt"
}
```

We have three main fields: `data`, `signature`, and `prize`.

The fact that `prize` comes after `signature` hints that it's not part of the _signed_ data. This means it could maybe be modified.

## Arbitrary File Read

Let's predict the next winning numbers, make a grid and get the QR code from the ticket. 

Then, modify the _JSON_ to put `app.py` in the `prize` field.

![afr_qr.png](https://i.ibb.co/ksH4hnMT/IMG-1573.png)

Then scan the QR code on the machine. It should see that we have the right numbers and print out the contents of the file named in `prize` (`app.py`).

![flag_3.png](https://i.ibb.co/M0NmW7b/IMG-1576.jpg)

(The flag is commented at the top of the ticket.)

![meme](https://i.imgflip.com/9vbvm4.jpg)

# 4/4 - Misc

Great! We can now read pretty much any file we want on the server, and we know it's running a Python _Flask_ architecture.

If you remember, our goal is to have a ticket with all the numbers correct **and** the bonus number. On the machine, we can only select bonus numbers between 1 and 10, but the draw's bonus numbers are always above 10.

![draws.png](https://i.ibb.co/TqKNmCn2/IMG-1582.jpg)

So there's only one way to get the _Jackpot_: arbitrarily crafting a QR code with the right numbers.

To do so, we need to know how the `signature` field works and the key used. But we can read any file, so that will be pretty trivial.

## Retrieving useful data

Let's read both `.env` and `sign.py` files.

![secret_key.png](https://i.ibb.co/rR8Fjyfs/IMG-1581.jpg)

![sign.py.png](https://i.ibb.co/vCcn165M/IMG-1583.jpg)

It's a simple _HMAC SHA-256_ signature on the `data` field. We have the function and the key used by the machine, so we can generate valid signatures.

## Signing tickets

Let's implement this in a small script:

```python
#!/usr/bin/env python3
import hmac, hashlib, json, sys

SECRET = "3c0a8dfe0420367"
PRIZE  = "flag.txt"

def _sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(),
                    hashlib.sha256).hexdigest()

def pack(data) -> str:
    if isinstance(data, str):
        data = json.loads(data)
    inner = json.dumps(data, separators=(", ", ": "))

    full = {"data": inner, "signature": _sign(inner), "prize": PRIZE}
    return json.dumps(full, separators=(", ", ": "))

if __name__ == "__main__":
    payload = sys.stdin.read().strip()
    print(pack(payload if payload else {}))
```

![script.py.png](https://i.ibb.co/CpkyDS8D/2025-05-27-155234-954x128-scrot.png)

Now that we have a valid _JSON_ payload that should give us a _Jackpot_, let's put it in a QR code and scan it on the machine!

![final.png](https://i.ibb.co/Z65Cj0fm/IMG-1587.jpg)

It worked, and we got a beautiful check for completing this challenge!

# Conclusion

This was definitely one of the best challenge series I've played. Having a physical machine was a great plus over other challenges, and seeing a whole source code printed on a ticket made my day (or my night, I guess?).

Thanks to `hackdaddy` and `hessman` for creating this series !

![meme](https://i.imgflip.com/9vbw2s.jpg)
