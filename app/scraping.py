"""
Module de scraping du menu pour Keyword Categorization App
Récupère et nettoie les catégories de navigation à partir d'une URL fournie.
"""

from typing import List, Set, Optional
import html as _html
import re
import random
import time
import unicodedata as _unicodedata
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Liste d'User-Agents réalistes pour rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]


def create_session_with_retry() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_random_headers() -> dict:
    user_agent = random.choice(USER_AGENTS)
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }


def has_mojibake(s: str) -> bool:
    return any(token in s for token in ("Ã", "Â", "â€™", "â€œ", "â€", "â€¢"))


def decode_html_response(resp: requests.Response) -> str:
    raw = getattr(resp, "content", None)
    if isinstance(raw, (bytes, bytearray)):
        # 1) utf-8 direct
        try:
            text_utf8 = raw.decode("utf-8")
            if not has_mojibake(text_utf8):
                return text_utf8
        except Exception:
            pass
        # 2) latin-1 si nécessaire
        try:
            text_latin1 = raw.decode("latin-1", errors="ignore")
            if not has_mojibake(text_latin1):
                return text_latin1
        except Exception:
            pass
        # 3) charset-normalizer si dispo
        try:
            import charset_normalizer as cn  # type: ignore

            best = cn.from_bytes(raw).best()
            if best is not None:
                return str(best)
        except Exception:
            pass
    # 4) Fallback requests
    try:
        return resp.text
    except Exception:
        return ""


def extract_all_header_elements(soup: BeautifulSoup) -> List[str]:
    header_elements: List[str] = []
    header_selectors = [
        "header",
        'div[id="header"]',
        'div[id*="header"]',
        'div[class*="header"]',
    ]
    for selector in header_selectors:
        for element in soup.select(selector):
            for link in element.find_all("a", href=True):
                text = clean_text(link.get_text())
                if text and 2 <= len(text) <= 100 and text not in header_elements:
                    header_elements.append(text)
    return header_elements


def scrape_menu(url: str, session: Optional[requests.Session] = None) -> List[str]:
    session = session or create_session_with_retry()
    time.sleep(random.uniform(0.5, 1.5))
    try:
        headers = get_random_headers()
        resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)
        if resp.status_code == 403:
            simple_headers = {
                "User-Agent": USER_AGENTS[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
            resp = session.get(url, headers=simple_headers, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        html_text = decode_html_response(resp)
    except Exception as e:
        print(f"Erreur lors du scraping du menu : {e}")
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    menu_items = extract_all_header_elements(soup)
    if len(menu_items) < 3:
        menu_items.update(extract_structured_navigation(soup)) if isinstance(menu_items, set) else menu_items.extend(list(extract_structured_navigation(soup)))
    if len(menu_items) < 2:
        menu_items_set = set(menu_items) if not isinstance(menu_items, set) else menu_items
        menu_items_set.update(extract_main_links(soup, url))
        menu_items = list(menu_items_set)
    categories = clean_and_filter_menu_items_preserve_order(menu_items)
    return categories


def extract_structured_navigation(soup: BeautifulSoup) -> Set[str]:
    menu_items: Set[str] = set()
    nav_selectors = [
        "nav",
        "header",
        "footer",
        '[role="navigation"]',
        '[class*="nav"]',
        '[class*="menu"]',
        '[id*="nav"]',
        '[id*="menu"]',
        '[class*="header"]',
        '[class*="footer"]',
    ]
    for selector in nav_selectors:
        for element in soup.select(selector):
            for ul in element.find_all(["ul", "ol"]):
                for li in ul.find_all("li", recursive=False):
                    txt = extract_link_text(li)
                    if txt:
                        menu_items.add(txt)
            for a in element.find_all("a", href=True):
                txt = clean_text(a.get_text())
                if txt:
                    menu_items.add(txt)
    return menu_items


def extract_main_links(soup: BeautifulSoup, base_url: str) -> Set[str]:
    menu_items: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        txt = clean_text(a.get_text())
        if is_internal_link(href, base_url) and is_valid_menu_item(txt, href, base_url):
            menu_items.add(txt)
    return menu_items


def extract_link_text(li_element) -> Optional[str]:
    a = li_element.find("a")
    if a:
        return clean_text(a.get_text())
    for child in li_element.children:
        if hasattr(child, "name") and child.name in ["span", "div", "strong", "b"]:
            txt = clean_text(child.get_text())
            if txt:
                return txt
    return clean_text(li_element.get_text())


def clean_text(text: str) -> str:
    if not text:
        return ""
    txt = _html.unescape(str(text))
    try:
        import ftfy  # type: ignore

        txt = ftfy.fix_text(txt)
    except Exception:
        if any(m in txt for m in ("Ã", "Â", "â€™", "â€œ", "â€", "â€¢")):
            try:
                txt = txt.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore") or txt
            except Exception:
                pass
    # Remplacements ciblés sûrs
    replacements = {
        "Ã ": "à",
        "Ã¢": "â",
        "Ã¤": "ä",
        "Ã§": "ç",
        "Ã©": "é",
        "Ã¨": "è",
        "Ãª": "ê",
        "Ã«": "ë",
        "Ã®": "î",
        "Ã¯": "ï",
        "Ã´": "ô",
        "Ã¶": "ö",
        "Ã¹": "ù",
        "Ã»": "û",
        "Ã¼": "ü",
        "Â ": "\u00A0",
        "Â°": "°",
        "â€™": "’",
        "â€˜": "‘",
        "â€“": "–",
        "â€”": "—",
        "â€œ": "“",
        "â€": "”",
        "â€¢": "•",
    }
    for bad, good in replacements.items():
        if bad in txt:
            txt = txt.replace(bad, good)
    txt = _unicodedata.normalize("NFC", txt)
    txt = re.sub(r"\s+", " ", txt.strip())
    txt = re.sub(r"[\n\r\t]", " ", txt)
    txt = "".join(ch for ch in txt if ord(ch) >= 32)
    return txt.strip()


def is_valid_menu_item(text: str, href: str, base_url: str) -> bool:
    if not text or len(text) < 2:
        return False
    if len(text) > 50:
        return False
    if href.startswith("#") or href.startswith("javascript:"):
        return False
    if href.startswith("mailto:") or href.startswith("tel:"):
        return False
    return True


def is_internal_link(href: str, base_url: str) -> bool:
    if not href:
        return False
    if href.startswith("/") or href.startswith("./") or href.startswith("../"):
        return True
    try:
        return urlparse(base_url).netloc == urlparse(href).netloc
    except Exception:
        return False


def clean_and_filter_menu_items_preserve_order(menu_items: List[str]) -> List[str]:
    if not menu_items:
        return []
    cleaned: List[str] = []
    for item in menu_items:
        t = clean_text(item)
        if t and len(t) >= 2:
            cleaned.append(t)
    unique: dict[str, str] = {}
    for t in cleaned:
        key = t.lower()
        if key not in unique:
            unique[key] = t
    return list(unique.values())


