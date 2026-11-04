#!/usr/bin/env python3
"""fleet_check_framework_pack.py — Fleet Check Framework Pack
descriptor for verdictrow.com (Next-20 Integration Builds, Item 13).

Publishes:

    fleet-check-framework-pack.json

describing the Fleet Check pack for agent-framework builders: the
buy / run / status endpoints, the pack's price, credits and renewal
cycle, and the `framework_log` run-log format every Fleet Check
delivery now carries (with a fixture example, marked as fixture).

NOTHING here is hand-typed where a source of truth exists:

  * pack price / credits / TTL and the single-sweep price are parsed
    (AST) from the StallRow repo's enforcing constants —
    app/services/recheck.py (FLEET_CHECK_PACK_*) and
    app/services/fleetcheck.py (ONE_SHOT_PRICE_UNITS);
  * endpoint URLs and payment terms (network, asset, payTo) come
    from the canonical fleet route registry, the same source the
    function-calling pack is generated from — and the generator
    REFUSES to emit a descriptor whose parsed pack price disagrees
    with the registry's amount for the pack route.

Invoked by snapshot.py on every refresh so the descriptor
regenerates and is never orphaned; also runnable standalone.
Stdlib only. $0 spend: local files only, no network, never pays.
"""
import ast
import json
from pathlib import Path

SITE = Path(__file__).resolve().parent
STALL_ROW = Path("~/workspace/stall-row").expanduser()
CHECKER = Path(
    "~/workspace/goals/x402-fleet-integration-into-repeat-monitoring-loops/"
    "hidden_files/fleet-checker"
).expanduser()
REGISTRY_PATH = CHECKER / "route_registry.json"

BASE_URL = "https://verdictrow.com"
CONTACT = "Ren, Verdict Row Patrol — patrol@verdictrow.com"


def parse_constants(path: Path, names: set[str]) -> dict[str, int]:
    """Read simple `NAME = <int literal>` assignments from a module
    WITHOUT importing it (the stall's runtime deps are not the
    site's). Fails loudly when a name is missing — a descriptor
    built on a guessed number is worse than none."""
    tree = ast.parse(path.read_text())
    found: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and target.id in names
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
            ):
                found[target.id] = node.value.value
    missing = names - found.keys()
    if missing:
        raise SystemExit(f"{path}: constants not found: {sorted(missing)}")
    return found


def registry_route(registry: dict, path: str) -> dict:
    for stall in registry.get("stalls", []):
        for route in stall.get("routes", []):
            if route.get("path") == path:
                return route
    raise SystemExit(f"route {path} not in the canonical registry")


def origin_of(resource: str) -> str:
    return resource.rsplit("/v1/", 1)[0]


def fixture_framework_log() -> list[dict]:
    """Fixture framework_log entries — synthetic example data in the
    exact entry shape StallRow's fleetcheck.framework_log_entry
    emits. Marked as fixture by the caller; never live data."""
    return [
        {
            "tool": "fleet_check_route_probe",
            "action": "fleet_check_route_probe",
            "resource": "https://service.example.com/v1/endpoint",
            "verdict": "OK",
            "defect": None,
            "defects": [],
            "http_status": 402,
            "message": (
                "fleet_check_route_probe "
                "https://service.example.com/v1/endpoint: OK — answers "
                "402 with a parseable challenge, no defect found"
            ),
            "checked_at": "2026-01-01T00:00:00Z",
        },
        {
            "tool": "fleet_check_route_probe",
            "action": "fleet_check_route_probe",
            "resource": "https://service.example.com/v1/broken",
            "verdict": "DOWN",
            "defect": "server_error",
            "defects": ["server_error"],
            "http_status": 500,
            "message": (
                "fleet_check_route_probe "
                "https://service.example.com/v1/broken: DOWN "
                "(server_error: target returned HTTP 500)"
            ),
            "checked_at": "2026-01-01T00:00:00Z",
        },
    ]


def build_descriptor() -> dict:
    pack_consts = parse_constants(
        STALL_ROW / "app" / "services" / "recheck.py",
        {
            "FLEET_CHECK_PACK_CREDITS",
            "FLEET_CHECK_PACK_PRICE_UNITS",
            "FLEET_CHECK_PACK_TTL_DAYS",
        },
    )
    sweep_consts = parse_constants(
        STALL_ROW / "app" / "services" / "fleetcheck.py",
        {"ONE_SHOT_PRICE_UNITS"},
    )
    registry = json.loads(REGISTRY_PATH.read_text())
    pack_route = registry_route(registry, "/v1/fleet-check/pack")
    sweep_route = registry_route(registry, "/v1/fleet-check")
    origin = origin_of(pack_route["resource"])

    # Drift guard: the parsed enforcing constants must agree with
    # the registry's published amounts for both routes.
    if str(pack_consts["FLEET_CHECK_PACK_PRICE_UNITS"]) != str(
        pack_route["amount_units_base"]
    ):
        raise SystemExit(
            "pack price drift: recheck.py FLEET_CHECK_PACK_PRICE_UNITS="
            f"{pack_consts['FLEET_CHECK_PACK_PRICE_UNITS']} but the "
            f"registry says {pack_route['amount_units_base']}"
        )
    if str(sweep_consts["ONE_SHOT_PRICE_UNITS"]) != str(
        sweep_route["amount_units_base"]
    ):
        raise SystemExit(
            "single-sweep price drift: fleetcheck.py "
            f"ONE_SHOT_PRICE_UNITS={sweep_consts['ONE_SHOT_PRICE_UNITS']} "
            f"but the registry says {sweep_route['amount_units_base']}"
        )

    price_units = pack_consts["FLEET_CHECK_PACK_PRICE_UNITS"]
    sweep_units = sweep_consts["ONE_SHOT_PRICE_UNITS"]
    credits = pack_consts["FLEET_CHECK_PACK_CREDITS"]
    ttl_days = pack_consts["FLEET_CHECK_PACK_TTL_DAYS"]
    constants = registry.get("constants", {})

    return {
        "kind": "verdict-row-fleet-check-framework-pack/v1",
        "name": "Fleet Check Framework Pack",
        "generated_by": (
            "verdictrow-site/fleet_check_framework_pack.py from the "
            "StallRow FLEET_CHECK_PACK_* constants (parsed from "
            "app/services/recheck.py + fleetcheck.py) and the "
            "canonical fleet route registry"
        ),
        "registry_generated_at": registry.get("generated_at"),
        "contact": CONTACT,
        "pack": {
            "price_units": price_units,
            "price_usd": f"${price_units / 1_000_000:.2f}",
            "credits": credits,
            "credits_unit": "one credit = one whole-fleet sweep of the pack's fixed fleet definition, never one route",
            "ttl_days": ttl_days,
            "renewal": {
                "renewal_cycle_days": ttl_days,
                "renewal_price_units": price_units,
                "renewal_price_usd": f"${price_units / 1_000_000:.2f}",
                "credits_per_pack": credits,
                "how": "Buy a new pack at POST /v1/fleet-check/pack; deliveries carry these same terms in their `renewal` section, with days_remaining computed from the pack's real expiry.",
            },
        },
        "single_sweep": {
            "price_units": sweep_units,
            "price_usd": f"${sweep_units / 1_000_000:.2f}",
        },
        "payment": {
            "protocol": "x402 v2 (exact scheme)",
            "network": constants.get("base_network"),
            "asset": constants.get("base_asset_usdc"),
            "pay_to": constants.get("pay_to"),
            "note": "The pack and single sweep are paid via x402; pack runs spend pack credits and the status read is free — neither makes an x402 payment.",
        },
        "endpoints": {
            "buy_pack": {
                "method": "POST",
                "url": pack_route["resource"],
                "price_usd": f"${price_units / 1_000_000:.2f}",
                "body": "resources and/or origins (the pack's FIXED fleet definition), optional webhook_url, email, heartbeat, interval_s (300-86400)",
                "returns": "pack_id, definition, credits_total/credits_remaining, expires_at, renewal terms",
            },
            "run_sweep": {
                "method": "POST",
                "url": f"{origin}/v1/fleet-check/run",
                "price_usd": "one pack credit",
                "body": "pack_id",
                "returns": "summary, run-over-run diff, credits_remaining, framework_log, renewal terms; new failures and recoveries are also pushed to the pack's webhook",
            },
            "status": {
                "method": "POST",
                "url": f"{origin}/v1/fleet-check/status",
                "price_usd": "free",
                "body": "pack_id",
                "returns": "pack (definition, credits, expiry, renewal terms), latest sweep table, that sweep's framework_log, webhook delivery records",
            },
            "single_sweep": {
                "method": "POST",
                "url": sweep_route["resource"],
                "price_usd": f"${sweep_units / 1_000_000:.2f}",
                "body": "resources and/or origins",
                "returns": "the sweep table (resources, origins, summary) plus framework_log",
            },
        },
        "framework_log": {
            "where": "Every Fleet Check delivery (single sweep, pack run, pack status) carries a top-level `framework_log` list, additive to the original delivery fields.",
            "shape": "One structured entry per probed resource, in sweep order — shaped so an AgentKit / LangChain-style runner can drop the entries into its own run log verbatim.",
            "entry_fields": {
                "tool": "always 'fleet_check_route_probe'",
                "action": "same as tool (frameworks that key run logs by action)",
                "resource": "the probed resource URL",
                "verdict": "OK | DEGRADED | DOWN",
                "defect": "the first defect's code (e.g. server_error, amount_mismatch, payto_mismatch, no_402, challenge_undecodable, unreachable), or null when OK",
                "defects": "all defect codes for the resource (possibly empty)",
                "http_status": "HTTP status the unpaid probe met, or null when unreachable",
                "message": "one-line human-readable summary of the entry",
                "checked_at": "ISO timestamp of the sweep",
            },
            "fixture_example": {
                "fixture": True,
                "note": "Synthetic example entries in the live format — fixture data, not a real sweep.",
                "framework_log": fixture_framework_log(),
            },
        },
        "framework_surfaces": {
            "agentkit": {
                "package": "token-verdict-agentkit (npm, prepared — see repo)",
                "repo": "https://github.com/QuincyGB/token-verdict-tools/tree/main/agentkit",
                "actions": [
                    "buy_fleet_check_pack ($5.00, hand-written — above the <=$0.05 pack-generated cap)",
                    "fleet_check_sweep ($0.10, hand-written)",
                    "run_fleet_check_sweep (one pack credit)",
                ],
                "note": "The provider's other 24 actions are generated from the function-calling pack (routes <= $0.05); the Fleet Check actions are separate hand-written actions because Fleet Check is priced above that cap.",
            },
            "inspector_sdk": {
                "package": "@quincygb/verdict-row-inspector (TypeScript) / verdict-row-inspector (Python)",
                "repo": "https://github.com/QuincyGB/verdict-row-inspector",
                "helpers": [
                    "buyFleetCheckPack / buy_fleet_check_pack",
                    "fleetCheckSweep / fleet_check_sweep",
                    "runFleetCheckSweep / run_fleet_check_sweep",
                    "fleetCheckStatus / fleet_check_status",
                    "frameworkLogEntries + frameworkLogLines / framework_log_entries + framework_log_lines",
                ],
            },
            "function_calling_pack": f"{BASE_URL}/function-tools.json",
            "descriptor": f"{BASE_URL}/fleet-check-framework-pack.json",
        },
    }


def main() -> None:
    descriptor = build_descriptor()
    (SITE / "fleet-check-framework-pack.json").write_text(
        json.dumps(descriptor, indent=2) + "\n"
    )
    pack = descriptor["pack"]
    print(
        "fleet-check framework pack: "
        f"{pack['price_usd']} / {pack['credits']} sweeps / "
        f"{pack['ttl_days']}d -> fleet-check-framework-pack.json"
    )


if __name__ == "__main__":
    main()
