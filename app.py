import os
import json
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
import scraper
import notifier
import scheduler_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Klasörlerin varlığını garanti altına al
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıç işlemleri
    print("[Uygulama] Başlatılıyor...")
    database.init_db()
    cfg = scheduler_service.load_config()
    if cfg.get("products"):
        database.sync_products_from_config(cfg["products"])
    scheduler_service.setup_scheduler()
    print("[Uygulama] Veritabanı ve Zamanlayıcı hazır.")
    yield
    # Kapanış işlemleri
    print("[Uygulama] Kapatılıyor...")
    if scheduler_service.scheduler and scheduler_service.scheduler.running:
        scheduler_service.scheduler.shutdown(wait=False)


app = FastAPI(title="Akakçe Fiyat Takip & Alarm Sistemi", lifespan=lifespan)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Pydantic modelleri
class ThresholdUpdateRequest(BaseModel):
    threshold_price: float


class ProductCreateRequest(BaseModel):
    name: str
    category: Optional[str] = "SSD & Depolama"
    capacity: Optional[str] = ""
    url: str
    threshold_price: float = 0.0


class SettingsUpdateRequest(BaseModel):
    daily_report_time: Optional[str] = "10:00"
    check_interval_minutes: Optional[int] = 60
    scheduler_enabled: Optional[bool] = True
    desktop_enabled: Optional[bool] = True
    telegram_enabled: Optional[bool] = False
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    discord_enabled: Optional[bool] = False
    discord_webhook_url: Optional[str] = ""


class TestNotificationRequest(BaseModel):
    channel: str  # 'desktop', 'telegram', 'discord'


@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))


@app.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots():
    content = "User-agent: *\nAllow: /\n\nSitemap: https://fsyazilimbilisim.com/sitemap.xml\n"
    return PlainTextResponse(content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def get_sitemap():
    now_str = datetime.now().strftime("%Y-%m-%d")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://fsyazilimbilisim.com/</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://fsyazilimbilisim.com/?cat=deals</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://fsyazilimbilisim.com/?cat=bilgisayar</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://fsyazilimbilisim.com/?cat=ram</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://fsyazilimbilisim.com/?cat=oyuncak</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://fsyazilimbilisim.com/?cat=bisiklet</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@app.get("/google{code}.html")
async def google_verification(code: str):
    filename = f"google{code}.html"
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read().strip())
    raise HTTPException(status_code=404, detail="Doğrulama dosyası bulunamadı")




@app.get("/api/status")
async def get_status():
    config = scheduler_service.load_config()
    products = database.get_all_products()
    sched = scheduler_service.scheduler
    
    return {
        "status": "online",
        "scheduler_running": sched.running if sched else False,
        "daily_report_time": config.get("schedule", {}).get("daily_report_time", "10:00"),
        "check_interval_minutes": config.get("schedule", {}).get("check_interval_minutes", 60),
        "total_products": len(products),
        "active_products": len([p for p in products if p.get("is_active")]),
        "desktop_enabled": config.get("notifications", {}).get("desktop_enabled", True),
        "telegram_enabled": config.get("notifications", {}).get("telegram_enabled", False),
        "discord_enabled": config.get("notifications", {}).get("discord_enabled", False)
    }


@app.get("/api/products")
async def get_products():
    products = database.get_all_products()
    enriched = []
    
    for p in products:
        prod_id = p["id"]
        latest = database.get_latest_price(prod_id)
        yesterday = database.get_yesterday_price(prod_id)
        
        cur_p = latest["price"] if latest else None
        yest_p = yesterday["price"] if yesterday else None
        
        diff = 0.0
        diff_pct = 0.0
        if cur_p is not None and yest_p is not None:
            diff = cur_p - yest_p
            if yest_p > 0:
                diff_pct = round((diff / yest_p) * 100, 2)
                
        top_sellers = latest.get("top_sellers", []) if latest else []
        if not top_sellers and latest and latest.get("price"):
            top_sellers = [{
                "seller_name": latest.get("seller") or "En Ucuz Satıcı",
                "seller_logo": "",
                "price": latest.get("price"),
                "price_str": scheduler_service.format_currency(latest["price"]),
                "cargo": latest.get("cargo_info") or "Ücretsiz Kargo",
                "url": latest.get("direct_link") or p["url"]
            }]
            
        cache = database.get_product_history_cache(prod_id)
        stats = cache.get("stats", {}) if cache else {}
        avg_price = stats.get("avg_price") or 0.0
        max_price = stats.get("max_price") or 0.0
        drop_from_avg = stats.get("drop_from_avg_pct") or 0.0
        drop_from_max = stats.get("drop_from_max_pct") or 0.0
        
        candidates = [drop_from_avg]
        if drop_from_max and drop_from_max > 0:
            candidates.append(drop_from_max)
        if diff_pct < 0:
            candidates.append(abs(diff_pct))
        best_discount = max(candidates) if candidates else 0.0
        is_deal = bool(drop_from_avg >= 20.0 or stats.get("is_big_discount") or best_discount >= 20.0)
                
        enriched.append({
            "id": prod_id,
            "name": p["name"],
            "category": p.get("category", "SSD & Depolama"),
            "capacity": p.get("capacity", ""),
            "url": p["url"],
            "image_url": p.get("image_url", ""),
            "threshold_price": p.get("threshold_price", 0.0),
            "is_active": bool(p.get("is_active", 1)),
            "current_price": cur_p,
            "current_price_str": scheduler_service.format_currency(cur_p) if cur_p else "Henüz taranmadı",
            "current_seller": latest["seller"] if latest else "-",
            "direct_link": latest["direct_link"] if latest else p["url"],
            "cargo_info": latest["cargo_info"] if latest else "-",
            "top_sellers": top_sellers,
            "checked_at": latest["checked_at"] if latest else None,
            "yesterday_price": yest_p,
            "yesterday_price_str": scheduler_service.format_currency(yest_p) if yest_p else "-",
            "yesterday_seller": yesterday["seller"] if yesterday else "-",
            "price_diff": diff,
            "price_diff_percent": diff_pct,
            "avg_price": avg_price,
            "avg_price_str": scheduler_service.format_currency(avg_price) if avg_price > 0 else "-",
            "max_price": max_price,
            "max_price_str": scheduler_service.format_currency(max_price) if max_price > 0 else "-",
            "discount_percent": round(drop_from_avg if drop_from_avg > 0 else best_discount, 1),
            "is_featured_deal": is_deal,
            "is_below_threshold": bool(cur_p and p.get("threshold_price") and cur_p <= p.get("threshold_price"))
        })
        
    return enriched


@app.get("/api/history/{product_id}")
async def get_history(product_id: str, limit: int = 100):
    prod = database.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
    cache = database.get_product_history_cache(product_id)
    
    if not cache or not cache.get("points"):
        try:
            scraped = scraper.scrape_akakce_product(prod["url"])
            if scraped and scraped.get("historical_1y"):
                database.save_product_history_cache(
                    product_id=product_id,
                    points=scraped["historical_1y"],
                    stats=scraped.get("stats_1y", {})
                )
                cache = database.get_product_history_cache(product_id)
        except Exception as e:
            print(f"[History API] Geçmiş çekme hatası: {e}")
            
    live_history = database.get_price_history(product_id, limit=limit)

    raw_points = cache["points"] if (cache and cache.get("points")) else []
    normalized_points = []
    for p in raw_points:
        d_str = p.get("date", "")
        disp_str = p.get("display_date", "")
        if "." in d_str:
            parts = d_str.split(".")
            if len(parts) == 3:
                iso_d = f"{parts[2]}-{parts[1]}-{parts[0]}"
                disp_str = d_str
            else:
                iso_d = d_str
        else:
            iso_d = d_str
            if "-" in d_str and len(d_str.split("-")) == 3:
                parts = d_str.split("-")
                disp_str = f"{parts[2]}.{parts[1]}.{parts[0]}"
        
        normalized_points.append({
            "date": iso_d,
            "price": p["price"],
            "display_date": disp_str or iso_d,
            "price_str": p.get("price_str") or f"{p['price']:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
        })

    # Fallback mekanizması: Eğer geçmiş veri henüz yoksa canlı loglar veya temsili eğriyi kullan
    if not normalized_points:
        if live_history and len(live_history) >= 2:
            for h in reversed(live_history):
                dt_part = h["checked_at"].split(" ")[0]
                dp = dt_part.split("-")
                disp = f"{dp[2]}.{dp[1]}.{dp[0]}" if len(dp) == 3 else dt_part
                normalized_points.append({
                    "date": dt_part,
                    "price": h["price"],
                    "display_date": disp,
                    "price_str": f"{h['price']:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
                })
        else:
            last_p = live_history[0]["price"] if live_history else (prod.get("threshold_price") or 3500.0)
            normalized_points = scraper.generate_fallback_history(last_p)

    current_p = normalized_points[-1]["price"] if normalized_points else (prod.get("threshold_price") or 0.0)
    stats = scraper.compute_history_statistics(normalized_points, current_p)
    
    return {
        "product_id": product_id,
        "product_name": prod["name"],
        "capacity": prod.get("capacity", ""),
        "threshold_price": prod.get("threshold_price", 0.0),
        "has_1y_history": len(normalized_points) > 0,
        "historical_1y_points": normalized_points,
        "stats_1y": stats,
        "summary": {
            "highest_price": stats.get("max_price"),
            "highest_date": stats.get("max_date"),
            "lowest_price": stats.get("min_price"),
            "lowest_date": stats.get("min_date"),
            "current_price": stats.get("current_price")
        },
        "live_history": live_history
    }


@app.get("/api/reports")
async def get_reports(limit: int = 20):
    return database.get_latest_reports(limit=limit)


@app.get("/api/alarms")
async def get_alarms(limit: int = 20):
    return database.get_recent_alarms(limit=limit)


@app.post("/api/check-now")
async def check_now():
    """Tüm ürünleri hemen canlı olarak tarar ve günceller."""
    result = scheduler_service.run_check_cycle(is_daily_report=False)
    return result


@app.post("/api/generate-daily-report")
async def generate_daily_report():
    """Saat 10:00 günlük özet raporunu simüle edip hemen üretir."""
    result = scheduler_service.run_check_cycle(is_daily_report=True)
    return result


@app.post("/api/products/{product_id}/threshold")
async def update_threshold(product_id: str, req: ThresholdUpdateRequest):
    database.update_product_threshold(product_id, req.threshold_price)
    # config.json'ı da güncelle
    cfg = scheduler_service.load_config()
    for p in cfg.get("products", []):
        if p["id"] == product_id:
            p["threshold_price"] = req.threshold_price
    scheduler_service.save_config(cfg)
    return {"status": "success", "threshold_price": req.threshold_price}


@app.post("/api/products/{product_id}/toggle")
async def toggle_product(product_id: str):
    p = database.get_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    new_state = not bool(p.get("is_active"))
    database.toggle_product_active(product_id, new_state)
    return {"status": "success", "is_active": new_state}


@app.post("/api/products")
async def add_product(req: ProductCreateRequest):
    import uuid
    prod_id = "prod-" + str(uuid.uuid4())[:8]
    prod_data = {
        "id": prod_id,
        "name": req.name,
        "category": req.category or "SSD & Depolama",
        "capacity": req.capacity,
        "url": req.url,
        "threshold_price": req.threshold_price,
        "is_active": True
    }
    database.add_or_update_product(prod_data)
    
    # config.json'a da ekle
    cfg = scheduler_service.load_config()
    cfg.setdefault("products", []).append(prod_data)
    scheduler_service.save_config(cfg)
    
    # İlk taramayı hemen yap
    try:
        scraped = scraper.scrape_akakce_product(req.url)
        if scraped and scraped.get("lowest_price"):
            top_3 = scraped.get("top_3_sellers", [])
            database.save_price_record(
                product_id=prod_id,
                price=scraped["lowest_price"],
                seller=scraped["lowest_seller"],
                direct_link=scraped["direct_link"],
                cargo_info=scraped.get("cargo", ""),
                raw_price_str=scraped["lowest_price_str"],
                top_sellers=top_3
            )
            if scraped.get("image_url"):
                database.update_product_image(prod_id, scraped["image_url"])
                prod_data["image_url"] = scraped["image_url"]
                try:
                    import urllib.request
                    img_dir = os.path.join(STATIC_DIR, "product_imgs")
                    os.makedirs(img_dir, exist_ok=True)
                    img_file = os.path.join(img_dir, f"{prod_id}.jpg")
                    req_img = urllib.request.Request(scraped["image_url"], headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_img, timeout=6) as r_img:
                        with open(img_file, "wb") as f_img:
                            f_img.write(r_img.read())
                except Exception as e_img:
                    print(f"[App] Yeni ürün görseli indirilemedi: {e_img}")
            if scraped.get("historical_1y"):
                database.save_product_history_cache(
                    product_id=prod_id,
                    points=scraped["historical_1y"],
                    stats=scraped.get("stats_1y", {})
                )
    except Exception as e:
        print(f"İlk tarama hatası: {e}")
        
    return {"status": "success", "product": prod_data}


@app.get("/api/settings")
async def get_settings():
    cfg = scheduler_service.load_config()
    return {
        "daily_report_time": cfg.get("schedule", {}).get("daily_report_time", "10:00"),
        "check_interval_minutes": cfg.get("schedule", {}).get("check_interval_minutes", 60),
        "scheduler_enabled": cfg.get("schedule", {}).get("enabled", True),
        "desktop_enabled": cfg.get("notifications", {}).get("desktop_enabled", True),
        "telegram_enabled": cfg.get("notifications", {}).get("telegram_enabled", False),
        "telegram_bot_token": cfg.get("notifications", {}).get("telegram_bot_token", ""),
        "telegram_chat_id": cfg.get("notifications", {}).get("telegram_chat_id", ""),
        "discord_enabled": cfg.get("notifications", {}).get("discord_enabled", False),
        "discord_webhook_url": cfg.get("notifications", {}).get("discord_webhook_url", "")
    }


@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    cfg = scheduler_service.load_config()
    
    cfg.setdefault("schedule", {})
    cfg["schedule"]["daily_report_time"] = req.daily_report_time
    cfg["schedule"]["check_interval_minutes"] = req.check_interval_minutes
    cfg["schedule"]["enabled"] = req.scheduler_enabled
    
    cfg.setdefault("notifications", {})
    cfg["notifications"]["desktop_enabled"] = req.desktop_enabled
    cfg["notifications"]["telegram_enabled"] = req.telegram_enabled
    cfg["notifications"]["telegram_bot_token"] = req.telegram_bot_token
    cfg["notifications"]["telegram_chat_id"] = req.telegram_chat_id
    cfg["notifications"]["discord_enabled"] = req.discord_enabled
    cfg["notifications"]["discord_webhook_url"] = req.discord_webhook_url
    
    scheduler_service.save_config(cfg)
    # Zamanlayıcıyı yeni ayarlara göre yeniden başlat
    scheduler_service.setup_scheduler()
    
    return {"status": "success", "message": "Ayarlar başarıyla kaydedildi."}


@app.post("/api/test-notification")
async def test_notification(req: TestNotificationRequest):
    cfg = scheduler_service.load_config()
    ch = req.channel.lower()
    
    if ch == "desktop":
        ok = notifier.send_windows_toast(
            "🔔 Akakçe Bildirim Testi",
            "Windows Masaüstü Bildirim sistemi başarıyla çalışıyor!",
            "https://www.akakce.com"
        )
        return {"status": "success" if ok else "failed", "message": "Windows bildirimi gönderildi."}
    elif ch == "telegram":
        token = cfg.get("notifications", {}).get("telegram_bot_token")
        chat_id = cfg.get("notifications", {}).get("telegram_chat_id")
        if not token or not chat_id:
            raise HTTPException(status_code=400, detail="Lütfen önce Telegram Bot Token ve Chat ID girin.")
        ok = notifier.send_telegram_message(
            token, chat_id,
            "🔔 <b>Akakçe Fiyat Takip Test Bildirimi</b>\nTelegram bildirim entegrasyonu kusursuz çalışıyor!"
        )
        return {"status": "success" if ok else "failed", "message": "Telegram mesajı gönderildi." if ok else "Telegram gönderimi başarısız. Bilgilerinizi kontrol edin."}
    elif ch == "discord":
        url = cfg.get("notifications", {}).get("discord_webhook_url")
        if not url:
            raise HTTPException(status_code=400, detail="Lütfen önce Discord Webhook URL girin.")
        ok = notifier.send_discord_webhook(
            url,
            "🔔 Akakçe Fiyat Takip Test Bildirimi",
            "Discord Webhook entegrasyonu kusursuz çalışıyor!"
        )
        return {"status": "success" if ok else "failed", "message": "Discord bildirimi gönderildi." if ok else "Discord gönderimi başarısız."}
    else:
        raise HTTPException(status_code=400, detail="Geçersiz bildirim kanalı")


@app.get("/api/search")
async def search_akakce(q: str):
    if not q:
        return []
    return scraper.search_product_on_akakce(q)
