import os
import json
import webbrowser
import requests
from typing import Dict, Any, Optional

try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except ImportError:
    HAS_WINOTIFY = False


def send_windows_toast(title: str, message: str, link: Optional[str] = None, sound: bool = True) -> bool:
    """Windows 10/11 yerel Toast bildirimi gönderir."""
    if not HAS_WINOTIFY:
        print(f"[Bildirim] Windows Toast kütüphanesi bulunamadı. Mesaj: {title} - {message}")
        return False
        
    try:
        toast = Notification(
            app_id="Akakçe Fiyat Takip",
            title=title[:60],
            msg=message[:200],
            duration="long"
        )
        if sound:
            toast.set_audio(audio.Default, loop=False)
            
        if link and link.startswith("http"):
            toast.add_actions(label="🛒 Satıcıya Git", launch=link)
            
        toast.show()
        return True
    except Exception as e:
        print(f"[Bildirim Hatası - Windows Toast]: {e}")
        return False


def send_telegram_message(bot_token: str, chat_id: str, text: str, button_url: Optional[str] = None) -> bool:
    """Telegram botu üzerinden mesaj gönderir."""
    if not bot_token or not chat_id:
        return False
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        if button_url and button_url.startswith("http"):
            payload["reply_markup"] = json.dumps({
                "inline_keyboard": [
                    [{"text": "🛒 Satıcıya Git / Ürünü İncele", "url": button_url}]
                ]
            })
            
        r = requests.post(url, data=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[Bildirim Hatası - Telegram]: {e}")
        return False


def send_discord_webhook(webhook_url: str, title: str, description: str, fields: list = None, link: str = None) -> bool:
    """Discord Webhook üzerinden zengin gömülü (Embed) kart gönderir."""
    if not webhook_url or not webhook_url.startswith("http"):
        return False
        
    try:
        embed = {
            "title": title,
            "description": description,
            "color": 0x10B981,  # Zümrüt yeşili
            "footer": {"text": "Akakçe Otomatik Fiyat Takip Sistemi"}
        }
        if link:
            embed["url"] = link
        if fields:
            embed["fields"] = fields
            
        payload = {
            "username": "Akakçe Fiyat Takipçisi",
            "embeds": [embed]
        }
        r = requests.post(webhook_url, json=payload, timeout=10)
        return r.status_code in [200, 204]
    except Exception as e:
        print(f"[Bildirim Hatası - Discord]: {e}")
        return False


def notify_price_threshold_alarm(
    product_name: str,
    current_price: float,
    threshold_price: float,
    seller: str,
    direct_link: str,
    config: Dict[str, Any]
) -> Dict[str, bool]:
    """
    Fiyat Eşiği Alarmı (Koşullu Takip) tetiklendiğinde tüm aktif kanallara bildirim yollar.
    """
    cfg_notif = config.get("notifications", {})
    results = {"desktop": False, "telegram": False, "discord": False}
    
    cur_fmt = f"{current_price:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
    thr_fmt = f"{threshold_price:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
    
    title = f"🚨 FİYAT DÜŞTÜ ALARMI! ({product_name})"
    message = (
        f"Hedeflediğiniz {thr_fmt} altına indi!\n"
        f"💰 En Düşük Fiyat: {cur_fmt}\n"
        f"🏪 En Ucuz Satıcı: {seller}"
    )
    
    print(f"\n[ALARM TETİKLENDİ] {product_name} - {cur_fmt} (Hedef: {thr_fmt}) - Satıcı: {seller}")
    
    # 1. Windows Masaüstü Bildirimi
    if cfg_notif.get("desktop_enabled", True):
        results["desktop"] = send_windows_toast(title, message, direct_link)
        
    # 2. Telegram Bildirimi
    if cfg_notif.get("telegram_enabled") and cfg_notif.get("telegram_bot_token"):
        tg_text = (
            f"🚨 <b>FİYAT DÜŞTÜ ALARMI!</b>\n\n"
            f"📦 <b>Ürün:</b> {product_name}\n"
            f"🎯 <b>Hedef Eşik:</b> {thr_fmt}\n"
            f"💰 <b>Anlık Fiyat:</b> <code>{cur_fmt}</code>\n"
            f"🏪 <b>Satıcı:</b> {seller}\n"
            f"🔗 <a href='{direct_link}'>Doğrudan Satıcıya Git</a>"
        )
        results["telegram"] = send_telegram_message(
            cfg_notif.get("telegram_bot_token"),
            cfg_notif.get("telegram_chat_id"),
            tg_text,
            direct_link
        )
        
    # 3. Discord Bildirimi
    if cfg_notif.get("discord_enabled") and cfg_notif.get("discord_webhook_url"):
        fields = [
            {"name": "Anlık En Düşük Fiyat", "value": cur_fmt, "inline": True},
            {"name": "Hedeflenen Eşik", "value": thr_fmt, "inline": True},
            {"name": "Satıcı", "value": seller, "inline": True},
        ]
        results["discord"] = send_discord_webhook(
            cfg_notif.get("discord_webhook_url"),
            f"🚨 Fiyat Alarmı: {product_name}",
            f"Ürün belirlediğiniz eşiğin ({thr_fmt}) altına düştü!",
            fields,
            direct_link
        )
        
    return results


def notify_daily_report(
    summary_text: str,
    reports_list: list,
    config: Dict[str, Any]
) -> Dict[str, bool]:
    """
    Her gün saat 10:00'da oluşturulan özet raporu bildirir.
    """
    cfg_notif = config.get("notifications", {})
    results = {"desktop": False, "telegram": False, "discord": False}
    
    title = "📊 Akakçe Günlük Fiyat Raporu (10:00)"
    short_msg = summary_text[:180] + ("..." if len(summary_text) > 180 else "")
    
    # 1. Windows Masaüstü Bildirimi
    if cfg_notif.get("desktop_enabled", True):
        results["desktop"] = send_windows_toast(
            title, 
            short_msg, 
            f"http://localhost:{config.get('server', {}).get('port', 8000)}"
        )
        
    # 2. Telegram Bildirimi
    if cfg_notif.get("telegram_enabled") and cfg_notif.get("telegram_bot_token"):
        tg_text = f"📊 <b>GÜNLÜK FİYAT VE KAMPANYA RAPORU (10:00)</b>\n\n{summary_text}"
        results["telegram"] = send_telegram_message(
            cfg_notif.get("telegram_bot_token"),
            cfg_notif.get("telegram_chat_id"),
            tg_text
        )
        
    # 3. Discord Bildirimi
    if cfg_notif.get("discord_enabled") and cfg_notif.get("discord_webhook_url"):
        fields = []
        for r in reports_list:
            diff_str = f"{r.get('price_diff', 0):+,.2f} TL (%{r.get('price_diff_percent', 0):+.1f})".replace(",", "X").replace(".", ",").replace("X", ".")
            fields.append({
                "name": f"{r.get('product_name', 'Ürün')} ({r.get('product_capacity', '')})",
                "value": f"Fiyat: {r.get('current_price_str', '')} ({diff_str})\nSatıcı: {r.get('current_seller', '')}",
                "inline": False
            })
            
        results["discord"] = send_discord_webhook(
            cfg_notif.get("discord_webhook_url"),
            "📊 Günlük Fiyat Değişim ve Kampanya Özeti",
            "Saat 10:00 otomatik taraması tamamlandı.",
            fields
        )
        
    return results
