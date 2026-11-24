# The Meridian — Tuesday, 24 November 2026

[![badge](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/semutadv/news-image-20261124-entry/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard)
[![reward](https://make.fun/badge/news-image-20261124/semutadv/news-image-20261124-entry/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

A one-page illustrated newspaper summing up the world's news of
**Tuesday, 24 November 2026**, drawn entirely by a Python program.

`main.py` (Python 3, standard library only — no PIL, no third-party
packages) renders the front page pixel by pixel with a built-in bitmap
typeface and hand-drawn pictograms, encodes it as an indexed-colour
PNG, and writes it to `/output/entry.png` (or
`$MAKEFUN_OUTPUT_DIR/entry.png`). The output is fully deterministic:
the same bytes on every run, well under the 1 MiB / 1024×1024 limits.

The page carries 45 stories from that day across world news, war,
politics, the Middle East, climate and disasters, the Americas, Asia
and health, business and technology, science and space, sport and
culture — led by Ukraine's announcement that its drones sank a Russian
warship off Libya.

## Run it

```sh
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
# writes out/entry.png
```

## License

MIT — see `LICENSE`.
