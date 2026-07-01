#!/usr/bin/env python3
"""
Claude Wrapped — turn your Claude Code session logs into a scroll-through
year-in-review.

Parses the .jsonl logs Claude Code writes under ~/.claude/projects, reconstructs
your usage, and writes the numbers straight into index.html. Then just open
index.html in a browser.

    python3 generate.py                 # scan ~/.claude/projects, update index.html
    python3 generate.py --logs PATH     # scan a different logs directory
    python3 generate.py --print         # print the report, don't touch index.html
    python3 generate.py --json out.json # also dump the raw data block

Cost is reconstructed from token counts at current published per-model rates —
Claude Code stores no dollar figures, so treat it as a close estimate.
"""
import argparse, json, glob, os, re, html, collections, datetime, sys

# Published per-model rates, $/million tokens: (input, output).
# Cache reads bill at 0.1x input; cache writes at 1.25x (5-min) / 2x (1-hour).
RATES = {
    "claude-opus-4-8": (5, 25), "claude-fable-5": (10, 50),
    "claude-sonnet-5": (3, 15), "claude-sonnet-4-6": (3, 15),
    "claude-haiku-4-5-20251001": (1, 5),
}
NICE = {"claude-opus-4-8": "Opus 4.8", "claude-fable-5": "Fable 5",
        "claude-sonnet-5": "Sonnet 5", "claude-sonnet-4-6": "Sonnet 4.6",
        "claude-haiku-4-5-20251001": "Haiku 4.5"}
M = 1_000_000
HERE = os.path.dirname(os.path.abspath(__file__))


def parse(logs, drange=None):
    """drange: optional (start_date, end_date) — only count activity within it."""
    dmin, dmax = drange if drange else (None, None)
    files = glob.glob(os.path.join(logs, "**", "*.jsonl"), recursive=True)
    if not files:
        sys.exit(f"No .jsonl logs found under {logs}")
    seen = set()
    model = collections.defaultdict(lambda: collections.Counter())   # per-model token counters
    creads = collections.Counter()                                   # cache reads per model
    tools = collections.Counter(); bash = collections.Counter()
    reads = collections.Counter(); edits = collections.Counter()
    byhour = collections.Counter(); active = set()
    roles = collections.Counter()
    sess = collections.defaultdict(lambda: {"msgs": 0, "cost": 0.0, "out": 0,
                                            "first": None, "last": None})
    web = think = errors = agents = usr_chars = maxout = maxusr = 0

    for f in files:
        for line in open(f, errors="replace"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            dt = None; ts = d.get("timestamp")
            if ts:
                try:
                    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    dt = None
            if dmin:  # date filter active — drop anything outside the window (incl. undated lines)
                if dt is None or not (dmin <= dt.date() <= dmax):
                    continue
            if dt:
                byhour[dt.hour] += 1; active.add(dt.date().isoformat())
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            roles[m.get("role", "?")] += 1
            cont = m.get("content")
            if d.get("type") == "user" and isinstance(cont, str):
                usr_chars += len(cont); maxusr = max(maxusr, len(cont))
            if isinstance(cont, list):
                for b in cont:
                    if not isinstance(b, dict):
                        continue
                    bt = b.get("type"); inp = b.get("input") or {}
                    if bt == "tool_use":
                        nm = b.get("name", "?"); tools[nm] += 1
                        if nm == "Bash":
                            cmd = (inp.get("command") or "").strip()
                            tok = re.split(r"\s+", cmd)[0].split("/")[-1] if cmd else ""
                            if tok: bash[tok] += 1
                        elif nm == "Read":
                            p = inp.get("file_path") or inp.get("path") or ""
                            if p: reads[os.path.basename(p)] += 1
                        elif nm in ("Edit", "Write"):
                            p = inp.get("file_path") or ""
                            if p: edits[os.path.basename(p)] += 1
                        elif nm in ("WebSearch", "WebFetch"): web += 1
                        elif nm in ("Agent", "Task", "TaskCreate", "Workflow"): agents += 1
                    elif bt == "thinking": think += 1
                    elif bt == "tool_result" and b.get("is_error"): errors += 1
                    elif bt == "text" and d.get("type") == "user":
                        usr_chars += len(b.get("text", "")); maxusr = max(maxusr, len(b.get("text", "")))
            u = m.get("usage")
            if not u:
                continue
            key = (m.get("id"), d.get("requestId"))
            if key[0] and key in seen:
                continue
            seen.add(key)
            mdl = m.get("model", "?"); c = model[mdl]
            for fld in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
                c[fld] += u.get(fld, 0)
            cc = u.get("cache_creation") or {}
            c5, c1 = cc.get("ephemeral_5m_input_tokens", 0), cc.get("ephemeral_1h_input_tokens", 0)
            if c5 + c1 == 0:
                c5 = u.get("cache_creation_input_tokens", 0)
            c["cw5"] += c5; c["cw1"] += c1
            creads[mdl] += u.get("cache_read_input_tokens", 0)
            maxout = max(maxout, u.get("output_tokens", 0))
            sid = d.get("sessionId") or f; s = sess[sid]
            s["msgs"] += 1; s["cost"] += _cost(c_row(u), mdl); s["out"] += u.get("output_tokens", 0)
            if dt:
                s["first"] = min(s["first"], dt) if s["first"] else dt
                s["last"] = max(s["last"], dt) if s["last"] else dt
    return dict(files=len(files), model=model, creads=creads, tools=tools, bash=bash,
                reads=reads, edits=edits, byhour=byhour, active=active, roles=roles,
                sess=sess, web=web, think=think, errors=errors, agents=agents,
                usr_chars=usr_chars, maxout=maxout, maxusr=maxusr)


def c_row(u):
    cc = u.get("cache_creation") or {}
    c5, c1 = cc.get("ephemeral_5m_input_tokens", 0), cc.get("ephemeral_1h_input_tokens", 0)
    if c5 + c1 == 0:
        c5 = u.get("cache_creation_input_tokens", 0)
    return collections.Counter(input_tokens=u.get("input_tokens", 0),
                               output_tokens=u.get("output_tokens", 0),
                               cache_read_input_tokens=u.get("cache_read_input_tokens", 0),
                               cw5=c5, cw1=c1)


def _cost(c, mdl):
    if mdl not in RATES:
        return 0.0
    pin, pout = RATES[mdl]
    return (c["input_tokens"] * pin + c["output_tokens"] * pout
            + c["cache_read_input_tokens"] * pin * 0.1
            + c["cw5"] * pin * 1.25 + c["cw1"] * pin * 2) / M


def hour_label(h):
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}{ap}"


def streak_len(active):
    days = sorted(datetime.date.fromisoformat(x) for x in active)
    best = cur = 1 if days else 0
    for i in range(1, len(days)):
        cur = cur + 1 if (days[i] - days[i - 1]).days == 1 else 1
        best = max(best, cur)
    return best


def build_data(r):
    modelcost = {NICE.get(k, k): sum(_cost(c, k) for c in [c]) for k, c in r["model"].items() if k in RATES}
    modelcost = {NICE.get(k, k): round(_cost(c, k), 2) for k, c in r["model"].items() if k in RATES}
    models = sorted(modelcost.items(), key=lambda x: -x[1])
    grand = round(sum(v for _, v in models), 2)
    out_tok = sum(c["output_tokens"] for c in r["model"].values())
    in_tok = sum(c["input_tokens"] for c in r["model"].values())
    cr = sum(c["cache_read_input_tokens"] for c in r["model"].values())
    cw = sum(c["cw5"] + c["cw1"] for c in r["model"].values())
    saved = round(sum(r["creads"][k] * RATES[k][0] * 0.9 for k in RATES) / M)
    users = r["roles"].get("user", 0); asst = r["roles"].get("assistant", 0)
    days_span = 1
    if r["active"]:
        lo, hi = min(r["active"]), max(r["active"])
        days_span = (datetime.date.fromisoformat(hi) - datetime.date.fromisoformat(lo)).days + 1
    peak = max(r["byhour"], key=r["byhour"].get) if r["byhour"] else 0

    srows = []
    for s in r["sess"].values():
        hrs = (s["last"] - s["first"]).total_seconds() / 3600 if s["first"] and s["last"] else 0
        srows.append((s["msgs"], round(s["cost"], 2), round(hrs, 1), s["out"]))
    longest = max(srows, key=lambda x: x[2]) if srows else (0, 0, 0, 0)
    priciest = max((x[1] for x in srows), default=0)

    top_read = r["reads"].most_common(1)
    topfile = top_read[0][0] if top_read else "your busiest file"
    reads_n = top_read[0][1] if top_read else 0
    edits_n = r["edits"].get(topfile, 0)
    cents = (grand / users * 100) if users else 0
    per_msg = f"{round(cents)}¢" if cents < 100 else f"${grand/users:.2f}"

    sup = _superlatives(r, saved, longest, priciest, models, grand, topfile, reads_n, edits_n)

    return {
        "range": [min(r["active"]) if r["active"] else "", max(r["active"]) if r["active"] else ""],
        "days": days_span, "grand": grand, "perDay": round(grand / days_span),
        "perMsg": per_msg, "models": [[k, round(v)] for k, v in models],
        "topModel": models[0][0] if models else "—",
        "topModelPct": round(100 * models[0][1] / grand) if models and grand else 0,
        "messages": users + asst, "userMsgs": users, "asstMsgs": asst,
        "outputTokensM": round(out_tok / M, 1), "novels": round(out_tok * 0.75 / 90000),
        "userCharsM": round(r["usr_chars"] / M, 1), "toolCalls": sum(r["tools"].values()),
        "topTools": [[k, v] for k, v in r["tools"].most_common(3)],
        "cacheHitPct": round(100 * cr / max(cr + cw + in_tok, 1), 1), "cacheSaved": saved,
        "peakHourLabel": hour_label(peak), "activeDays": len(r["active"]),
        "streak": streak_len(r["active"]), "web": r["web"], "thinking": r["think"],
        "agents": r["agents"], "errors": r["errors"], "maxOutput": r["maxout"],
        "longestSessionHrs": round(longest[2]), "longestSessionMsgs": longest[0],
        "longestSessionOutK": round(longest[3] / 1000), "longestSessionCost": round(longest[1]),
        "priciestSession": round(priciest), "topFile": topfile,
        "topFileReads": reads_n, "topFileEdits": edits_n, "superlatives": sup,
    }


def _superlatives(r, saved, longest, priciest, models, grand, topfile, reads_n, edits_n):
    b = r["bash"]; t = r["tools"]
    cd = b.get("cd", 0); grep = b.get("grep", 0); bash_total = sum(b.values())
    night = r["byhour"].get(0, 0)
    ask = t.get("AskUserQuestion", 0); art = t.get("Artifact", 0)
    cand = [
        ("🏦", "The cache paid rent", f"Prompt caching saved <b>${saved:,}</b> at 10% of full input price.", saved > 0),
        ("🕰️", "Never-ending session", f"One session stayed open <b>{round(longest[2])} hours</b> — {longest[0]:,} messages.", longest[2] >= 2),
        ("💸", "Big spender", f"<b>${round(priciest):,}</b> in a single session.", priciest > 0),
        ("📋", "The mega-paste", f"Longest single message: <b>{r['maxusr']:,}</b> characters.", r["maxusr"] > 5000),
        ("⚡", "Bash workhorse", f"<b>{bash_total:,}</b> commands — <b>{cd:,}</b> were just <code>cd</code>.", bash_total > 0),
        ("🔎", "grep-happy", f"Searched with grep <b>{grep:,}</b> times.", grep > 0),
        ("📖", "Comfort file", f"<code>{html.escape(topfile)}</code>: read <b>{reads_n}×</b>, edited <b>{edits_n}×</b>.", reads_n > 0),
        ("🤖", f"{models[0][0]} carried it" if models else "Top model", f"<b>{round(100*models[0][1]/grand)}%</b> of all spend ran on {models[0][0]}." if models and grand else "", bool(models)),
        ("🧠", "Deep thinker", f"<b>{r['think']:,}</b> extended-reasoning passes.", r["think"] > 0),
        ("🌙", "Night owl", f"<b>{night:,}</b> events logged after midnight.", night > 0),
        ("🧩", "Delegator", f"<b>{r['agents']:,}</b> sub-agents & workflows dispatched.", r["agents"] > 0),
        ("🐘", "Biggest reply", f"<b>{r['maxout']:,}</b> output tokens in one message.", r["maxout"] > 0),
        ("❓", "Claude asked back", f"<b>{ask:,}</b> clarifying questions to you.", ask > 0),
        ("🎨", "Meta moment", f"<b>{art:,}</b> artifacts built — including this one.", art > 0),
        ("📅", "Consistency", f"<b>{streak_len(r['active'])}-day</b> streak; {len(r['active'])} days active.", len(r["active"]) > 1),
    ]
    return [{"em": e, "t": ti, "s": s} for e, ti, s, keep in cand if keep]


def inject(data, template, out):
    page = open(template, encoding="utf-8").read()
    block = json.dumps(data, indent=2, ensure_ascii=False)
    # Escape so nothing in the data (e.g. an odd filename) can break out of the
    # <script> tag. JSON.parse decodes these \uXXXX back to the real chars.
    for ch, esc in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                    (" ", "\\u2028"), (" ", "\\u2029")):
        block = block.replace(ch, esc)
    new, n = re.subn(
        r'(<script id="wrapped-data" type="application/json">).*?(</script>)',
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, count=1, flags=re.S)
    if not n:
        sys.exit(f"Could not find the <script id=\"wrapped-data\"> block in {template}")
    open(out, "w", encoding="utf-8").write(new)


def report(d):
    print("═" * 52)
    print(f"  CLAUDE WRAPPED   {d['range'][0]} → {d['range'][1]}")
    print("═" * 52)
    print(f"  Total spend      ${d['grand']:,.2f}   (~${d['perDay']}/day, {d['perMsg']}/msg)")
    print(f"  Messages         {d['messages']:,}  (you {d['userMsgs']:,} · Claude {d['asstMsgs']:,})")
    print(f"  Output tokens    {d['outputTokensM']}M   You typed {d['userCharsM']}M chars")
    print(f"  Tool calls       {d['toolCalls']:,}   Cache hit {d['cacheHitPct']}% (saved ${d['cacheSaved']:,})")
    print(f"  Top model        {d['topModel']} ({d['topModelPct']}%)")
    print(f"  Longest session  {d['longestSessionHrs']}h / {d['longestSessionMsgs']:,} msgs")
    print(f"  Peak hour        {d['peakHourLabel']}   Active {d['activeDays']}/{d['days']} days")
    print("  Spend by model:  " + " · ".join(f"{k} ${v:,}" for k, v in d["models"]))
    print("═" * 52)
    print("  Note: token-cost estimate at API rates. On a Pro/Max plan you")
    print("  didn't pay this — it's what the usage would cost pay-as-you-go.")


def main():
    ap = argparse.ArgumentParser(description="Claude Code usage → Wrapped")
    ap.add_argument("--logs", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--date", metavar="MM/DD/YY-MM/DD/YY",
                    help="only include activity in this date range (inclusive); "
                         "default is all logs")
    ap.add_argument("--template", default=os.path.join(HERE, "index.html"),
                    help="page template to fill (kept unmodified)")
    ap.add_argument("--out", default=os.path.join(HERE, "wrapped.html"),
                    help="where to write your filled-in Wrapped (gitignored by default)")
    ap.add_argument("--print", action="store_true", dest="only_print",
                    help="print the report only; write no file")
    ap.add_argument("--json", help="also write the raw data block to this file")
    a = ap.parse_args()

    drange = None
    if a.date:
        try:
            lo, hi = a.date.split("-")
            drange = (datetime.datetime.strptime(lo.strip(), "%m/%d/%y").date(),
                      datetime.datetime.strptime(hi.strip(), "%m/%d/%y").date())
        except Exception:
            sys.exit("--date must look like MM/DD/YY-MM/DD/YY, e.g. 06/08/26-07/01/26")
        if drange[0] > drange[1]:
            sys.exit("--date start is after end")

    data = build_data(parse(a.logs, drange))
    report(data)
    if a.json:
        json.dump(data, open(a.json, "w"), indent=2, ensure_ascii=False)
        print(f"  wrote {a.json}")
    if not a.only_print:
        inject(data, a.template, a.out)
        print(f"\n  ✓ Wrote {a.out} — open it in a browser to see your Wrapped.")
        print("    (index.html stays a scrubbed template so you don't accidentally commit your own data.)")


if __name__ == "__main__":
    main()
