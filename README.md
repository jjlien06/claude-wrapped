# 🎁 Claude Wrapped

A [Spotify-Wrapped](https://www.spotify.com/wrapped/)-style year-in-review for **[Claude Code](https://claude.com/claude-code)** — built entirely from the session logs on your own machine.

Scroll through your spend, tokens, tool calls, longest sessions, and a wall of superlatives, one full-screen scene at a time.

![MIT License](https://img.shields.io/badge/license-MIT-black)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-black)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-black)

**▶ Live demo:** https://jjlien06.github.io/claude-wrapped/ *(sample data)*

> Claude Code stores **no dollar figures** in its logs — cost is reconstructed token-by-token from current published per-model rates. Treat it as a close estimate, not a bill.

## Wrap your own year

```bash
git clone https://github.com/jjlien06/claude-wrapped
cd claude-wrapped
python3 generate.py        # reads ~/.claude/projects
open wrapped.html          # your Wrapped (or just double-click it)
```

That's it — **no dependencies, Python standard library only.** `generate.py` reconstructs your stats and writes **`wrapped.html`**, a filled-in copy with your numbers. `index.html` stays a scrubbed template and `wrapped.html` is gitignored, so you can't accidentally commit your own filenames or spend.

### Options

```bash
python3 generate.py --date 06/08/26-07/01/26   # limit to a date range (MM/DD/YY-MM/DD/YY; default: all logs)
python3 generate.py --logs /path/to/logs       # a different logs directory
python3 generate.py --out mine.html            # write the page somewhere else
python3 generate.py --print                    # print the report only, write no file
python3 generate.py --json stats.json          # also dump the raw data as JSON
```

## What you'll see

A scroll-snap story of thirteen scenes:

| | Scene |
|---|---|
| 💸 | Total spend — and your $/day, ¢/message |
| 💬 | Messages sent vs. Claude's replies |
| 🔤 | Output tokens (≈ how many novels) + characters you typed |
| 🕰️ | Your prime hour, active days, longest streak |
| 🤖 | Spend by model, ranked |
| 🛠️ | Tool calls, with a top-3 leaderboard |
| 🏦 | Cache savings + hit rate |
| ⏱️ | Your longest single session |
| 📁 | The file you reopened most |
| 🏆 | A 15-card **superlatives wall** (mega-pastes, night-owl hours, grep counts, …) |
| 🧾 | A shareable recap card |

Count-up numbers, per-scene gradients, keyboard navigation, a progress bar, and `prefers-reduced-motion` support.

## Example report

```
════════════════════════════════════════════════════
  CLAUDE WRAPPED   2026-06-08 → 2026-07-01
════════════════════════════════════════════════════
  Total spend      $2,868.10   (~$120/day, 13¢/msg)
  Messages         59,645  (you 21,884 · Claude 37,761)
  Output tokens    13.6M   You typed 6.3M chars
  Tool calls       18,894   Cache hit 97.1% (saved $14,567)
  Top model        Opus 4.8 (73%)
  Longest session  66h / 1,811 msgs
  Peak hour        5PM   Active 22/24 days
  Spend by model:  Opus 4.8 $2,099 · Fable 5 $700 · Sonnet 4.6 $43 · ...
════════════════════════════════════════════════════
```

## How the numbers are computed

- **Logs**: every `.jsonl` under `~/.claude/projects` (all projects, unless `--date` narrows it).
- **Dedup**: usage rows keyed by `(message id, request id)` so log replays aren't double-counted.
- **Cost** = `input × rate + output × rate + cache-read × 0.1 + cache-write × (1.25 for 5-min / 2 for 1-hour)`, at each model's published $/M rate.
- Rates live in the `RATES` table at the top of `generate.py` — edit them when pricing changes.

## Privacy & safety

- **Nothing leaves your machine.** `generate.py` reads local files only — no network calls, no telemetry, no dependencies.
- **Your data stays local.** It writes to `wrapped.html` (gitignored); the committed `index.html` is a scrubbed sample. Publish that sample freely; keep your `wrapped.html` to yourself.
- **Injection-safe.** Values from your logs (e.g. odd filenames) are escaped before they're embedded in the page, so nothing in a log can execute when you open your Wrapped.

## Files

| File | What |
|---|---|
| `index.html` | The Wrapped page template — self-contained, responsive, keyboard-navigable, reduced-motion-safe. Reads its numbers from an embedded JSON block. |
| `generate.py` | Parses your logs and writes `wrapped.html`. Standard library only. |

## Notes

- Cache-write TTL split (5-min vs 1-hour) is read from `usage.cache_creation` when present; older logs fall back to 5-min.
- Sonnet 5 is priced at the $3/$15 sticker rate (the $2/$10 intro rate through 2026-08-31 would trim a little).
- Not affiliated with Anthropic.

## License

MIT — see [LICENSE](LICENSE).
