import re
import json
import time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BrandInsightsBot/1.0; +https://example.com/bot)"
}
TIMEOUT = 15

def _get(url):
    return requests.get(url, headers=REQ_HEADERS, timeout=TIMEOUT)

def _soup(html):
    return BeautifulSoup(html, "lxml")

def _clean_text(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def _domain(url):
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    return f"{parsed.scheme}://{parsed.netloc}"

def is_shopify_site(website_url: str):
    """Lightweight Shopify heuristic: fingerprints in HTML/headers and common routes."""
    try:
        r = _get(website_url if website_url.startswith("http") else f"https://{website_url}")
        if r.status_code >= 400:
            return False, f"status {r.status_code}"
        soup = _soup(r.text)
        txt = r.text.lower()
        hints = [
            "cdn.shopify.com" in txt,
            "shopify-buy" in txt,
            "x-shopid" in [k.lower() for k in r.headers.keys()],
            "Shopify" in r.headers.get("Server", ""),
            bool(soup.select('a[href*="/products"]') or soup.select('a[href*="/collections"]')),
        ]
        if any(hints):
            return True, "looks like shopify"
        return False, "no shopify fingerprints found"
    except Exception as e:
        return False, str(e)

# -------------------------- PRODUCTS --------------------------

def fetch_products_json(base_url, max_pages=5, per_page=250):
    products, seen_ids = [], set()
    base = _domain(base_url)
    since_id = None
    for i in range(max_pages):
        try:
            if since_id:
                url = f"{base}/products.json?limit={per_page}&since_id={since_id}"
            else:
                url = f"{base}/products.json?limit={per_page}&page={i+1}"
            r = _get(url)
            if r.status_code != 200:
                break
            data = r.json().get("products", [])
            if not data:
                break
            for p in data:
                pid = p.get("id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                handle = p.get("handle")
                first_variant = (p.get("variants") or [{}])[0]
                price = first_variant.get("price")
                image = (p.get("images") or [{}])[0].get("src")
                products.append({
                    "id": pid,
                    "title": p.get("title"),
                    "handle": handle,
                    "price": price,
                    "url": urljoin(base, f"/products/{handle}") if handle else None,
                    "image": image
                })
                since_id = pid
        except Exception:
            break
        time.sleep(0.4)
    return products

def fetch_products_from_sitemap(base_url, max_items=100):
    base = _domain(base_url)
    urls = [
        f"{base}/sitemap_products_1.xml",
        f"{base}/sitemap_products_2.xml",
        f"{base}/sitemap.xml",
    ]
    products, seen = [], set()
    for u in urls:
        try:
            r = _get(u)
            if r.status_code != 200:
                continue
            soup = _soup(r.text)
            for loc in soup.find_all("loc"):
                href = _clean_text(loc.text)
                if "/products/" in href and href not in seen:
                    seen.add(href)
                    products.append({"url": href})
                    if len(products) >= max_items:
                        return products
        except Exception:
            continue
    return products

# -------------------------- PAGES --------------------------

def extract_home_hero_products(base_url, max_items=12):
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        hero = []

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else [data]
                for d in items:
                    if isinstance(d, dict) and d.get("@type") == "Product":
                        hero.append({
                            "title": d.get("name"),
                            "url": d.get("url"),
                            "image": (d.get("image") or [None])[0] if isinstance(d.get("image"), list) else d.get("image"),
                            "price": (d.get("offers") or {}).get("price")
                        })
            except Exception:
                pass

        for a in soup.select('a[href*="/products/"]'):
            title = _clean_text(a.get_text()) or a.get("title")
            href = urljoin(_domain(base_url), a.get("href"))
            if title and href:
                hero.append({"title": title, "url": href})

        seen, uniq = set(), []
        for p in hero:
            u = p.get("url")
            if u and u not in seen:
                seen.add(u)
                uniq.append(p)
        return uniq[:max_items]
    except Exception:
        return []

def find_policy_url(base_url, keywords=("privacy", "policy")):
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(k in href for k in keywords):
                return urljoin(_domain(base_url), a["href"])
        for guess in ["/policies/privacy-policy", "/pages/privacy-policy", "/policies/privacy"]:
            test = urljoin(_domain(base_url), guess)
            if _get(test).status_code == 200:
                return test
        return None
    except Exception:
        return None

def extract_policy_text(url, max_chars=4000):
    if not url:
        return None
    try:
        r = _get(url)
        soup = _soup(r.text)
        body = soup.select_one("main") or soup.body
        text = _clean_text(body.get_text(" ")) if body else ""
        return text[:max_chars]
    except Exception:
        return None

def find_refund_return_urls(base_url):
    found = {}
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "refund" in href and "refund_policy_url" not in found:
                found["refund_policy_url"] = urljoin(_domain(base_url), a["href"])
            if ("return" in href or "returns" in href) and "return_policy_url" not in found:
                found["return_policy_url"] = urljoin(_domain(base_url), a["href"])
        defaults = {
            "refund_policy_url": ["/policies/refund-policy", "/pages/refund-policy"],
            "return_policy_url": ["/pages/return-policy", "/policies/return-policy"],
        }
        for key, guesses in defaults.items():
            if key not in found:
                for g in guesses:
                    test = urljoin(_domain(base_url), g)
                    if _get(test).status_code == 200:
                        found[key] = test
                        break
    except Exception:
        pass
    return found

def find_faq(base_url):
    faq_url = None
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "faq" in href or "faqs" in href or "frequently-asked" in href:
                faq_url = urljoin(_domain(base_url), a["href"])
                break
        if not faq_url:
            test = urljoin(_domain(base_url), "/pages/faq")
            if _get(test).status_code == 200:
                faq_url = test
    except Exception:
        pass

    qa_pairs = []
    if faq_url:
        try:
            rr = _get(faq_url)
            ss = _soup(rr.text)
            for h in ss.select("h1,h2,h3,h4"):
                q = _clean_text(h.get_text())
                answer_chunks = []
                for sib in h.next_siblings:
                    if getattr(sib, "name", "") in ["h1", "h2", "h3", "h4"]:
                        break
                    answer_chunks.append(_clean_text(getattr(sib, "get_text", lambda *_: str(sib))()))
                a = _clean_text(" ".join(answer_chunks))[:1000]
                if q and a:
                    qa_pairs.append({"q": q, "a": a})
            if not qa_pairs:
                for d in ss.find_all("details"):
                    q = _clean_text((d.find("summary") or d).get_text())
                    a = _clean_text(d.get_text())
                    if q and a:
                        qa_pairs.append({"q": q, "a": a})
        except Exception:
            pass

    return {"url": faq_url, "qa_pairs": qa_pairs or None}

def find_socials(base_url):
    socials = {}
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "instagram.com" in href and "instagram" not in socials:
                socials["instagram"] = href
            elif "facebook.com" in href and "facebook" not in socials:
                socials["facebook"] = href
            elif "tiktok.com" in href and "tiktok" not in socials:
                socials["tiktok"] = href
            elif "youtube.com" in href and "youtube" not in socials:
                socials["youtube"] = href
            elif "x.com" in href or "twitter.com" in href:
                socials["twitter"] = href
    except Exception:
        pass
    return socials or None

def find_contacts(base_url):
    emails, phones = set(), set()
    contact_page = None
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("mailto:"):
                emails.add(href.replace("mailto:", "").strip())
            if href.startswith("tel:"):
                phones.add(re.sub(r"[^0-9+]", "", href.replace("tel:", "")))
            if ("contact" in href.lower() or "support" in href.lower()) and not contact_page:
                contact_page = urljoin(_domain(base_url), href)
        text = soup.get_text(" ")
        for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            emails.add(m)
        for m in re.findall(r"(\+?\d[\d\s\-().]{7,}\d)", text):
            phones.add(re.sub(r"[^0-9+]", "", m))
    except Exception:
        pass
    return {"emails": sorted(emails) or None, "phones": sorted(phones) or None, "contact_page": contact_page}

def find_about(base_url):
    about_url, excerpt = None, None
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        meta_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
        meta_desc = meta_desc.get("content") if meta_desc else None

        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "/pages/about" in href or "about-us" in href:
                about_url = urljoin(_domain(base_url), a["href"])
                break
        if about_url:
            rr = _get(about_url)
            ss = _soup(rr.text)
            main = ss.select_one("main") or ss.body
            if main:
                excerpt = _clean_text(main.get_text(" "))[:1000]
        return {"about_url": about_url, "about_excerpt": excerpt or meta_desc}
    except Exception:
        return {"about_url": None, "about_excerpt": None}

def find_important_links(base_url):
    links = {}
    candidates = {
        "order_tracking": ["track", "tracking", "order-tracking"],
        "blog": ["blog"],
        "contact_us": ["contact"],
    }
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        for a in soup.find_all("a", href=True):
            href_l = a["href"].lower()
            for key, kws in candidates.items():
                if any(k in href_l for k in kws) and key not in links:
                    links[key] = urljoin(_domain(base_url), a["href"])
    except Exception:
        pass
    return links or None

def get_store_header(base_url):
    try:
        r = _get(base_url)
        soup = _soup(r.text)
        title = _clean_text(soup.title.get_text()) if soup.title else None
        meta_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
        meta_desc = meta_desc.get("content") if meta_desc else None
        return {"url": _domain(base_url), "title": title, "meta_description": meta_desc}
    except Exception:
        return {"url": _domain(base_url), "title": None, "meta_description": None}

def get_brand_context(website_url: str):
    base = website_url if website_url.startswith("http") else f"https://{website_url}"

    store = get_store_header(base)

    products = fetch_products_json(base)
    if not products:
        products = fetch_products_from_sitemap(base)

    hero_products = extract_home_hero_products(base)

    privacy_url = find_policy_url(base, ("privacy",))
    privacy = extract_policy_text(privacy_url)

    ret_urls = find_refund_return_urls(base)
    refund_text = extract_policy_text(ret_urls.get("refund_policy_url"))
    return_text = extract_policy_text(ret_urls.get("return_policy_url"))

    faqs = find_faq(base)
    socials = find_socials(base)
    contacts = find_contacts(base)
    brand_about = find_about(base)
    important_links = find_important_links(base)

    context = {
        "store": store,
        "whole_product_catalog": products or None,
        "hero_products": hero_products or None,
        "privacy_policy_url": privacy_url,
        "privacy_policy_excerpt": privacy,
        "refund_policy_url": ret_urls.get("refund_policy_url"),
        "refund_policy_excerpt": refund_text,
        "return_policy_url": ret_urls.get("return_policy_url"),
        "return_policy_excerpt": return_text,
        "brand_faqs": faqs,
        "social_handles": socials,
        "contacts": contacts,
        "brand_context": brand_about,
        "important_links": important_links,
    }
    return context