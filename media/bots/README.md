# Bot sprites (optional)

Drop a PNG here named after the bot, lowercase, spaces/punctuation replaced with `-`:

```
media/bots/tombstone.png
media/bots/minotaur.png
media/bots/beta.png
media/bots/whiplash.png
...
```

Recommended: square-ish canvas, transparent background, the bot roughly centered and filling the frame — it gets drawn into a `2*botRadius × 2*botRadius` box (currently 14×14 world units) and rotated/squashed with the body, so keep the silhouette readable at small size and simple enough to survive an 8× nearest-neighbor upscale.

If a bot's file is missing, `render.js`'s `loadSprite()` resolves to `null` and that bot falls back to the plain colored blob automatically — nothing else needs to change. Sprites can be added at any point, per bot, without touching code.
