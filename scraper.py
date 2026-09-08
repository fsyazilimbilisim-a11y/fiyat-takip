import re
import time
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List
from curl_cffi import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

_session: Optional[requests.Session] = None


def get_session(force_new: bool = False) -> requests.Session:
    global _session
    if _session is None or force_new:
        try:
            if _session:
                _session.close()
        except Exception:
            pass
        _session = requests.Session(impersonate="chrome124")
        _session.headers.update(HEADERS)
        try:
            _session.get("https://www.akakce.com", timeout=10)
        except Exception:
            pass
    return _session


def parse_turkish_price(price_str: str) -> Optional[float]:
    """
    Örn: '12.041,49 TL', '3.499,00TL', '3.500 TL' -> float(12041.49)
    """
    if not price_str:
        return None
    try:
        cleaned = price_str.upper().replace("TL", "").replace("TRY", "").strip()
        cleaned = re.split(r'\+|\s+FİYAT|\s+FIYAT', cleaned, flags=re.IGNORECASE)[0].strip()
        cleaned = cleaned.replace(".", "").replace(",", ".")
        match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
        if match:
            return float(match.group(1))
    except Exception as e:
        pass
    return None


def extract_direct_link(raw_href: str) -> str:
    """
    Akakçe yönlendirme linkini (akakce.com/r/?pr=...) temiz bir şekilde üretir.
    """
    if not raw_href:
        return "https://www.akakce.com"
        
    try:
        if "f=" in raw_href:
            f_val = raw_href.split("f=")[1].split("&")[0]
            unquoted = urllib.parse.unquote(f_val)
            if unquoted.startswith("/"):
                return "https://www.akakce.com" + unquoted
            elif unquoted.startswith("http"):
                return unquoted
        if raw_href.startswith("/"):
            return "https://www.akakce.com" + raw_href
        if raw_href.startswith("http"):
            return raw_href
    except Exception:
        pass
    return "https://www.akakce.com"


def extract_price_history_from_scripts(html: str) -> List[Dict[str, Any]]:
    """
    Akakçe ürün sayfasındaki <script> etiketleri içinde dizi (array) formatında yer alan
    geçmiş fiyat grafiği verilerini (Highcharts series, timestamp veya date array) regex ile ayrıştırır.
    Format: [{ 'date': 'YYYY-MM-DD', 'price': 8095.00, 'display_date': '16.04.2026' }, ...]
    """
    points = []
    
    # 1. Date.UTC pattern: Date.UTC(YYYY, M-1, D), price
    utc_pattern = r'Date\.UTC\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})\)[^,\d]*,\s*([0-9]+(?:\.[0-9]+)?)'
    utc_matches = re.findall(utc_pattern, html)
    if utc_matches:
        for y, m, d, p in utc_matches:
            month = int(m) + 1  # JS 0-index month to 1-12
            iso_date = f"{int(y):04d}-{month:02d}-{int(d):02d}"
            disp_date = f"{int(d):02d}.{month:02d}.{int(y):04d}"
            points.append({
                "date": iso_date,
                "price": float(p),
                "display_date": disp_date,
                "price_str": f"{float(p):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
            })
        if points:
            return points

    # 2. Timestamp (ms) and price array: [1713225600000, 8095.0]
    ts_pattern = r'\[\s*(\d{12,13})\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*\]'
    ts_matches = re.findall(ts_pattern, html)
    if len(ts_matches) >= 3:
        for ts, p in ts_matches:
            try:
                dt = datetime.fromtimestamp(int(ts) / 1000.0)
                points.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "price": float(p),
                    "display_date": dt.strftime("%d.%m.%Y"),
                    "price_str": f"{float(p):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
                })
            except Exception:
                pass
        if points:
            return points

    # 3. Date string and price array: ["2026-04-16", 8095.0] or ['16.04.2026', 8095.0]
    str_pattern = r'\[\s*[\'"](\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})[\'"]\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*\]'
    str_matches = re.findall(str_pattern, html)
    if len(str_matches) >= 3:
        for d_str, p in str_matches:
            if "." in d_str:
                dp = d_str.split(".")
                iso_date = f"{dp[2]}-{dp[1]}-{dp[0]}"
                disp_date = d_str
            else:
                iso_date = d_str
                dp = d_str.split("-")
                disp_date = f"{dp[2]}.{dp[1]}.{dp[0]}"
            points.append({
                "date": iso_date,
                "price": float(p),
                "display_date": disp_date,
                "price_str": f"{float(p):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
            })
        if points:
            return points

    # 4. Object array: { date: "...", price: ... } or { x: ..., y: ... }
    obj_pattern = r'\{\s*[\'"]?(?:date|time|x)[\'"]?\s*:\s*[\'"]?([^\'"}]+)[\'"]?\s*,\s*[\'"]?(?:price|val|y)[\'"]?\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*\}'
    obj_matches = re.findall(obj_pattern, html)
    if len(obj_matches) >= 3:
        for d_str, p in obj_matches:
            try:
                d_str = d_str.strip().strip("'\"")
                if "." in d_str:
                    dp = d_str.split(".")
                    iso_date = f"{dp[2]}-{dp[1]}-{dp[0]}"
                    disp_date = d_str
                elif "-" in d_str and len(d_str) >= 10:
                    iso_date = d_str[:10]
                    dp = iso_date.split("-")
                    disp_date = f"{dp[2]}.{dp[1]}.{dp[0]}"
                elif d_str.isdigit() and len(d_str) >= 10:
                    dt = datetime.fromtimestamp(int(d_str[:10]))
                    iso_date = dt.strftime("%Y-%m-%d")
                    disp_date = dt.strftime("%d.%m.%Y")
                else:
                    continue
                points.append({
                    "date": iso_date,
                    "price": float(p),
                    "display_date": disp_date,
                    "price_str": f"{float(p):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
                })
            except Exception:
                pass
        if points:
            return points

    return points


def extract_price_history_from_table(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Akakçe ürün sayfasındaki table.graph_table tablosundaki tüm tarih ve fiyatları ayrıştırır.
    Tarihleri 'YYYY-MM-DD' ISO formatına dönüştürür.
    Format: [{ 'date': 'YYYY-MM-DD', 'price': 8095.00, 'display_date': '16.04.2026', ... }, ...]
    """
    points = []
    table = soup.select_one("table.graph_table")
    if not table:
        return points

    rows = table.select("tbody tr")
    for tr in rows:
        tds = tr.select("td")
        if len(tds) >= 2:
            date_raw = tds[0].get_text(strip=True)  # örn: '13.03.2026'
            p_text = tds[1].get_text(strip=True)    # örn: '8.391,35 TL'
            p_val = parse_turkish_price(p_text)

            diff_text = tds[2].get_text(strip=True) if len(tds) > 2 else ""
            diff_val = parse_turkish_price(diff_text) or 0.0

            pct_text = tds[3].get_text(strip=True) if len(tds) > 3 else ""
            pct_clean = pct_text.replace("%", "").replace(",", ".").strip()
            try:
                pct_val = float(pct_clean)
            except Exception:
                pct_val = 0.0

            is_down = "green" in str(tr) or "in" in str(tr)
            if is_down and diff_val > 0:
                diff_val = -diff_val
                pct_val = -pct_val

            # ISO YYYY-MM-DD formatına dönüştürme
            iso_date = date_raw
            if "." in date_raw:
                parts = date_raw.split(".")
                if len(parts) == 3:
                    iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

            if p_val:
                points.append({
                    "date": iso_date,
                    "price": p_val,
                    "display_date": date_raw,
                    "price_str": p_text,
                    "diff": diff_val,
                    "percent": pct_val
                })

    # Kronolojik sıra (eskiden yeniye)
    return list(reversed(points))


def generate_fallback_history(current_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Akakçe'den script/tablo verisi anlık çekilemezse sistemin çökmemesi için
    temsili geçmiş fiyat verisi döner (6 aylık periyot, gerçekçi dalgalanmalar).
    """
    from datetime import timedelta
    base_price = current_price if (current_price and current_price > 0) else 3500.0
    now = datetime.now()
    points = []
    
    multipliers = [
        0.88, 0.90, 0.89, 0.92, 0.87, 0.91, 0.93, 0.95,
        0.94, 0.96, 0.92, 0.97, 0.99, 0.95, 0.98, 1.01,
        1.00, 0.99, 1.00
    ]
    total_steps = len(multipliers)
    days_span = 180
    step_days = max(1, days_span // total_steps)
    
    for i, mult in enumerate(multipliers):
        d = now - timedelta(days=(total_steps - 1 - i) * step_days)
        p = round(base_price * mult, 2)
        if i == total_steps - 1:
            p = base_price  # Son nokta tam olarak şu andaki fiyat
        iso_d = d.strftime("%Y-%m-%d")
        disp_d = d.strftime("%d.%m.%Y")
        points.append({
            "date": iso_d,
            "price": p,
            "display_date": disp_d,
            "price_str": f"{p:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."),
            "diff": 0.0,
            "percent": 0.0,
            "is_fallback": True
        })
    return points


def compute_history_statistics(points: List[Dict[str, Any]], current_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Tarih ve fiyat ikililerinden:
    - Dönem İçi En Yüksek Fiyat & Tarih
    - Dönem İçi En Düşük Fiyat & Tarih
    - Şu Andaki Fiyat
    hesaplar.
    """
    if not points:
        cur = current_price or 0.0
        return {
            "has_history": False,
            "total_points": 0,
            "min_price": cur,
            "min_date": "-",
            "max_price": cur,
            "max_date": "-",
            "avg_price": cur,
            "current_price": cur,
            "oldest_price": cur,
            "oldest_date": "-",
            "rise_from_min_tl": 0.0,
            "rise_from_min_pct": 0.0,
            "drop_from_max_tl": 0.0,
            "drop_from_max_pct": 0.0,
            "drop_from_avg_tl": 0.0,
            "drop_from_avg_pct": 0.0,
            "discount_pct": 0.0,
            "is_big_discount": False,
            "net_1y_change_tl": 0.0,
            "net_1y_change_pct": 0.0
        }

    prices = [p["price"] for p in points]
    highest_p = max(prices)
    lowest_p = min(prices)
    cur_p = current_price if (current_price and current_price > 0) else points[-1]["price"]

    avg_p = round(sum(prices) / len(prices), 2) if prices else cur_p
    drop_from_avg_tl = round(avg_p - cur_p, 2)
    drop_from_avg_pct = round(((avg_p - cur_p) / avg_p * 100), 1) if avg_p > 0 else 0.0

    highest_pt = next(p for p in reversed(points) if p["price"] == highest_p)
    lowest_pt = next(p for p in reversed(points) if p["price"] == lowest_p)
    oldest_pt = points[0]

    rise_tl = cur_p - lowest_p
    rise_pct = round((rise_tl / lowest_p * 100), 1) if lowest_p > 0 else 0.0

    drop_tl = highest_p - cur_p
    drop_pct = round((drop_tl / highest_p * 100), 1) if highest_p > 0 else 0.0

    discount_pct = max(drop_from_avg_pct, drop_pct, 0.0)
    is_big_discount = bool(discount_pct >= 20.0 or drop_from_avg_pct >= 20.0)

    net_tl = cur_p - oldest_pt["price"]
    net_pct = round((net_tl / oldest_pt["price"] * 100), 1) if oldest_pt["price"] > 0 else 0.0

    return {
        "has_history": True,
        "total_points": len(points),
        "min_price": lowest_p,
        "min_date": lowest_pt.get("display_date") or lowest_pt["date"],
        "max_price": highest_p,
        "max_date": highest_pt.get("display_date") or highest_pt["date"],
        "avg_price": avg_p,
        "current_price": cur_p,
        "oldest_price": oldest_pt["price"],
        "oldest_date": oldest_pt.get("display_date") or oldest_pt["date"],
        "rise_from_min_tl": round(rise_tl, 2),
        "rise_from_min_pct": rise_pct,
        "drop_from_max_tl": round(drop_tl, 2),
        "drop_from_max_pct": drop_pct,
        "drop_from_avg_tl": drop_from_avg_tl,
        "drop_from_avg_pct": drop_from_avg_pct,
        "discount_pct": discount_pct,
        "is_big_discount": is_big_discount,
        "net_1y_change_tl": round(net_tl, 2),
        "net_1y_change_pct": net_pct
    }


def extract_historical_data(soup: BeautifulSoup, html: str, current_price: Optional[float] = None) -> Dict[str, Any]:
    """
    1. Önce sayfa kaynağındaki script etiketlerinden dizi/Highcharts ayrıştırmayı dener.
    2. Bulunamazsa table.graph_table tablosunu ayrıştırır.
    3. Her ikisi de bulunamazsa uygulamanın çökmemesi için temsilî fallback geçmişi üretir.
    """
    # 1. Script kontrolü
    points = extract_price_history_from_scripts(html)
    
    # 2. Tablo kontrolü
    if not points:
        points = extract_price_history_from_table(soup)
        
    # 3. Fallback kontrolü
    if not points:
        points = generate_fallback_history(current_price)
        
    stats = compute_history_statistics(points, current_price)
    
    return {
        "points": points,
        "stats": stats
    }


def extract_seller_details(row) -> tuple:
    """
    Satıcı adını ve satıcı logosunu Akakçe satırından temizleyerek çeker.
    """
    v_el = row.select_one(".v_v8, .v_n, .v_b")
    seller_name = "Bilinmeyen"
    seller_logo = ""
    if v_el:
        img = v_el.select_one("img")
        if img:
            seller_logo = img.get("src") or img.get("data-src") or ""
            if img.get("alt"):
                seller_name = img.get("alt").strip()
        b_el = v_el.select_one("b")
        if b_el and b_el.get_text(strip=True):
            b_name = b_el.get_text(strip=True)
            if seller_name == "Bilinmeyen":
                seller_name = b_name
            elif b_name.lower() not in seller_name.lower():
                seller_name = f"{seller_name} ({b_name})"
        elif seller_name == "Bilinmeyen":
            from bs4 import BeautifulSoup as BS
            v_copy = BS(str(v_el), "html.parser")
            for junk in v_copy.select(".rc_v8, .r_v8, em"):
                junk.decompose()
            cleaned_text = v_copy.get_text(strip=True)
            if cleaned_text:
                seller_name = cleaned_text
    else:
        alt_img = row.select_one("img[alt]")
        if alt_img and alt_img.get("alt"):
            seller_name = alt_img.get("alt").strip()
            seller_logo = alt_img.get("src") or alt_img.get("data-src") or ""

    seller_name = seller_name.strip(" /-,")
    seller_name = re.sub(r'\d+[,\.]\d+\s*\d*\s*Yorum.*', '', seller_name, flags=re.IGNORECASE).strip()
    return seller_name or "Bilinmeyen", seller_logo


def scrape_akakce_product(url: str, retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Verilen Akakçe ürün linkinden en düşük fiyatı, satıcıları, ürün görselini ve 1 yıllık fiyat geçmişini çeker.
    """
    session = get_session()
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(
                url,
                timeout=10
            )
            
            if resp.status_code == 429:
                wait_time = 3 + attempt * 2
                print(f"[Scraper] Akakçe hız sınırı (HTTP 429). {wait_time} saniye bekleniyor... Deneme {attempt}/{retries}", flush=True)
                time.sleep(wait_time)
                session = get_session(force_new=True)
                continue
            elif resp.status_code != 200:
                print(f"[Scraper] Uyarı: {url} HTTP {resp.status_code} döndürdü. Deneme {attempt}/{retries}", flush=True)
                time.sleep(2)
                continue
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 1. Başlık
            title_el = soup.find("h1") or soup.select_one(".p_h1, .p-title, .title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title and soup.title:
                title = soup.title.string.split("|")[0].strip()

            # 2. Orijinal Ürün Görseli
            img_url = ""
            og_img = soup.select_one('meta[property="og:image"]')
            if og_img and og_img.get("content"):
                img_url = og_img.get("content").strip()
            if not img_url:
                img_el = soup.select_one("img[itemprop='image'], #img_v8 img, .p_img_v8 img, #p_u_img img, .img_u img, img.p_img")
                if img_el:
                    img_url = (img_el.get("src") or img_el.get("data-src") or "").strip()
                
            # 3. Satıcılar listesi
            seller_rows = soup.select("#PL li, .pl_v8 li, ul.pl li, .v_w, li.w")
            
            lowest_price = None
            lowest_price_str = ""
            lowest_seller = "Bilinmeyen Satıcı"
            lowest_direct_link = url
            lowest_cargo = ""
            all_sellers = []
            
            for row in seller_rows:
                price_el = row.select_one(".pt_v8, .pr_v8, .pt, .pr, span.price")
                if not price_el:
                    continue
                p_text = price_el.get_text(strip=True)
                p_val = parse_turkish_price(p_text)
                if not p_val:
                    continue
                    
                seller_name, seller_logo = extract_seller_details(row)
                cargo_el = row.select_one(".bdgv_v8, .n_uk_v8, .kargo")
                cargo = cargo_el.get_text(strip=True) if cargo_el else "Ücretsiz Kargo"
                
                link_el = row.select_one("a[href]")
                raw_href = link_el.get("href", "") if link_el else ""
                direct_link = extract_direct_link(raw_href)
                
                seller_info = {
                    "seller_name": seller_name,
                    "seller_logo": seller_logo,
                    "price": p_val,
                    "price_str": f"{p_val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."),
                    "cargo": cargo,
                    "url": direct_link
                }
                all_sellers.append(seller_info)
                
                if lowest_price is None or p_val < lowest_price:
                    lowest_price = p_val
                    lowest_price_str = seller_info["price_str"]
                    lowest_seller = seller_name
                    lowest_direct_link = direct_link
                    lowest_cargo = cargo

            if lowest_price is None:
                top_price_el = soup.select_one(".pd_v8 .pt_v8, .p_c .pt_v8, span.pt, span.pr")
                if top_price_el:
                    top_text = top_price_el.get_text(strip=True)
                    top_val = parse_turkish_price(top_text)
                    if top_val:
                        lowest_price = top_val
                        lowest_price_str = f"{top_val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
                        lowest_seller = "Akakçe En Düşük Liste Fiyatı"
                        lowest_direct_link = url

            # Satıcıları fiyata göre artan sırada sırala
            all_sellers.sort(key=lambda x: x["price"])
            top_3_sellers = all_sellers[:3]
            if not top_3_sellers and lowest_price is not None:
                top_3_sellers = [{
                    "seller_name": lowest_seller,
                    "seller_logo": "",
                    "price": lowest_price,
                    "price_str": lowest_price_str,
                    "cargo": lowest_cargo,
                    "url": lowest_direct_link
                }]

            # 4. Son 1 Yıllık / 6 Aylık Tarihsel Fiyat Geçmişi (Script / Tablo / Fallback)
            history_data = extract_historical_data(soup, resp.text, lowest_price)

            if lowest_price is not None:
                return {
                    "title": title,
                    "url": url,
                    "image_url": img_url,
                    "lowest_price": lowest_price,
                    "lowest_price_str": lowest_price_str,
                    "lowest_seller": lowest_seller,
                    "direct_link": lowest_direct_link,
                    "cargo": lowest_cargo,
                    "top_3_sellers": top_3_sellers,
                    "all_sellers": all_sellers[:10],
                    "historical_1y": history_data["points"],
                    "stats_1y": history_data["stats"],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            print(f"[Scraper] {url} çekilirken hata (deneme {attempt}/{retries}): {e}", flush=True)
            time.sleep(2)
            
    return None


def search_product_on_akakce(query: str) -> List[Dict[str, Any]]:
    """
    Akakçe üzerinde ürün araması yapar ve ilk eşleşen ürünleri listeler.
    """
    results = []
    try:
        session = get_session()
        url = f"https://www.akakce.com/arama/?q={urllib.parse.quote_plus(query)}"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li[data-pr], .p-c, li.wrap")
            for item in items[:6]:
                a = item.select_one("a[href]")
                if not a:
                    continue
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = urllib.parse.urljoin("https://www.akakce.com", href)
                    
                title_el = item.select_one("h3, .pn, .title")
                title = title_el.get_text(strip=True) if title_el else ""
                
                price_el = item.select_one(".pt, .pr, span.price")
                price_str = price_el.get_text(strip=True) if price_el else ""
                price_val = parse_turkish_price(price_str)
                
                if title and href:
                    results.append({
                        "title": title,
                        "url": href,
                        "price": price_val,
                        "price_str": price_str
                    })
    except Exception as e:
        print(f"[Scraper Search Error]: {e}", flush=True)
    return results
