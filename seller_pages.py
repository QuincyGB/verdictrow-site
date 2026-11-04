#!/usr/bin/env python3
"""seller_pages.py — per-seller grade pages for verdictrow.com
(Next-20 Integration Builds, Item 15 / Play 3).

Generates, from the fleet-checker's committed reciprocity ledger
(reciprocity-ledger.json, built by reciprocity_ledger.py from the
recorded Test-Purse buyer-mode run data ONLY):

    sellers/index.html            (every graded seller, one table)
    sellers/<slug>/index.html     (one grade page per seller)

Every figure on every page is copied programmatically from the
ledger — no purchase, amount, date or grade is hand-typed, and a
page never claims a purchase the records don't show. Grades are
shown with their basis and sample size; sellers below the ledger's
minimum sample carry "Insufficient data", not a letter.

Also appends the seller URLs to sitemap.xml (after route_pages.py
has regenerated it) and drops seller dirs no longer in the ledger,
so refreshes never orphan them.

Invoked by snapshot.py on every refresh; also runnable standalone.
Stdlib only. $0 spend: local files only, no network, never pays,
never sends.
"""
import html
import json
import re
import shutil
from pathlib import Path

import route_pages

SITE = Path(__file__).resolve().parent
CHECKER = Path(
    "~/workspace/goals/x402-fleet-integration-into-repeat-monitoring-loops/"
    "hidden_files/fleet-checker"
).expanduser()
LEDGER_PATH = CHECKER / "reciprocity-ledger.json"

BASE_URL = "https://verdictrow.com"
CONTACT = "Ren, Verdict Row Patrol — patrol@verdictrow.com"

BELT_LINKS = [
    ("ListSmith — Grade", "routes/list-smith-grade/",
     "grade a list of routes before you pay any of them"),
    ("RouteVerdict — Check", "routes/route-verdict-check/",
     "a pre-trade verdict on a single route"),
    ("StallRow — Grade My Stall", "routes/stall-row-grade-my-stall/",
     "grade your own stall the way this page grades sellers"),
    ("StallRow — Recheck", "routes/stall-row-recheck/",
     "recheck a route's live payment terms"),
]


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def money(v) -> str:
    return f"${float(v):.4f}"


def grade_label(s: dict) -> str:
    if s["delivery_grade"] == "Insufficient data":
        return "Insufficient data"
    return f"Grade {s['delivery_grade']}"


def belt_block(prefix: str) -> str:
    items = "".join(
        f'<li><a href="{prefix}{path}">{esc(name)}</a> — {esc(desc)}</li>'
        for name, path, desc in BELT_LINKS)
    return (
        "<h2>The inspector belt — routes that grade suppliers</h2>\n"
        "<p>These Verdict Row routes grade routes and suppliers the same "
        "way this page was built — from recorded payment outcomes:</p>\n"
        f"<ul>{items}</ul>\n"
        f'<p>All fleet routes: <a href="{prefix}routes/">route sheets</a> · '
        f'<a href="{prefix}function-tools/">function-calling schema pack</a>.</p>')


def render_index(ledger: dict) -> str:
    prefix = "../"
    t = ledger["totals"]
    rows = []
    for s in ledger["sellers"]:
        rows.append(
            '<tr><td><a href="{slug}/">{seller}</a></td>'
            "<td>{grade}</td><td>{verified} of {payment}</td>"
            "<td>{attempts}</td><td>{spent}</td><td>{last}</td></tr>".format(
                slug=esc(s["slug"]), seller=esc(s["seller"]),
                grade=esc(grade_label(s)),
                verified=s["verified_purchases"],
                payment=s["payment_attempts"],
                attempts=s["attempts_total"],
                spent=esc(money(s["total_spent_usd"])),
                last=esc(s["last_attempt_date"] or "—"),
            )
        )
    body = f"""<h1>Seller grade pages — the Test-Purse reciprocity ledger</h1>
<p>The Verdict Row Test Purse buys from other x402 sellers on a daily
buyer-mode run and records every outcome. This page is the cumulative
ledger of those recorded runs: <strong>{t['sellers']} sellers</strong>,
<strong>{t['runs']} runs</strong> ({esc(t['first_date'])} to
{esc(t['last_date'])}), <strong>{t['attempts_total']} recorded
attempts</strong>, <strong>{t['verified_purchases']} verified
purchases</strong>, <strong>{esc(money(t['total_spent_usd']))}</strong>
spent (recorded amounts only). Each seller has its own grade page
with the full attempt record behind its grade.</p>
<p><strong>Grade rule:</strong> {esc(ledger['grade_rule'])}</p>
<table>
<tr><th>Seller</th><th>Delivery grade</th><th>Verified of payment attempts</th><th>Recorded attempts</th><th>Total spent (recorded)</th><th>Last attempt</th></tr>
{''.join(rows)}
</table>
{belt_block(prefix)}
<p class="muted">Generated from the committed reciprocity ledger
(reciprocity_ledger.py, fleet-checker) — figures are copied
programmatically from recorded run data, never hand-typed. Contact:
{esc(CONTACT)}.</p>
"""
    return route_pages.page_shell(
        "Seller grades — Test-Purse reciprocity ledger · Verdict Row Patrol",
        f"Per-seller delivery grades from the Verdict Row Test Purse's "
        f"recorded buyer-mode runs: {t['sellers']} sellers, "
        f"{t['verified_purchases']} verified purchases, "
        f"{money(t['total_spent_usd'])} spent.",
        f"{BASE_URL}/sellers/", prefix, body)


def render_seller_page(s: dict) -> str:
    prefix = "../../"
    bought = ""
    if s["resources_bought"]:
        items = "".join(f"<li><code>{esc(r)}</code></li>" for r in s["resources_bought"])
        bought = (f"<h2>What we bought</h2>\n"
                  f"<p>Resources with a settlement-verified, delivered purchase "
                  f"({s['verified_purchases']} verified purchase(s) in total):</p>\n"
                  f"<ul>{items}</ul>")
    else:
        bought = ("<h2>What we bought</h2>\n"
                  "<p><strong>No verified purchase is recorded for this "
                  "seller.</strong> The attempts below never reached a "
                  "settlement-verified delivery, so this page claims no "
                  "purchase — only the recorded attempts.</p>")

    resource_rows = []
    for r in s["resources"]:
        statuses = ", ".join(f"{k}: {v}" for k, v in sorted(r["statuses"].items()))
        resource_rows.append(
            "<tr><td><code>{res}</code></td><td>{att}</td><td>{ver}</td>"
            "<td>{spent}</td><td>{statuses}</td></tr>".format(
                res=esc(r["resource"]), att=r["attempts"],
                ver=r["verified_purchases"], spent=esc(money(r["spent_usd"])),
                statuses=esc(statuses)))
    outcome_rows = "".join(
        f"<tr><td><code>{esc(k)}</code></td><td>{v}</td></tr>"
        for k, v in s["outcomes"].items())
    attempt_rows = []
    for a in s["attempt_records"]:
        if a["amount_usd"] is not None:
            amt = (f"{esc(money(a['amount_usd']))} "
                   f"({'spent' if a.get('spent') else 'not spent'})")
        else:
            amt = "not recorded"
        tx = f"<code>{esc(a['tx'])}</code>" if a.get("tx") else "—"
        attempt_rows.append(
            "<tr><td>{date}</td><td><code>{run}</code></td>"
            "<td><code>{res}</code></td><td><code>{status}</code></td>"
            "<td>{amt}</td><td>{tx}</td></tr>".format(
                date=esc(a["date"] or "—"), run=esc(a["run_id"]),
                res=esc(a["resource"]), status=esc(a["status"]),
                amt=amt, tx=tx))

    last_purchase = (esc(s["last_purchase_date"]) if s["last_purchase_date"]
                     else "none recorded")
    body = f"""<p class="muted"><a href="../">← All seller grades</a> · <a href="../../tools/">Tools index</a></p>
<h1>Seller grade — {esc(s['seller'])}</h1>
<p class="pill">Delivery grade: {esc(grade_label(s))} — {esc(s['grade_basis'])}</p>
<p>This page is generated from the Verdict Row Test Purse's recorded
buyer-mode runs. It states only what those records show.</p>
{bought}
<h2>The record</h2>
<table>
<tr><th>Measure</th><th>Recorded value</th></tr>
<tr><td>Verified purchases (paid_verified)</td><td>{s['verified_purchases']}</td></tr>
<tr><td>Payment attempts</td><td>{s['payment_attempts']}</td></tr>
<tr><td>Recorded attempts, all outcomes</td><td>{s['attempts_total']}</td></tr>
<tr><td>Total spent (recorded amounts only)</td><td>{esc(money(s['total_spent_usd']))}</td></tr>
<tr><td>First recorded attempt</td><td>{esc(s['first_attempt_date'] or '—')}</td></tr>
<tr><td>Last recorded attempt</td><td>{esc(s['last_attempt_date'] or '—')}</td></tr>
<tr><td>Last verified purchase</td><td>{last_purchase}</td></tr>
</table>
<h2>Delivery grade — basis</h2>
<p>Grade: <strong>{esc(grade_label(s))}</strong>, from
<strong>{esc(s['grade_basis'])}</strong>. Sample size:
{s['payment_attempts']} payment attempt(s). Outcomes by status:</p>
<table>
<tr><th>Outcome</th><th>Count</th></tr>
{outcome_rows}
</table>
<p class="muted">Only settlement-verified deliveries (paid_verified)
count toward a grade; rejected, unknown-outcome and
settlement-unverified attempts count in the denominator, never the
numerator. Pre-payment outcomes (aborted_*, skipped_*) are recorded
above but are not payment attempts. A seller under the minimum
sample carries "Insufficient data", not a letter.</p>
<h2>Resources attempted</h2>
<table>
<tr><th>Resource</th><th>Attempts</th><th>Verified</th><th>Spent (recorded)</th><th>Outcomes</th></tr>
{''.join(resource_rows)}
</table>
<h2>Attempt records</h2>
<table>
<tr><th>Date</th><th>Run</th><th>Resource</th><th>Outcome</th><th>Amount (recorded)</th><th>Settlement tx</th></tr>
{''.join(attempt_rows)}
</table>
{belt_block(prefix)}
<p class="muted">Generated from the committed reciprocity ledger
(reciprocity_ledger.py, fleet-checker) from recorded Test-Purse run
data only. Contact: {esc(CONTACT)}.</p>
"""
    title = f"Seller grade: {s['seller']} — Verdict Row Patrol"
    desc = (f"Delivery grade for {s['seller']} from recorded Test-Purse "
            f"buyer-mode runs: {grade_label(s)} — {s['grade_basis']}; "
            f"{money(s['total_spent_usd'])} spent (recorded).")[:300]
    return route_pages.page_shell(
        title, desc, f"{BASE_URL}/sellers/{s['slug']}/", prefix, body)


def update_sitemap(slugs: list[str]) -> None:
    p = SITE / "sitemap.xml"
    existing = p.read_text() if p.exists() else ""
    urls = re.findall(r"<loc>([^<]+)</loc>", existing)
    for slug in slugs:
        u = f"{BASE_URL}/sellers/{slug}/"
        if u not in urls:
            urls.append(u)
    idx = f"{BASE_URL}/sellers/"
    if idx not in urls:
        urls.insert(5 if len(urls) >= 5 else len(urls), idx)
    items = "\n".join(f"  <url><loc>{esc(u)}</loc></url>" for u in urls)
    p.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                 f"{items}\n</urlset>\n")


def main() -> None:
    if not LEDGER_PATH.exists():
        raise SystemExit(f"missing reciprocity ledger: {LEDGER_PATH} — "
                         "run reciprocity_ledger.py build first")
    ledger = json.loads(LEDGER_PATH.read_text())
    sellers_dir = SITE / "sellers"
    sellers_dir.mkdir(parents=True, exist_ok=True)
    expected = set()
    for s in ledger["sellers"]:
        expected.add(s["slug"])
        out = sellers_dir / s["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(render_seller_page(s))
    (sellers_dir / "index.html").write_text(render_index(ledger))
    update_sitemap(sorted(expected))
    for child in sellers_dir.iterdir():
        if child.is_dir() and child.name not in expected:
            shutil.rmtree(child)
            print(f"sellers/{child.name} removed (no longer in ledger)")
    print(f"sellers: {len(expected)} seller grade pages + index regenerated")


if __name__ == "__main__":
    main()
