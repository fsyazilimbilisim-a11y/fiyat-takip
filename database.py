import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "akakce_tracker.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    """Veritabanı tablolarını ilklendirir."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Ürünler tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'SSD & Depolama',
                capacity TEXT,
                url TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                threshold_price REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'SSD & Depolama'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        
        # Fiyat geçmişi tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                price REAL NOT NULL,
                seller TEXT,
                direct_link TEXT,
                cargo_info TEXT,
                raw_price_str TEXT,
                top_sellers TEXT DEFAULT '[]',
                checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE price_history ADD COLUMN top_sellers TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass
        
        # Günlük 10:00 özet raporları tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL,
                product_id TEXT NOT NULL,
                current_price REAL NOT NULL,
                yesterday_price REAL,
                price_diff REAL,
                price_diff_percent REAL,
                current_seller TEXT,
                yesterday_seller TEXT,
                campaign_notes TEXT,
                summary_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        
        # Fiyat eşiği alarm tetiklenme logları
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarm_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                trigger_price REAL NOT NULL,
                threshold_price REAL NOT NULL,
                seller TEXT,
                direct_link TEXT,
                triggered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                notified_desktop INTEGER DEFAULT 0,
                notified_telegram INTEGER DEFAULT 0,
                notified_discord INTEGER DEFAULT 0,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        
        # Akakçe son 1 yıllık tarihsel grafik ve istatistik önbelleği
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_historical_cache (
                product_id TEXT PRIMARY KEY,
                points_json TEXT NOT NULL,
                stats_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        
        conn.commit()


def sync_products_from_config(products_list: List[Dict[str, Any]]):
    """config.json içerisindeki varsayılan ürünleri veritabanına ekler veya günceller."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for p in products_list:
            cursor.execute("""
                INSERT INTO products (id, name, category, capacity, url, image_url, threshold_price, is_active)
                VALUES (:id, :name, :category, :capacity, :url, :image_url, :threshold_price, :is_active)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    capacity = excluded.capacity,
                    url = excluded.url,
                    image_url = CASE WHEN excluded.image_url != '' THEN excluded.image_url ELSE products.image_url END,
                    threshold_price = CASE WHEN products.threshold_price = 0 THEN excluded.threshold_price ELSE products.threshold_price END
            """, {
                "id": p["id"],
                "name": p["name"],
                "category": p.get("category", "SSD & Depolama"),
                "capacity": p.get("capacity", ""),
                "url": p["url"],
                "image_url": p.get("image_url", ""),
                "threshold_price": float(p.get("threshold_price", 0.0)),
                "is_active": 1 if p.get("is_active", True) else 0
            })
        conn.commit()


def get_all_products(only_active: bool = False) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM products"
        if only_active:
            query += " WHERE is_active = 1"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_or_update_product(product: Dict[str, Any]):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (id, name, category, capacity, url, image_url, threshold_price, is_active)
            VALUES (:id, :name, :category, :capacity, :url, :image_url, :threshold_price, :is_active)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                capacity = excluded.capacity,
                url = excluded.url,
                image_url = CASE WHEN excluded.image_url != '' THEN excluded.image_url ELSE products.image_url END,
                threshold_price = excluded.threshold_price,
                is_active = excluded.is_active
        """, {
            "id": product["id"],
            "name": product["name"],
            "category": product.get("category", "SSD & Depolama"),
            "capacity": product.get("capacity", ""),
            "url": product["url"],
            "image_url": product.get("image_url", ""),
            "threshold_price": float(product.get("threshold_price", 0.0)),
            "is_active": 1 if product.get("is_active", True) else 0
        })
        conn.commit()


def update_product_image(product_id: str, image_url: str):
    if not image_url:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET image_url = ? WHERE id = ?", (image_url, product_id))
        conn.commit()


def update_product_threshold(product_id: str, threshold: float):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET threshold_price = ? WHERE id = ?", (threshold, product_id))
        conn.commit()


def toggle_product_active(product_id: str, is_active: bool):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET is_active = ? WHERE id = ?", (1 if is_active else 0, product_id))
        conn.commit()


def save_price_record(product_id: str, price: float, seller: str, direct_link: str, cargo_info: str, raw_price_str: str, top_sellers: Optional[List[Dict[str, Any]]] = None) -> int:
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sellers_json = json.dumps(top_sellers, ensure_ascii=False) if top_sellers else "[]"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_history (product_id, price, seller, direct_link, cargo_info, raw_price_str, top_sellers, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (product_id, price, seller, direct_link, cargo_info, raw_price_str, sellers_json, checked_at))
        conn.commit()
        return cursor.lastrowid


def get_latest_price(product_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history 
            WHERE product_id = ? 
            ORDER BY checked_at DESC LIMIT 1
        """, (product_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        top_sellers_raw = res.get("top_sellers")
        if top_sellers_raw:
            try:
                res["top_sellers"] = json.loads(top_sellers_raw)
            except Exception:
                res["top_sellers"] = []
        else:
            res["top_sellers"] = []
        return res


def get_yesterday_price(product_id: str) -> Optional[Dict[str, Any]]:
    """Dünkü (veya son 24 saatten önceki son kayıt) fiyat kaydını döndürür."""
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Önce dün tarihli bir kayıt var mı bakalım
        cursor.execute("""
            SELECT * FROM price_history
            WHERE product_id = ? AND date(checked_at) = ?
            ORDER BY checked_at DESC LIMIT 1
        """, (product_id, yesterday_str))
        row = cursor.fetchone()
        
        if not row:
            # Dün yoksa, 20 saat öncesinden daha eski en son kaydı bul
            cutoff = (datetime.now() - timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                SELECT * FROM price_history
                WHERE product_id = ? AND checked_at <= ?
                ORDER BY checked_at DESC LIMIT 1
            """, (product_id, cutoff))
            row = cursor.fetchone()
            
        if not row:
            # En son kayıttan bir önceki kaydı getir
            cursor.execute("""
                SELECT * FROM price_history
                WHERE product_id = ?
                ORDER BY checked_at DESC LIMIT 1 OFFSET 1
            """, (product_id,))
            row = cursor.fetchone()
            
        return dict(row) if row else None


def get_price_history(product_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history
            WHERE product_id = ?
            ORDER BY checked_at ASC
        """, (product_id,))
        rows = cursor.fetchall()
        # Son 'limit' tanesini döndür
        return [dict(r) for r in rows[-limit:]]


def save_daily_report(report_data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO daily_reports (
                report_date, product_id, current_price, yesterday_price,
                price_diff, price_diff_percent, current_seller, yesterday_seller,
                campaign_notes, summary_text, created_at
            ) VALUES (
                :report_date, :product_id, :current_price, :yesterday_price,
                :price_diff, :price_diff_percent, :current_seller, :yesterday_seller,
                :campaign_notes, :summary_text, :created_at
            )
        """, report_data)
        conn.commit()
        return cursor.lastrowid


def get_latest_reports(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, p.name as product_name, p.capacity as product_capacity 
            FROM daily_reports r
            LEFT JOIN products p ON r.product_id = p.id
            ORDER BY r.created_at DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]


def save_alarm_log(alarm_data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alarm_logs (
                product_id, trigger_price, threshold_price, seller, direct_link,
                triggered_at, notified_desktop, notified_telegram, notified_discord
            ) VALUES (
                :product_id, :trigger_price, :threshold_price, :seller, :direct_link,
                :triggered_at, :notified_desktop, :notified_telegram, :notified_discord
            )
        """, alarm_data)
        conn.commit()
        return cursor.lastrowid


def get_recent_alarms(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, p.name as product_name, p.capacity as product_capacity
            FROM alarm_logs a
            LEFT JOIN products p ON a.product_id = p.id
            ORDER BY a.triggered_at DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]


def save_product_history_cache(product_id: str, points: List[Dict[str, Any]], stats: Dict[str, Any]):
    """Akakçe'den çekilen son 1 yıllık fiyat noktalarını ve istatistiklerini kaydeder."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO product_historical_cache (product_id, points_json, stats_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(product_id) DO UPDATE SET
                points_json = excluded.points_json,
                stats_json = excluded.stats_json,
                updated_at = CURRENT_TIMESTAMP
        """, (product_id, json.dumps(points, ensure_ascii=False), json.dumps(stats, ensure_ascii=False)))
        conn.commit()


def get_product_history_cache(product_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM product_historical_cache WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "product_id": row["product_id"],
            "points": json.loads(row["points_json"]),
            "stats": json.loads(row["stats_json"]),
            "updated_at": row["updated_at"]
        }

