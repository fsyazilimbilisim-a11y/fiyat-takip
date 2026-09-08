import os
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import database
import scraper
import notifier

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
scheduler: Optional[BackgroundScheduler] = None


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Okuma hatası: {e}")
    return {}


def save_config(config_data: Dict[str, Any]):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] Kaydetme hatası: {e}")


def format_currency(val: float) -> str:
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def run_check_cycle(is_daily_report: bool = False) -> Dict[str, Any]:
    """
    Tüm aktif ürünler için Akakçe fiyat kontrolünü çalıştırır.
    - Eşik alarmı varsa anında tetikler.
    - is_daily_report=True ise düne göre fiyat farkı hesaplayıp 10:00 özet raporu üretir.
    """
    config = load_config()
    products = database.get_all_products(only_active=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    results = []
    report_items = []
    daily_summaries = []
    
    print(f"\n[{now_str}] Fiyat kontrol döngüsü başladı. (Günlük Rapor Modu: {is_daily_report})")
    
    for prod in products:
        prod_id = prod["id"]
        prod_name = prod["name"]
        prod_cap = prod.get("capacity", "")
        threshold = float(prod.get("threshold_price") or 0.0)
        
        print(f"-> Akakçe taranıyor: {prod_name} ({prod['url']})")
        scraped = scraper.scrape_akakce_product(prod["url"])
        
        if not scraped:
            print(f"   [HATA] {prod_name} için Akakçe bilgisi alınamadı.")
            continue
            
        cur_price = scraped["lowest_price"]
        cur_seller = scraped["lowest_seller"]
        cur_link = scraped["direct_link"]
        cur_cargo = scraped.get("cargo", "")
        
        # 1. Fiyat kaydını veritabanına ekle
        top_3 = scraped.get("top_3_sellers", [])
        database.save_price_record(
            product_id=prod_id,
            price=cur_price,
            seller=cur_seller,
            direct_link=cur_link,
            cargo_info=cur_cargo,
            raw_price_str=scraped["lowest_price_str"],
            top_sellers=top_3
        )
        
        # 1.1 Ürün görselini güncelle (varsa)
        if scraped.get("image_url"):
            database.update_product_image(prod_id, scraped["image_url"])
        
        # 1.2 Akakçe son 1 yıllık tarihsel verilerini kaydet
        if scraped.get("historical_1y"):
            database.save_product_history_cache(
                product_id=prod_id,
                points=scraped["historical_1y"],
                stats=scraped.get("stats_1y", {})
            )
        
        # 2. Fiyat Eşiği Alarm Kontrolü (Koşullu Takip)
        alarm_triggered = False
        if threshold > 0 and cur_price <= threshold:
            alarm_triggered = True
            notif_res = notifier.notify_price_threshold_alarm(
                product_name=f"{prod_name} {prod_cap}".strip(),
                current_price=cur_price,
                threshold_price=threshold,
                seller=cur_seller,
                direct_link=cur_link,
                config=config
            )
            database.save_alarm_log({
                "product_id": prod_id,
                "trigger_price": cur_price,
                "threshold_price": threshold,
                "seller": cur_seller,
                "direct_link": cur_link,
                "triggered_at": now_str,
                "notified_desktop": 1 if notif_res.get("desktop") else 0,
                "notified_telegram": 1 if notif_res.get("telegram") else 0,
                "notified_discord": 1 if notif_res.get("discord") else 0
            })
            
        # 3. Düne göre karşılaştırma ve Günlük Rapor Hazırlığı
        yesterday_record = database.get_yesterday_price(prod_id)
        yesterday_price = yesterday_record["price"] if yesterday_record else None
        yesterday_seller = yesterday_record["seller"] if yesterday_record else "-"
        
        price_diff = 0.0
        diff_pct = 0.0
        campaign_notes = []
        
        if yesterday_price is not None:
            price_diff = cur_price - yesterday_price
            if yesterday_price > 0:
                diff_pct = (price_diff / yesterday_price) * 100
                
            if price_diff < 0:
                campaign_notes.append(f"🔥 İNDİRİM: Fiyat düne göre {format_currency(abs(price_diff))} (%{abs(diff_pct):.1f}) düştü!")
            elif price_diff > 0:
                campaign_notes.append(f"📈 Fiyat düne göre +{format_currency(price_diff)} (%{diff_pct:+.1f}) arttı.")
            else:
                campaign_notes.append("⚖️ Fiyat düne göre değişmedi (aynı seviyede).")
                
            if cur_seller != yesterday_seller and yesterday_seller != "-":
                campaign_notes.append(f"🔄 Satıcı değişti: Eski ({yesterday_seller}) ➔ Yeni ({cur_seller})")
        else:
            campaign_notes.append("ℹ️ İlk fiyat kaydı alındı. Düne ait önceki kayıt bulunmuyor.")
            
        campaign_text = "\n".join(campaign_notes)
        
        summary_line = (
            f"• {prod_name} ({prod_cap}):\n"
            f"  - Güncel En Ucuz: {format_currency(cur_price)} ({cur_seller})\n"
            f"  - Dünkü Fiyat: {format_currency(yesterday_price) if yesterday_price else 'Kayıt Yok'}\n"
            f"  - Durum: {campaign_text.replace(chr(10), ' ')}"
        )
        daily_summaries.append(summary_line)
        
        report_item = {
            "report_date": today_str,
            "product_id": prod_id,
            "product_name": prod_name,
            "product_capacity": prod_cap,
            "current_price": cur_price,
            "current_price_str": format_currency(cur_price),
            "yesterday_price": yesterday_price,
            "yesterday_price_str": format_currency(yesterday_price) if yesterday_price else "-",
            "price_diff": price_diff,
            "price_diff_percent": round(diff_pct, 2),
            "current_seller": cur_seller,
            "yesterday_seller": yesterday_seller,
            "campaign_notes": campaign_text,
            "summary_text": summary_line,
            "direct_link": cur_link,
            "created_at": now_str,
            "alarm_triggered": alarm_triggered
        }
        report_items.append(report_item)
        
        # Günlük rapor kaydı
        if is_daily_report:
            database.save_daily_report({
                "report_date": today_str,
                "product_id": prod_id,
                "current_price": cur_price,
                "yesterday_price": yesterday_price,
                "price_diff": price_diff,
                "price_diff_percent": round(diff_pct, 2),
                "current_seller": cur_seller,
                "yesterday_seller": yesterday_seller,
                "campaign_notes": campaign_text,
                "summary_text": summary_line,
                "created_at": now_str
            })
            
        results.append({
            "product_id": prod_id,
            "name": prod_name,
            "capacity": prod_cap,
            "price": cur_price,
            "price_str": format_currency(cur_price),
            "seller": cur_seller,
            "direct_link": cur_link,
            "yesterday_price": yesterday_price,
            "price_diff": price_diff,
            "price_diff_percent": round(diff_pct, 2),
            "campaign_notes": campaign_text,
            "alarm_triggered": alarm_triggered
        })
        time.sleep(2.0)

    # Günlük rapor modu ise toplu bildirim gönder
    if is_daily_report and daily_summaries:
        full_summary = "\n\n".join(daily_summaries)
        notifier.notify_daily_report(full_summary, report_items, config)
        
    return {
        "status": "success",
        "timestamp": now_str,
        "is_daily_report": is_daily_report,
        "results": results
    }


def scheduled_daily_report_job():
    """Her gün saat 10:00'da çağrılan otomatik raporlama fonksiyonu."""
    print("\n[ZAMANLANMIŞ GÖREV] Saat 10:00 Günlük Fiyat Raporu Hazırlanıyor...")
    run_check_cycle(is_daily_report=True)


def scheduled_threshold_check_job():
    """Periyodik aralıklarla eşik alarmı kontrolü yapan fonksiyon."""
    print("\n[PERİYODİK GÖREV] Eşik Alarmı ve Güncel Fiyat Taraması...")
    run_check_cycle(is_daily_report=False)


def setup_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        
    config = load_config()
    sched_cfg = config.get("schedule", {})
    if not sched_cfg.get("enabled", True):
        print("[Scheduler] Zamanlayıcı ayarlarda devre dışı bırakılmış.")
        return None
        
    scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    
    # 1. Saat 10:00 Günlük Rapor Görevi
    daily_time = sched_cfg.get("daily_report_time", "10:00")
    try:
        hour, minute = map(int, daily_time.split(":"))
    except Exception:
        hour, minute = 10, 0
        
    scheduler.add_job(
        scheduled_daily_report_job,
        CronTrigger(hour=hour, minute=minute),
        id="daily_10am_report",
        name="Günlük 10:00 Fiyat Raporu",
        replace_existing=True
    )
    print(f"[Scheduler] Günlük rapor görevi her gün saat {hour:02d}:{minute:02d} için kuruldu.")
    
    # 2. Periyodik Eşik Kontrolü
    interval_mins = int(sched_cfg.get("check_interval_minutes", 60))
    scheduler.add_job(
        scheduled_threshold_check_job,
        IntervalTrigger(minutes=interval_mins),
        id="periodic_threshold_check",
        name="Periyodik Eşik Kontrolü",
        replace_existing=True
    )
    print(f"[Scheduler] Periyodik eşik kontrolü her {interval_mins} dakikada bir çalışacak şekilde kuruldu.")
    
    scheduler.start()
    return scheduler
