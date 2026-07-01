# 🎁 Claude Wrapped

A [Spotify-Wrapped](https://www.spotify.com/wrapped/)-style year-in-review for **[Claude Code](https://claude.com/claude-code)** — built entirely from the session logs Claude Code writes to disk.

Scroll through your spend, tokens, tool calls, longest sessions, and the fun superlatives, one full-screen scene at a time.

> Claude Code stores **no dollar figures** in its logs — cost is reconstructed token-by-token from current published per-model rates. Treat it as a close estimate, not a bill.

## Demo

Open `index.html` in a browser, or host it free on **GitHub Pages** (Settings → Pages → deploy from `main`). It's a single self-contained file — no build step, no dependencies.

## Wrap your own year

```bash
git clone https://github.com/jjlien06/claude-wrapped
cd claude-wrapped
python3 generate.py        # reads ~/.claude/projects
open wrapped.html          # your Wrapped (or double-click it)
```

That's it — no dependencies, Python standard library only. `generate.py` reconstructs your stats and writes **`wrapped.html`** — a filled-in copy with your numbers. `index.html` stays a scrubbed template, and `wrapped.html` is gitignored, so you can't accidentally commit your own filenames/spend.

Flags:

```bash
python3 generate.py --date 06/08/26-07/01/26   # only this date range (default: all logs)
python3 generate.py --logs /path      # a different logs directory
python3 generate.py --out mine.html   # write somewhere else
python3 generate.py --print           # print the report only, write no file
python3 generate.py --json out.json   # also dump the raw data block
```

Example report:

```
════════════════════════════════════════════════════
  CLAUDE WRAPPED   2026-06-08 → 2026-07-01
════════════════════════════════════════════════════
  Total spend        $2,868.10
  Sessions           93
  Messages           59,645  (you 21,884 · Claude 37,761)
  Output tokens      13,602,497
  Tool calls         18,894
  Cache hit rate     97.1%
  Cache saved        $14,566.72
  ...
```

## How the numbers are computed

- **Logs**: every `.jsonl` under `~/.claude/projects` (all projects).
- **Dedup**: usage rows keyed by `(message id, request id)` so log replays aren't double-counted.
- **Cost** = `input × rate + output × rate + cache-read × 0.1 + cache-write × (1.25 for 5-min / 2 for 1-hour)`, at each model's published $/M rate.
- Rates live in `RATES` at the top of `generate.py` — edit them if pricing changes.

## Files

| File | What |
|---|---|
| `index.html` | The Wrapped site — self-contained, responsive, keyboard-navigable, reduced-motion-safe. |
| `generate.py` | Parses your logs and prints the stats to plug in. Standard library only. |

## Notes

- Cache-write TTL split (5-min vs 1-hour) is read from `usage.cache_creation` when present; older logs fall back to 5-min.
- Sonnet 5 is priced at the $3/$15 sticker rate (intro $2/$10 through 2026-08-31 would trim a little).
- Not affiliated with Anthropic. Made with Claude Code.

## License

MIT — see [LICENSE](LICENSE).
