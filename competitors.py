# competitors.py
import os
import re
from urllib.parse import urlparse, urlencode, parse_qs, unquote
import requests
from bs4 import BeautifulSoup

from shopify_insights import get_brand_context, is_shopify_site  # same-folder import

UA = {"User-Agent": "Mozilla/5.0 (BrandInsightsBot/1.1)"}
TIMEOUT = 15
# Enable verbose logs by running in the server terminal:  export COMP_DEBUG=1
DEBUG = os.getenv("COMP_DEBUG", "0") == "1"


# -------------------------- logging helper --------------------------

def _log(*args):
    if DEBUG:
        print("[competitors]", *args)


# -------------------------- small utils --------------------------

def _normalize_root(url: str) -> str:
    """Return https://host only; add https if missing. Return '' if invalid."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    if not p.netloc:  # invalid like https:///
        return ""
    return f"{p.scheme}://{p.netloc}"

def _is_noise_domain(root: str) -> bool:
    """Filter out obvious non-store domains commonly seen in search results."""
    host = urlparse(root).netloc
    bad = (
        "shopify.com", "help.shopify", "apps.shopify",
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "pinterest.com", "linkedin.com",
        "wikipedia.org", "reddit.com", "medium.com",
        "tiktok.com", "google.com", "duckduckgo.com"
    )
    # NOTE: for testing you can loosen this by removing the startswith clause.
    return (not host) or any(b in host for b in bad) or host.startswith(("blog.", "docs.", "support.", "help."))

def _unwrap_ddg(href: str) -> str:
    """
    DuckDuckGo wraps external links as /l/?kh=-1&uddg=<ENCODED_URL>.
    Return the real URL if present; otherwise return original.
    """
    try:
        # relative wrapper
        if href.startswith("/l/?"):
            qs = parse_qs(urlparse(href).query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])
        # absolute wrapper
        u = urlparse(href)
        if u.netloc.endswith("duckduckgo.com") and u.path.startswith("/l/"):
            qs = parse_qs(u.query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])
    except Exception:
        pass
    return href


# -------------------------- HTML extraction --------------------------

def _extract_result_links(html: str):
    """
    Use BeautifulSoup to be resilient to DDG markup changes.
    Returns a de-duplicated list of absolute URLs (strings).
    """
    soup = BeautifulSoup(html, "lxml")
    links = []

    # Primary result links commonly use .result__a; keep a broad fallback (a[href])
    anchors = soup.select("a.result__a, a[href]")
    _log("anchors found:", len(anchors))

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        href = _unwrap_ddg(href)
        if href.startswith("http"):
            links.append(href)

    # Fallback: raw URLs inside text snippets (rare but helps)
    for txt in soup.stripped_strings:
        for m in re.findall(r"https?://[^\s)\"'>]+", txt):
            links.append(m)

    # de-dupe while preserving order
    seen, uniq = set(), []
    for h in links:
        if h in seen:
            continue
        seen.add(h)
        uniq.append(h)

    _log("extracted links (deduped):", len(uniq))
    return uniq

def _promote_storeish_links(hrefs):
    """
    Prefer links that look like store pages (products/collections/cart),
    then fall back to everything else.
    """
    storeish, others = [], []
    for h in hrefs:
        if any(p in h for p in ("/products/", "/collections/", "/cart", "/pages/")):
            storeish.append(h)
        else:
            others.append(h)
    ordered = storeish + others
    _log("storeish first (top 10 shown):", ordered[:10])
    return ordered


# -------------------------- DDG fetch --------------------------

def _ddg_search_pages(seed_root: str):
    """
    Yield HTML result pages for different query phrasings to improve recall.
    """
    queries = [
        f"Shopify brands similar to {seed_root}",
        f"stores like {seed_root} Shopify",
        f"{seed_root} competitors Shopify",
        f"site:.myshopify.com brands similar to {seed_root}",  # extra hint
    ]
    for q in queries:
        url = f"https://duckduckgo.com/html/?{urlencode({'q': q})}"
        _log("query:", q)
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            r.raise_for_status()
            yield r.text
        except Exception as e:
            _log("ddg fetch failed:", e)
            continue


# -------------------------- discovery --------------------------

def discover_competitors(seed_url: str, max_items: int = 3, loose: bool = False):
    """
    Best-effort competitor discovery via DuckDuckGo.
    - Parse links from multiple queries
    - Normalize to roots, filter obvious non-store 'noise'
    - STRICT: return only Shopify-like roots (via is_shopify_site)
    - LOOSE: return top non-noise roots if strict found nothing
    """
    seed_root = _normalize_root(seed_url)
    if not seed_root:
        _log("Invalid seed URL:", seed_url)
        return []

    _log("seed root:", seed_root)
    strict, loose_pool, seen = [], [], set()

    for html in _ddg_search_pages(seed_root):
        hrefs = _extract_result_links(html)
        _log("raw extracted:", hrefs[:10])
        hrefs = _promote_storeish_links(hrefs)

        for href in hrefs:
            root = _normalize_root(href)
            if not root:
                _log("skip invalid root:", href)
                continue
            if root == seed_root:
                _log("skip same as seed:", root)
                continue
            if root in seen:
                _log("skip already seen:", root)
                continue
            if _is_noise_domain(root):
                _log("skip noise domain:", root)
                continue

            seen.add(root)

            ok, why = is_shopify_site(root)
            _log("candidate:", root, "| shopify_like:", ok, "| reason:", why)

            if ok:
                strict.append(root)
                if len(strict) >= max_items:
                    _log("STRICT reached limit:", strict)
                    return strict
            else:
                loose_pool.append(root)

    if strict:
        _log("returning STRICT:", strict)
        return strict

    if loose:
        ret = loose_pool[:max_items]
        _log("STRICT empty; returning LOOSE:", ret)
        return ret

    _log("STRICT empty and loose=False; returning [].")
    return []


# -------------------------- contexts --------------------------

def competitor_contexts(seed_url: str, limit: int = 3, loose: bool = False):
    """
    Return contexts for discovered competitors.
    - In strict mode: double-check Shopify-ness before scraping.
    - In loose mode: scrape best-effort roots (some may fail).
    """
    results = []
    roots = discover_competitors(seed_url, max_items=limit, loose=loose)
    _log("final roots:", roots)

    for domain in roots:
        try:
            if not loose:
                ok, _ = is_shopify_site(domain)
                if not ok:
                    results.append({"competitor": domain, "error": "not Shopify-like"})
                    continue
            ctx = get_brand_context(domain)
            results.append({"competitor": domain, "context": ctx})
        except Exception as e:
            results.append({"competitor": domain, "error": str(e)})
    return results