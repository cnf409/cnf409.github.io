Panels are the frames everything sits in: ink borders at four weights, a caption tab, a screentone drop instead of a shadow, and the diagonal cut.

- `.panel` = paper + `stroke-panel`. Add `.panel__tab` as the first child for a caption (`INFO`, `BOX`, `CONNECT`).
- `.tone-drop` casts an 8px screentone copy behind a panel. Use it once or twice per page, never on cards in a list.
- `.cut` wraps one child and cuts its right edge diagonally (`--cut`, default 56px). One per page at most.
- `.balloon` is a speech-balloon edge, reserved for the 404 message.
