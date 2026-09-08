import os
import sys
import time
import threading
import webbrowser
import uvicorn
import scheduler_service

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_browser(url: str):
    time.sleep(1.5)
    print(f"\n[Tarayıcı] Kontrol paneli açılıyor: {url}")
    webbrowser.open(url)

def main():
    print("=" * 70)
    print("   F&S Yazılım — Akakçe Akıllı Fiyat Takip & Alarm Başlatılıyor")
    print("=" * 70)
    
    cfg = scheduler_service.load_config()
    server_cfg = cfg.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8000)
    local_ip = get_local_ip()
    
    # Tarayıcıyı arka planda otomatik aç (localhost olarak)
    browser_url = f"http://localhost:{port}"
    threading.Thread(target=open_browser, args=(browser_url,), daemon=True).start()
    
    print(f"\n[*] Bu Bilgisayar İçin:            {browser_url}")
    print(f"[*] Babanız / Aynı Wi-Fi Ağındakiler: http://{local_ip}:{port}")
    print("[*] İnternet Üzerinden Paylaşmak İçin: 'paylas_internete_ac.bat' dosyasını açın.")
    print("[*] Durdurmak için pencerede Ctrl+C tuşlarına basın.\n")
    
    uvicorn.run("app:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
