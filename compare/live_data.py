"""Best-effort live data pull from public insurer product pages via Firecrawl.

Scope, honestly stated: Thai insurers do not publish a structured premium API.
Official product pages show room rate / coverage-limit / deductible benefit
tables (static content), but the *exact* annual premium almost always needs an
age+gender quote calculator that this cannot drive. So a live pull reliably
refreshes plan tiers, room rates, coverage limits and deductible options; any
premium figure it finds is one example off the page (often for a single
age/gender shown as marketing copy), not a real quote, and is labelled as such
everywhere it is displayed. Rows pulled this way are kept SEPARATE from the
synthetic catalog in data.py rather than overwriting it, so provenance is
always visible to whoever is reading the comparison.

Only HEALTH has a configured source list right now, because that is where
public pages actually publish structured tier tables (and it is the category
the deductible analyzer needs). Investment / life / retirement premiums for
underwritten products are essentially never public, so no sources are
registered for them yet -- the UI says so rather than pretending otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "live_cache.json")
API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev").rstrip("/")

_BIN_DIRS = [
    "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/opt/local/bin",
    os.path.expanduser("~/.local/bin"), os.path.expanduser("~/.npm-global/bin"),
    os.path.expanduser("~/.volta/bin"), os.path.expanduser("~/.bun/bin"),
    os.path.expanduser("~/.yarn/bin"), os.path.expanduser("~/n/bin"),
]

SCHEMA = {
    "type": "object",
    "properties": {
        "plans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "plan_name": {"type": "string"},
                    "room_rate_per_day_thb": {"type": "number"},
                    "annual_coverage_limit_thb": {"type": "number"},
                    "deductible_thb": {"type": "number"},
                    "annual_premium_thb": {"type": "number"},
                },
            },
        },
        "product_summary": {"type": "string"},
    },
}
EXTRACT_PROMPT = (
    "Extract each health insurance plan/tier shown on this page. For each "
    "tier give: plan name, room rate per day (ค่าห้อง) "
    "in THB, annual coverage limit in THB, deductible / "
    "ความรับผิดส่วนแรก "
    "in THB (0 if the plan has no deductible option), and an annual premium "
    "in THB only if one is explicitly shown on the page. One-sentence Thai "
    "product_summary."
)

# Verified via web search 2026-08-28 -- real, currently-live product pages
# with static benefit tables. ไทยประกันชีวิต has no confirmed public source
# yet, so it is deliberately absent rather than guessed.
HEALTH_SOURCES = [
    {"insurer": "AIA ประเทศไทย", "url": "https://www.aia.co.th/th/our-products/health/aia-health-saver"},
    {"insurer": "เมืองไทยประกันชีวิต (MTL)", "url": "https://www.muangthai.co.th/th/health-insurance/extra-care-plus"},
    {"insurer": "พรูเด็นเชียล ประเทศไทย", "url": "https://online.prudential.co.th/ais/prueeasyhealthextra"},
    {"insurer": "เอฟดับบลิวดี ประกันชีวิต (FWD)", "url": "https://www.fwd.co.th/th/health-insurance/easy-e-health/"},
    {"insurer": "กรุงไทย-แอกซ่า ประกันชีวิต", "url": "https://www.krungthai-axa.co.th/th/products/health-insurance-and-hospital-income/ihealthy-ultra"},
    {"insurer": "อลิอันซ์ อยุธยา ประกันชีวิต", "url": "https://www.allianz.co.th/th_TH/health/lump-sum/ultracare.html"},
    {"insurer": "กรุงเทพประกันชีวิต", "url": "https://www.bangkoklife.com/online/th/product/completehealth"},
]
# category -> source list; only health is populated (see module docstring)
SOURCES_BY_CATEGORY = {
    "health": HEALTH_SOURCES,
    "investment": [],
    "life": [],
    "retirement": [],
}


@dataclass
class FetchResult:
    insurer: str
    url: str
    ok: bool
    plans: list = field(default_factory=list)
    product_summary: str = ""
    error: str = ""
    fetched_at: float = 0.0


def firecrawl_bin() -> Optional[str]:
    override = os.getenv("FIRECRAWL_BIN", "").strip()
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override
    found = shutil.which("firecrawl")
    if found:
        return found
    for directory in _BIN_DIRS:
        candidate = os.path.join(directory, "firecrawl")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
            return candidate
    return None


def backend() -> str:
    if os.getenv("FIRECRAWL_API_KEY", "").strip():
        return "http"
    if firecrawl_bin():
        return "cli"
    return "http"


def _scrape_cli(url: str, timeout: int = 90) -> dict:
    binpath = firecrawl_bin()
    proc = subprocess.run(
        [binpath, "scrape", url, "-f", "json", "--schema", json.dumps(SCHEMA)],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "firecrawl CLI failed").strip()[:300])
    payload = json.loads(proc.stdout)
    return payload.get("json", {})


def _scrape_http(url: str, timeout: int = 90) -> dict:
    body = {
        "url": url,
        "formats": ["json"],
        "jsonOptions": {"schema": SCHEMA, "prompt": EXTRACT_PROMPT},
        "onlyMainContent": True,
    }
    req = urllib.request.Request(
        f"{API_URL}/v2/scrape",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:200]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)[:200]) from exc
    data = payload.get("data", {})
    return data.get("json", {})


def _clean_number(v):
    """0 from this extractor means 'not found' for these fields, not a real zero."""
    return v if v else None


def fetch_one(insurer: str, url: str) -> FetchResult:
    try:
        result = _scrape_cli(url) if backend() == "cli" else _scrape_http(url)
        plans = result.get("plans") or []
        for p in plans:
            p["room_rate_per_day_thb"] = _clean_number(p.get("room_rate_per_day_thb"))
            p["annual_coverage_limit_thb"] = _clean_number(p.get("annual_coverage_limit_thb"))
            p["annual_premium_thb"] = _clean_number(p.get("annual_premium_thb"))
            p["deductible_thb"] = p.get("deductible_thb") or 0  # 0 deductible is a real, common value
        # drop plans where nothing useful came back at all
        plans = [p for p in plans if p["room_rate_per_day_thb"] or p["annual_coverage_limit_thb"]]
        # defensive: an identical premium repeated across every tier is almost
        # always the page's single marketing example being reused by the
        # extractor, not a real per-tier quote -- drop it rather than show a
        # wrong number with a straight face.
        premiums = {p["annual_premium_thb"] for p in plans if p["annual_premium_thb"]}
        if len(plans) > 1 and len(premiums) <= 1:
            for p in plans:
                p["annual_premium_thb"] = None
                p["premium_note"] = "พบเบี้ยตัวอย่างเดียวบนหน้าเว็บ ไม่แยกตามแผน"
        return FetchResult(
            insurer=insurer, url=url, ok=True, plans=plans,
            product_summary=result.get("product_summary", ""),
            fetched_at=time.time(),
        )
    except Exception as exc:  # noqa: BLE001 -- surfaced to the UI, not swallowed
        return FetchResult(insurer=insurer, url=url, ok=False, error=str(exc), fetched_at=time.time())


def fetch_category(category: str, progress_cb=None) -> list[FetchResult]:
    sources = SOURCES_BY_CATEGORY.get(category, [])
    results = []
    for i, src in enumerate(sources):
        if progress_cb:
            progress_cb(i, len(sources), src["insurer"])
        results.append(fetch_one(src["insurer"], src["url"]))
    return results


def load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_results(category: str, results: list[FetchResult]):
    cache = load_cache()
    cache[category] = {
        "fetched_at": time.time(),
        "results": [
            dict(insurer=r.insurer, url=r.url, ok=r.ok, plans=r.plans,
                 product_summary=r.product_summary, error=r.error, fetched_at=r.fetched_at)
            for r in results
        ],
    }
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def live_rows(category: str) -> list[dict]:
    """Flatten cached live results into product-catalog-shaped rows."""
    cache = load_cache().get(category)
    if not cache:
        return []
    rows = []
    for r in cache["results"]:
        if not r["ok"]:
            continue
        for plan in r["plans"]:
            rows.append(dict(
                category=category,
                insurer=r["insurer"],
                product_name=plan.get("plan_name") or "(ไม่พบชื่อแผน)",
                deductible_thb=plan.get("deductible_thb") or 0,
                annual_premium=plan.get("annual_premium_thb"),
                ipd_annual_limit=plan.get("annual_coverage_limit_thb"),
                room_rate_per_day=plan.get("room_rate_per_day_thb"),
                data_source="live",
                source_url=r["url"],
                fetched_at=r["fetched_at"],
            ))
    return rows


def cache_status(category: str) -> Optional[dict]:
    return load_cache().get(category)
