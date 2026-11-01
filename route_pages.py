#!/usr/bin/env python3
"""route_pages.py — per-route sheet pages for verdictrow.com (Block 1 Item 4).

Generates ONE static, search-indexable page per priced route in the
fleet's canonical route registry, plus a routes index, under:

    routes/index.html                              (all routes, by stall)
    routes/<stall-slug>-<route-slug>/index.html    (one page per route)

<route-slug> is the route path minus the leading "/v1/", with "/"
folded to "-" (e.g. stall-row /v1/fleet-check/pack ->
routes/stall-row-fleet-check-pack/). URLs are stable: they change only
if a stall slug or route path changes.

Every price, accept, URL and description is copied PROGRAMMATICALLY
from the canonical registry (route_registry.json in the fleet-checker
folder) — never hand-typed. Input/output shape summaries and the
worked request/response example pair come from each stall's committed
llms-full.txt (app/data/llms-full.txt in the stall's repo, the fleet's
canonical worked-example pack, itself generated from the registry +
served OpenAPI); worked examples are FIXTURE values and are labelled
as such on the page. Where llms-full.txt is unavailable for a stall,
the page falls back to the free sample body's top-level fields for the
output shape and omits the example pair rather than inventing one.

Last-change dates come from the fleet changelog store
(changelog-entries.json, the append-only store changelog_feed.py
renders): the newest entry naming that stall + route path. Routes with
no dated changelog entry show "—" — no date is invented.

Invoked by snapshot.py on every refresh so the pages regenerate
in-theme and are never orphaned; also runnable standalone.
Stdlib only. $0 spend: local files only, no network, never pays.
"""
import html
import json
import re
import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parent
CHECKER = Path(
    "~/workspace/goals/x402-fleet-integration-into-repeat-monitoring-loops/"
    "hidden_files/fleet-checker"
).expanduser()
REGISTRY_PATH = CHECKER / "route_registry.json"
CHANGELOG_PATH = CHECKER / "changelog-entries.json"

BASE_URL = "https://verdictrow.com"
CONTACT = "Ren, Verdict Row Patrol — patrol@verdictrow.com"
EXAMPLE_CAP = 6000  # chars per worked example on a page

STALL_DISPLAY = {
    "stall-row": "StallRow",
    "token-verdict": "Token Verdict",
    "route-verdict": "RouteVerdict",
    "list-smith": "ListSmith",
    "lock-smith": "LockSmith",
}
WORD_FIX = {"tx": "TX", "payto": "PayTo", "api": "API", "x402": "x402"}


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def stall_display(slug: str) -> str:
    return STALL_DISPLAY.get(slug, slug.replace("-", " ").title())


def route_slug(route: dict) -> str:
    path = route["path"]
    rest = path[len("/v1/"):] if path.startswith("/v1/") else path.strip("/")
    return rest.replace("/", "-")


def page_slug(stall_slug: str, route: dict) -> str:
    return f"{stall_slug}-{route_slug(route)}"


def route_name(route: dict) -> str:
    """Display name: the description's own 'Name — ...' prefix when the
    route carries one, else the title-cased path slug."""
    desc = route.get("description", "")
    m = re.match(r"^(.{2,40}?) — ", desc)
    if m and ":" not in m.group(1):
        return m.group(1).strip()
    words = []
    for w in route_slug(route).split("-"):
        words.append(WORD_FIX.get(w.lower(), w.capitalize()))
    return " ".join(words)


# --- worked examples + shapes from the stall's llms-full.txt -------------------

def parse_llms_full(stall: dict) -> dict:
    """Return {route_path: {input_shape, output_shape, req_example,
    resp_example}} parsed from the stall repo's app/data/llms-full.txt.
    Empty dict when the file is missing/unparseable (caller falls back)."""
    repo = stall.get("repo")
    if not repo:
        return {}
    p = Path(repo).expanduser() / "app" / "data" / "llms-full.txt"
    if not p.exists():
        return {}
    text = p.read_text(errors="replace")
    out = {}
    # Sections start with '### METHOD <resource-url> — <price>'; the pack
    # summary at the end repeats some routes as one-liners without the
    # shape/example block, so keep the FIRST full section per resource.
    for chunk in re.split(r"\n### ", text)[1:]:
        head, _, body = chunk.partition("\n")
        m = re.match(r"\S+ (\S+) — ", head)
        if not m:
            continue
        resource = m.group(1)
        path = resource[len(stall["base_url"]):] if resource.startswith(stall["base_url"]) else None
        if not path or path in out:
            continue
        if "Input shape:" not in body:
            continue
        entry = {}
        mi = re.search(r"^Input shape: (.+)$", body, re.M)
        mo = re.search(r"^Output shape: (.+)$", body, re.M)
        if mi:
            entry["input_shape"] = mi.group(1).strip()
        if mo:
            entry["output_shape"] = mo.group(1).strip()
        mr = re.search(
            r"Worked request example \(fixture\):\n```(?:json)?\n(.*?)```", body, re.S)
        if mr:
            entry["req_example"] = mr.group(1).strip()
        ms = re.search(
            r"Worked response example \(fixture\):\n```(?:json)?\n(.*?)```", body, re.S)
        if ms:
            entry["resp_example"] = ms.group(1).strip()
        out[path] = entry
    return out


def sample_output_fields(stall: dict, route: dict) -> str | None:
    """Fallback output shape: top-level fields of the route's free
    sample body in the stall repo (app/data/samples/<slug>.json)."""
    repo = stall.get("repo")
    if not repo:
        return None
    slug = route.get("sample", {}).get("sample_url", "").rsplit("/", 1)[-1]
    if not slug:
        return None
    p = Path(repo).expanduser() / "app" / "data" / "samples" / f"{slug}.json"
    if not p.exists():
        return None
    try:
        body = json.loads(p.read_text())
    except Exception:
        return None
    if isinstance(body, dict):
        return "type object; fields: " + ", ".join(sorted(body.keys()))
    return None


# --- chrome (same design as snapshot.py's, at routes/ depth) -------------------

def header(prefix: str) -> str:
    return f"""<header class="vr-header">
  <a class="vr-brand" href="{prefix}"><span class="vr-badge">VR</span>Verdict Row</a>
  <nav class="vr-nav">
    <a href="{prefix}tools/">Tools index</a>
    <a href="{prefix}routes/">Routes</a>
    <a href="{prefix}status/">Fleet status</a>
    <a href="{prefix}changelog/">Changelog</a>
    <a href="mailto:patrol@verdictrow.com">Contact</a>
  </nav>
</header>
"""


def footer(prefix: str) -> str:
    return f"""
<footer class="vr-footer">
  <span>Ren, Verdict Row Patrol — <a href="mailto:patrol@verdictrow.com">patrol@verdictrow.com</a></span>
  <span><a href="{prefix}">Home</a> · <a href="{prefix}tools/">Tools</a> · <a href="{prefix}routes/">Routes</a> · <a href="{prefix}status/">Status</a> · <a href="{prefix}changelog/">Changelog</a></span>
</footer>
"""


def page_shell(title: str, description: str, canonical: str, prefix: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
{header(prefix)}
{body}
{footer(prefix)}
</body>
</html>
"""


# --- page rendering --------------------------------------------------------------

def cap_example(text: str) -> tuple[str, bool]:
    if len(text) <= EXAMPLE_CAP:
        return text, False
    return text[:EXAMPLE_CAP].rstrip() + "\n…", True


def render_route_page(stall: dict, route: dict, details: dict,
                      last_change: str | None, registry_at: str) -> str:
    slug = page_slug(stall["slug"], route)
    name = route_name(route)
    sname = stall_display(stall["slug"])
    prefix = "../../"
    sample_url = stall["base_url"] + route.get("sample", {}).get("sample_url", "")
    surfaces = stall.get("surfaces", {})
    llms_full_url = stall["base_url"] + "/llms-full.txt"

    accepts_rows = []
    for a in route.get("accepts", []):
        accepts_rows.append(
            "<tr><td>{scheme}</td><td><code>{network}</code></td>"
            "<td>{amount}</td><td><code>{asset}</code></td>"
            "<td><code>{payto}</code></td><td>{timeout}</td></tr>".format(
                scheme=esc(a.get("scheme", "")),
                network=esc(a.get("network", "")),
                amount=esc(a.get("amount", "")),
                asset=esc(a.get("asset", "")),
                payto=esc(a.get("payTo", "")),
                timeout=esc(a.get("maxTimeoutSeconds", "")),
            )
        )
    dual = route.get("dual_accept") or len(route.get("accepts", [])) > 1
    dual_note = (
        "<p>This route is <strong>dual-accept</strong>: it takes payment on "
        "more than one network — every accepted rail is listed below.</p>"
        if dual else ""
    )

    shapes = ""
    if details.get("input_shape") or details.get("output_shape"):
        shapes = "<h2>Input &amp; output shape</h2>\n"
        if details.get("input_shape"):
            shapes += f"<p><strong>Input:</strong> {esc(details['input_shape'])}</p>\n"
        if details.get("output_shape"):
            shapes += f"<p><strong>Output:</strong> {esc(details['output_shape'])}</p>\n"
    elif details.get("output_fields"):
        shapes = (
            "<h2>Input &amp; output shape</h2>\n"
            f"<p><strong>Output:</strong> {esc(details['output_fields'])} "
            "(fields of the route's free sample response). Full input/output "
            "schemas are in the stall's discovery document, linked below.</p>\n"
        )

    examples = ""
    if details.get("req_example") or details.get("resp_example"):
        examples = (
            "<h2>Worked example (fixture)</h2>\n"
            "<p class=\"muted\">Fixture values from the stall's published "
            "worked examples — real shapes, not live data. Buy the route "
            "for live results.</p>\n"
        )
        for label, key in (("Request", "req_example"), ("Response", "resp_example")):
            if details.get(key):
                text, truncated = cap_example(details[key])
                examples += f"<h3>{label}</h3>\n<pre><code>{esc(text)}</code></pre>\n"
                if truncated:
                    examples += (
                        "<p class=\"muted\">Example truncated on this page — "
                        f"the full example is in the stall's <a href=\"{esc(llms_full_url)}\">"
                        "llms-full.txt</a>.</p>\n"
                    )

    tags = ", ".join(route.get("tags", []))
    last_change_html = esc(last_change) if last_change else "—"
    body = f"""<p class="muted"><a href="../">← All routes</a> · <a href="../../tools/">Tools index</a></p>
<h1>{esc(name)}</h1>
<p><strong>{esc(sname)}</strong> · <code>{esc(route['method'])} {esc(route['resource'])}</code></p>
<p class="pill">{esc(route['price_display'])} USDC per call · {esc(route['amount_units_base'])} atomic units (Base accept)</p>
<p>{esc(route['description'])}</p>
<h2>Payment terms</h2>
{dual_note}
<table>
<tr><th>Scheme</th><th>Network</th><th>Amount (atomic units)</th><th>Asset</th><th>payTo</th><th>Max timeout (s)</th></tr>
{''.join(accepts_rows)}
</table>
<p>Price: <strong>{esc(route['price_display'])}</strong> ({esc(route['price_usd'])} USD) ·
payTo <code>{esc(route['pay_to'])}</code> · x402 exact scheme — an unpaid call
returns HTTP 402 with the payment challenge; no API key, no signup.</p>
<p>Last change: <strong>{last_change_html}</strong>{'' if last_change else ' (no dated entry for this route in the fleet changelog store)'}</p>
{shapes}
{examples}
<h2>Free surfaces &amp; documents</h2>
<ul>
<li><a href="{esc(sample_url)}">Free sample response</a> for this route (source: {esc(route.get('sample', {}).get('source', ''))}; labelled in-band sample=true, live=false)</li>
<li><a href="{esc(surfaces.get('stability_manifest', ''))}">{esc(sname)} stability manifest</a> — signed, pins this route's price and terms</li>
<li><a href="{esc(surfaces.get('discovery', ''))}">{esc(sname)} discovery document</a> (/.well-known/x402)</li>
<li><a href="{esc(llms_full_url)}">{esc(sname)} llms-full.txt</a> — full route docs with worked examples</li>
<li><a href="{esc(surfaces.get('openapi', ''))}">{esc(sname)} OpenAPI document</a></li>
<li><a href="{esc(surfaces.get('samples_index', ''))}">All free samples on {esc(sname)}</a></li>
</ul>
<p class="muted">Tags: {esc(tags)}. Page generated from the canonical fleet
route registry (registry generated {esc(registry_at)}) by route_pages.py —
prices and terms are copied programmatically, never hand-typed. Contact:
Ren, Verdict Row Patrol — <a href="mailto:patrol@verdictrow.com">patrol@verdictrow.com</a>.</p>
"""
    title = f"{name} — {sname} · Verdict Row"
    desc = (f"{name} ({route['method']} {route['path']}) on {sname}: "
            f"{route['price_display']} USDC per call via x402. "
            + route["description"])[:300]
    return page_shell(title, desc, f"{BASE_URL}/routes/{slug}/", prefix, body)


def render_index(stalls_render: list, total: int, registry_at: str) -> str:
    prefix = "../"
    sections = []
    for sname, stall_slug, rows in stalls_render:
        trs = []
        for r in rows:
            trs.append(
                "<tr><td><a href=\"{slug}/\">{name}</a></td>"
                "<td><code>{method} {path}</code></td><td>{price}</td>"
                "<td>{changed}</td>"
                "<td><a href=\"{sample}\">sample</a></td></tr>".format(
                    slug=esc(r["slug"]), name=esc(r["name"]),
                    method=esc(r["method"]), path=esc(r["path"]),
                    price=esc(r["price"]), changed=esc(r["changed"] or "—"),
                    sample=esc(r["sample"]),
                )
            )
        sections.append(
            f"<h2>{esc(sname)}</h2>\n<table>\n"
            "<tr><th>Route</th><th>Endpoint</th><th>Price</th>"
            "<th>Last change</th><th>Free sample</th></tr>\n"
            + "\n".join(trs) + "\n</table>"
        )
    body = f"""<h1>Route sheets — every priced route on the row</h1>
<p>One static sheet per priced route: exact price and payment terms,
input/output shape, a fixture worked example, the free sample, and the
stall's stability manifest. {total} priced routes across 5 stalls,
generated from the canonical fleet route registry (registry generated
{esc(registry_at)}) — prices are copied programmatically, never
hand-typed. The <a href="../tools/">tools index</a> carries the same
fleet in index form.</p>
{''.join(sections)}
<p class="muted">Contact: {esc(CONTACT)}.</p>
"""
    return page_shell(
        "Route sheets — Verdict Row Patrol",
        f"Per-route sheets for all {total} priced x402 routes on Verdict Row: "
        "price, payment terms, shapes, worked examples, free samples and "
        "stability manifests, grouped by stall.",
        f"{BASE_URL}/routes/", prefix, body)


def render_sitemap(slugs: list[str]) -> str:
    urls = [f"{BASE_URL}/", f"{BASE_URL}/tools/", f"{BASE_URL}/status/",
            f"{BASE_URL}/changelog/", f"{BASE_URL}/routes/"]
    urls += [f"{BASE_URL}/routes/{s}/" for s in slugs]
    items = "\n".join(f"  <url><loc>{esc(u)}</loc></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{items}\n</urlset>\n")


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text())
    registry_at = str(registry.get("generated_at", ""))
    last_change: dict[tuple[str, str], str] = {}
    if CHANGELOG_PATH.exists():
        for e in json.loads(CHANGELOG_PATH.read_text()):
            if e.get("route") and e.get("stall") and e.get("at"):
                key = (e["stall"], e["route"])
                day = str(e["at"])[:10]
                if key not in last_change or day > last_change[key]:
                    last_change[key] = day

    routes_dir = SITE / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    index_data = []
    total = 0
    for stall in registry["stalls"]:
        details_by_path = parse_llms_full(stall)
        rows = []
        for route in stall["routes"]:
            slug = page_slug(stall["slug"], route)
            expected.add(slug)
            total += 1
            details = dict(details_by_path.get(route["path"], {}))
            if not details.get("output_shape"):
                fields = sample_output_fields(stall, route)
                if fields:
                    details["output_fields"] = fields
            changed = last_change.get((stall["slug"], route["path"]))
            page = render_route_page(stall, route, details, changed, registry_at)
            out = routes_dir / slug
            out.mkdir(parents=True, exist_ok=True)
            (out / "index.html").write_text(page)
            rows.append({
                "slug": slug, "name": route_name(route),
                "method": route["method"], "path": route["path"],
                "price": route["price_display"], "changed": changed,
                "sample": stall["base_url"] + route.get("sample", {}).get("sample_url", ""),
            })
        index_data.append((stall_display(stall["slug"]), stall["slug"], rows))

    (routes_dir / "index.html").write_text(render_index(index_data, total, registry_at))
    (SITE / "sitemap.xml").write_text(render_sitemap(sorted(expected)))

    # Never orphan: drop route dirs from earlier registry states.
    for child in routes_dir.iterdir():
        if child.is_dir() and child.name not in expected:
            shutil.rmtree(child)
            print(f"routes/{child.name} removed (no longer in registry)")
    print(f"routes: {total} route pages + index regenerated")


if __name__ == "__main__":
    main()
