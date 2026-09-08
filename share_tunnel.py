import os
import sys
import re
import time
import socket
import subprocess
import urllib.request

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def copy_to_clipboard(text: str):
    try:
        proc = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True)
        proc.communicate(text.strip().encode("utf-8"))
    except Exception:
        pass

def is_server_running(port=8000):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 78)
    print("       F&S YAZILIM — AKAKÇE FİYAT TAKİPÇİSİ CANLI İNTERNET PAYLAŞIMI")
    print("=" * 78)
    print("\n[1/3] Sistem kontrol ediliyor...")

    # 1. Ana uygulama açık mı?
    if not is_server_running(8000):
        print("[*] Akakçe Fiyat Takip sunucusu başlatılıyor...")
        py_exe = os.path.join(".venv", "Scripts", "python.exe")
        if not os.path.exists(py_exe):
            py_exe = sys.executable
        subprocess.Popen([py_exe, "run.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        for _ in range(15):
            time.sleep(1)
            if is_server_running(8000):
                break

    if not is_server_running(8000):
        print("\n[!] UYARI: Sunucu başlatılamadı. Lütfen önce 'baslat.bat' dosyasını çalıştırın.")
        input("\nÇıkmak için Enter'a basın...")
        return

    print("[2/3] Güvenli Cloudflare tüneli oluşturuluyor...")
    cloudflared_exe = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
    if not os.path.exists(cloudflared_exe):
        cloudflared_exe = "cloudflared.exe"

    proc = subprocess.Popen(
        [cloudflared_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Stderr üzerinden URL'yi yakala
    start_time = time.time()
    while time.time() - start_time < 25:
        line = proc.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        print("\n[!] Canlı internet linki oluşturulamadı.")
        print("Lütfen internet bağlantınızı kontrol edin veya 'cloudflared.exe' dosyasının varlığından emin olun.")
        input("\nÇıkmak için Enter'a basın...")
        return

    # Panoya kopyala
    copy_to_clipboard(tunnel_url)
    local_ip = get_local_ip()

    print("[3/3] Bağlantı başarıyla kuruldu!")
    print("\n" + "=" * 78)
    print("              🎉 UYGULAMANIZ ŞU ANDA HERKESE AÇIK VE CANLI! 🎉")
    print("=" * 78)
    print("\n  🌍 1. DÜNYANIN HER YERİNDEN ERİŞİM (Babanız, Telefonlar, Mobil Veri):")
    print(f"     👉  {tunnel_url}")
    print("     ✅ [LİNK KOPYALANDI] Doğrudan WhatsApp'ta 'Yapıştır' yapabilirsiniz!")
    print("\n  🏠 2. AYNI EV / WI-FI AĞINDAKİ CİHAZLAR İÇİN YEREL LİNK:")
    print(f"     👉  http://{local_ip}:8000")
    print("\n" + "-" * 78)
    print("  * Babanız bu linke tıkladığında tüm fiyatları, satıcıları ve grafikleri görür.")
    print("  * Bağlantı güvenli, şifreli (HTTPS) ve tamamen ücretsizdir.")
    print("  * Paylaşımı kapatmak için bu pencereyi kapatmanız yeterlidir.")
    print("=" * 78)
    print("\n[Çalışıyor] Paylaşım aktif. Kapatmak için klavyeden Ctrl+C tuşlarına basın...\n")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[Kapatılıyor] Tünel bağlantısı güvenle kapatıldı.")
        proc.terminate()

if __name__ == "__main__":
    main()
