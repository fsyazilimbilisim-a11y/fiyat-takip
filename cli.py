import argparse
import json
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import database
import scraper
import scheduler_service
import notifier


def print_banner():
    print("=" * 65)
    print("   Akakçe Samsung 990 EVO Plus Fiyat Takip & Alarm CLI")
    print("=" * 65)


def cmd_check(args):
    print("\n[+] Akakçe canlı fiyat kontrolü başlatılıyor...\n")
    res = scheduler_service.run_check_cycle(is_daily_report=False)
    print("-" * 65)
    for r in res.get("results", []):
        print(f"📦 Ürün: {r['name']} ({r.get('capacity', '')})")
        print(f"💰 En Düşük Fiyat: {r['price_str']} | Satıcı: {r['seller']}")
        print(f"🔗 Satıcı Linki: {r['direct_link']}")
        if r.get("alarm_triggered"):
            print("🚨 [DİKKAT] Belirlediğiniz eşik fiyatının altında! Alarm gönderildi.")
        if r.get("campaign_notes"):
            print(f"📊 Notlar:\n{r['campaign_notes']}")
        print("-" * 65)


def cmd_report(args):
    print("\n[+] Saat 10:00 Günlük Fiyat ve Kampanya Raporu simüle ediliyor...\n")
    res = scheduler_service.run_check_cycle(is_daily_report=True)
    print("\n[+] Rapor başarıyla oluşturuldu, veri tabanına kaydedildi ve bildirimler iletildi.")


def cmd_test_alarm(args):
    print("\n[+] Test Fiyat Alarmı Bildirimi Gönderiliyor...")
    cfg = scheduler_service.load_config()
    res = notifier.notify_price_threshold_alarm(
        product_name="Samsung 990 EVO Plus 1TB (TEST)",
        current_price=3399.00,
        threshold_price=3500.00,
        seller="Amazon Türkiye (Test)",
        direct_link="https://www.akakce.com/ssd/en-ucuz-samsung-990-evo-plus-mz-v9s1t0bw-pci-express-1-tb-m-2-fiyati,836325211.html",
        config=cfg
    )
    print(f"Sonuç: Windows Toast: {res.get('desktop')}, Telegram: {res.get('telegram')}, Discord: {res.get('discord')}")


def cmd_set_threshold(args):
    prod_id = args.product_id
    val = float(args.price)
    
    # Kısayol kontrolü: '1tb', '2tb'
    if prod_id.lower() == "1tb":
        prod_id = "samsung-990-evo-plus-1tb"
    elif prod_id.lower() == "2tb":
        prod_id = "samsung-990-evo-plus-2tb"
        
    database.init_db()
    database.update_product_threshold(prod_id, val)
    print(f"[+] {prod_id} için yeni alarm eşiği {val:,.2f} TL olarak ayarlandı.")


def cmd_search(args):
    q = args.query
    print(f"\n[+] Akakçe'de aranıyor: '{q}'...\n")
    items = scraper.search_product_on_akakce(q)
    if not items:
        print("Sonuç bulunamadı.")
        return
    for idx, item in enumerate(items, 1):
        print(f"{idx}. {item['title']}")
        print(f"   Fiyat: {item['price_str']} | URL: {item['url']}\n")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Akakçe Fiyat Takip ve Alarm Yönetim Aracı")
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")
    
    subparsers.add_parser("check", help="Canlı fiyat kontrolü yap ve ekrana bas")
    subparsers.add_parser("report", help="Saat 10:00 Günlük Raporunu şimdi oluştur ve bildir")
    subparsers.add_parser("test-alarm", help="Örnek bir eşik alarmı bildirimi gönder")
    
    set_parser = subparsers.add_parser("set-threshold", help="Ürün için alarm eşiği belirle")
    set_parser.add_argument("product_id", help="Ürün ID veya kısayol ('1tb', '2tb')")
    set_parser.add_argument("price", type=float, help="Hedef eşik fiyat (örn: 3500)")
    
    search_parser = subparsers.add_parser("search", help="Akakçe'de ürün ara")
    search_parser.add_argument("query", help="Arama kelimesi")
    
    args = parser.parse_args()
    
    # DB hazırla
    database.init_db()
    cfg = scheduler_service.load_config()
    if cfg.get("products"):
        database.sync_products_from_config(cfg["products"])
        
    if args.command == "check":
        cmd_check(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "test-alarm":
        cmd_test_alarm(args)
    elif args.command == "set-threshold":
        cmd_set_threshold(args)
    elif args.command == "search":
        cmd_search(args)
    else:
        # Argümansız çağrılırsa varsayılan check yap
        cmd_check(args)


if __name__ == "__main__":
    main()
