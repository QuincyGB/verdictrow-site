# verdictrow-site

Static site for **Verdict Row Patrol** — prepared for verdictrow.com
(DNS is handled separately; this repo is GitHub Pages-ready and makes no
DNS changes).

Pages, all generated from the same fleet generators the stalls use
(`tools_index.py`, `fleet_status.py`, `changelog_feed.py` in the
x402 fleet-checker folder, outputs staged in `stall-row/app/data/`):

- `/` — who the Patrol is, contact `patrol@verdictrow.com`
- `/tools/` — the fleet tools index snapshot (+ `tools.json`)
- `/status/` — the fleet status snapshot (+ `status.json`)
- `/changelog/` — the changelog rendered from the generated feed
  (+ `changelog.atom`, `changelog.json`)

Refresh the snapshot with `python3 snapshot.py`, then commit + push.
The standing weekly catalogue-freshness job and the fleet-route-checker
keep the underlying generator outputs current.
