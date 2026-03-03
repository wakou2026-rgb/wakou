from __future__ import annotations

from datetime import datetime, timezone
import importlib
import os
import threading
from typing import Any

from sqlalchemy import delete, select

from app.core.helpers import _append_event, _append_shipment_event, _inquiry_reminder_loop, _slugify
from app.core.state import *
import app.core.state as state


db_module = importlib.import_module("app.core.db")
auth_models = importlib.import_module("app.modules.auth.models")
auth_service = importlib.import_module("app.modules.auth.service")
product_models = importlib.import_module("app.modules.products.models")
magazine_models = importlib.import_module("app.modules.magazines.models")
categories_model_module = importlib.import_module("app.modules.categories.models")
costs_model_module = importlib.import_module("app.modules.costs.models")

Base = db_module.Base
SessionLocal = db_module.SessionLocal
engine = db_module.engine
User = auth_models.User
register_user = auth_service.register_user
Product = product_models.Product
MagazineArticle = magazine_models.MagazineArticle
Category = categories_model_module.Category
Cost = costs_model_module.Cost


def _run_migrations() -> None:  # noqa: WPS430
    """Apply any ad-hoc ALTER TABLE migrations not covered by create_all."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE magazine_articles "
                "ADD COLUMN layout_blocks_json LONGTEXT NOT NULL DEFAULT '[]'"
            ))
            conn.commit()
        except OperationalError:
            # Column already exists — safe to ignore
            pass



def _start_inquiry_reminder_worker() -> None:  # noqa: WPS430
    if state._inquiry_reminder_thread_started:
        return
    worker = threading.Thread(target=_inquiry_reminder_loop, daemon=True, name="wakou-inquiry-reminder")
    worker.start()
    state._inquiry_reminder_thread_started = True

def reset_state() -> None:

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.execute(delete(User))
        session.execute(delete(Product))
        session.add_all(
            [
                Product(
                    sku="WK-WATCH-001",
                    category="watch",
                    name_zh_hant="Rolex Submariner 5513",
                    name_ja="ロレックス サブマリーナ 5513",
                    name_en="Rolex Submariner 5513",
                    price_twd=380000,
                    grade="A",
                    description_zh="經典潛水錶款，面盤帶有迷人岁月痕跡。",
                    description_ja="美しいエイジング文字盤を持つクラシックなダイバーズウォッチ。",
                    description_en="Classic dive watch with a beautifully aged dial.",
                ),
                Product(
                    sku="WK-BAG-001",
                    category="bag",
                    name_zh_hant="Vintage Hermès Kelly 32",
                    name_ja="ヴィンテージ エルメス ケリー 32",
                    name_en="Vintage Hermès Kelly 32",
                    price_twd=420000,
                    grade="B",
                    description_zh="稀有皮質與五金，歷經岁月更顯優雅。",
                    description_ja="希少なレザーと金具、時を経てさらに優雅さを増す逸品。",
                    description_en="Rare leather and hardware, aging gracefully over time.",
                ),
                Product(
                    sku="WK-JEWELRY-001",
                    category="jewelry",
                    name_zh_hant="Tiffany & Co. 古董珍珠項錢",
                    name_ja="Tiffany & Co. アンティークパールネックレス",
                    name_en="Tiffany & Co. Antique Pearl Necklace",
                    price_twd=68000,
                    grade="A",
                    description_zh="典雅珍珠搭配復古鉤扣，跨越時代的經典設計。",
                    description_ja="エレガントなパールとヴィンテージクラスプ、時代を超える名品。",
                    description_en="Elegant pearls with vintage clasp, a timeless design.",
                ),
                Product(
                    sku="WK-APPAREL-001",
                    category="apparel",
                    name_zh_hant="Seven by Seven 重製丹寧外套",
                    name_ja="Seven by Seven 再構築デニムジャケット",
                    name_en="Seven by Seven Reconstructed Denim Jacket",
                    price_twd=18500,
                    grade="S",
                    description_zh="手工拆解拼接老丹寧，每件皆1独一無二。",
                    description_ja="手作業で解体・再構築されたヴィンテージデニム。すべてが一点物。",
                    description_en="Hand-deconstructed vintage denim. Each piece is unique.",
                ),
                Product(
                    sku="WK-LIFESTYLE-001",
                    category="lifestyle",
                    name_zh_hant="昭和銅製花器",
                    name_ja="昭和銅製花器",
                    name_en="Showa-era Copper Flower Vase",
                    price_twd=12500,
                    grade="A",
                    description_zh="昭和時期手工鍛造，銅面隨岁月生成獨特綠青。",
                    description_ja="昭和時代の手打ち銅器、経年の綠青が独特の味わいを醇す。",
                    description_en="Hand-forged in the Showa era, copper patina tells its own story.",
                ),
                Product(
                    sku="WK-ACC-001",
                    category="accessory",
                    name_zh_hant="Vintage Cartier 絲巾",
                    name_ja="ヴィンテージ カルティエ スカーフ",
                    name_en="Vintage Cartier Silk Scarf",
                    price_twd=9800,
                    grade="S",
                    description_zh="法式優雅印花絲巾，品相如新的珍稀品。",
                    description_ja="フレンチエレガンスのシルクスカーフ、極美品。",
                    description_en="French-elegant silk scarf in pristine condition.",
                )
            ]
        )
        session.commit()
        register_user(session, "admin@wakou-demo.com", "admin123", "admin")
        register_user(session, "user@wakou-demo.com", "user123", "buyer")
        register_user(session, "sales@wakou-demo.com", "sales123", "sales")
        register_user(session, "maint@wakou-demo.com", "maint123", "maintenance")
        register_user(session, "vip@wakou-demo.com", "vip123", "buyer")
        # 示範買家帳戶
        register_user(session, "yuki@demo.com", "demo123", "buyer")
        register_user(session, "kenji@demo.com", "demo123", "buyer")
        register_user(session, "mei@demo.com", "demo123", "buyer")
        # 設定示範買家的顯示名稱
        for email, name in [("yuki@demo.com", "佐藤 ゆき"), ("kenji@demo.com", "田中 健司"), ("mei@demo.com", "林 美惠")]:
            u = session.scalar(select(User).where(User.email == email))
            if u:
                u.display_name = name
        session.commit()
    finally:
        session.close()
    state.reset_state()

    PRODUCTS.extend([
        {
            "id": 1, "sku": "WK-WATCH-001", "category": "watch",
            "name": {"zh-Hant": "Rolex Submariner 5513", "ja": "ロレックス サブマリーナ 5513", "en": "Rolex Submariner 5513"},
            "price_twd": 380000, "grade": "A",
            "image_urls": ["/Watches.png"],
            "description": {"zh-Hant": "經典潛水錶款，面盤帶有迷人歲月痕跡。", "ja": "美しいエイジング文字盤を持つクラシックなダイバーズウォッチ。", "en": "Classic dive watch with a beautifully aged dial."},
        },
        {
            "id": 2, "sku": "WK-BAG-001", "category": "bag",
            "name": {"zh-Hant": "Vintage Hermès Kelly 32", "ja": "ヴィンテージ エルメス ケリー 32", "en": "Vintage Hermès Kelly 32"},
            "price_twd": 420000, "grade": "B",
            "image_urls": ["/Handbags.png"],
            "description": {"zh-Hant": "稀有皮質與五金，歷經歲月更顯優雅。", "ja": "希少なレザーと金具、時を経てさらに優雅さを増す逸品。", "en": "Rare leather and hardware, aging gracefully over time."},
        },
        {
            "id": 3, "sku": "WK-JEWELRY-001", "category": "jewelry",
            "name": {"zh-Hant": "Tiffany & Co. 古董珍珠項鍊", "ja": "Tiffany & Co. アンティークパールネックレス", "en": "Tiffany & Co. Antique Pearl Necklace"},
            "price_twd": 68000, "grade": "A",
            "image_urls": ["/Jewelry.png"],
            "description": {"zh-Hant": "典雅珍珠搭配復古鍊扣，跨越時代的經典設計。", "ja": "エレガントなパールとヴィンテージクラスプ、時代を超える名品。", "en": "Elegant pearls with vintage clasp, a timeless design."},
        },
        {
            "id": 4, "sku": "WK-APPAREL-001", "category": "apparel",
            "name": {"zh-Hant": "Seven by Seven 重製丹寧外套", "ja": "Seven by Seven 再構築デニムジャケット", "en": "Seven by Seven Reconstructed Denim Jacket"},
            "price_twd": 18500, "grade": "S",
            "image_urls": ["/Apparel.png"],
            "description": {"zh-Hant": "手工拆解拼接老丹寧，每件皆獨一無二。", "ja": "手作業で解体・再構築されたヴィンテージデニム。すべてが一点物。", "en": "Hand-deconstructed vintage denim. Each piece is unique."},
        },
        {
            "id": 5, "sku": "WK-LIFESTYLE-001", "category": "lifestyle",
            "name": {"zh-Hant": "昭和銅製花器", "ja": "昭和銅製花器", "en": "Showa-era Copper Flower Vase"},
            "price_twd": 12500, "grade": "A",
            "image_urls": ["/Lifestyle.png"],
            "description": {"zh-Hant": "昭和時期手工鍛造，銅面隨歲月生成獨特綠青。", "ja": "昭和時代の手打ち銅器、経年の緑青が独特の味わいを醸す。", "en": "Hand-forged in the Showa era, copper patina tells its own story."},
        },
        {
            "id": 6, "sku": "WK-ACC-001", "category": "accessory",
            "name": {"zh-Hant": "Vintage Cartier 絲巾", "ja": "ヴィンテージ カルティエ スカーフ", "en": "Vintage Cartier Silk Scarf"},
            "price_twd": 9800, "grade": "S",
            "image_urls": ["/Wallets.png"],
            "description": {"zh-Hant": "法式優雅印花絲巾，品相如新的珍稀品。", "ja": "フレンチエレガンスのシルクスカーフ、極美品。", "en": "French-elegant silk scarf in pristine condition."},
        },
    ])
    WAREHOUSE_LOGS.extend(
        [
            {
                "id": 1,
                "arrived_at": "2026-02-28T09:15:00Z",
                "source_city": "Tokyo",
                "product_name": "Rolex Submariner 5513 アンティーク",
                "image_url": "https://images.unsplash.com/photo-1547996160-81dfa63595aa?w=600&q=80",
                "category": "watch",
                "description": "1968年製造，原裝表盤，狀態極佳",
            },
            {
                "id": 2,
                "arrived_at": "2026-02-27T14:30:00Z",
                "source_city": "Osaka",
                "product_name": "Hermès Kelly 32 ヴィンテージ",
                "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80",
                "category": "bag",
                "description": "奶油色 Togo 皮革，金色五金，附原廠盒",
            },
            {
                "id": 3,
                "arrived_at": "2026-02-26T11:00:00Z",
                "source_city": "Tokyo",
                "product_name": "Leica M3 クラシックカメラ",
                "image_url": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&q=80",
                "category": "camera",
                "description": "1955年單捲軸版本，附 Summicron 50mm f/2 鏡頭",
            },
            {
                "id": 4,
                "arrived_at": "2026-02-25T16:45:00Z",
                "source_city": "Nagoya",
                "product_name": "Chanel 2.55 フラップバッグ",
                "image_url": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&q=80",
                "category": "bag",
                "description": "1990年代中期，黑色 Lambskin，銀色五金",
            },
            {
                "id": 5,
                "arrived_at": "2026-02-24T08:20:00Z",
                "source_city": "Kyoto",
                "product_name": "Omega Constellation ヴィンテージ",
                "image_url": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=600&q=80",
                "category": "watch",
                "description": "1960年代圓形款，原裝星形標誌表盤",
            },
            {
                "id": 6,
                "arrived_at": "2026-02-23T13:10:00Z",
                "source_city": "Tokyo",
                "product_name": "Nikon F フォトニック ファインダー",
                "image_url": "https://images.unsplash.com/photo-1496016943515-7d33598c11e6?w=600&q=80",
                "category": "camera",
                "description": "1968年製，含原廠皮質背帶與鏡頭蓋",
            },
        ]
    )
    USER_DISPLAY_NAMES.update(
        {
            "admin@wakou-demo.com": "管理員",
            "user@wakou-demo.com": "客人",
            "sales@wakou-demo.com": "銷售",
            "maint@wakou-demo.com": "維護",
            "vip@wakou-demo.com": "VIP 會員",
        }
    )
    USERS_LIST.extend([
        {"email": "admin@wakou-demo.com", "role": "admin", "display_name": "管理員", "created_at": "2025-12-01T08:00:00Z", "total_orders": 1, "total_spent_twd": 365000},
        {"email": "user@wakou-demo.com", "role": "buyer", "display_name": "客人", "created_at": "2026-01-10T14:00:00Z", "total_orders": 2, "total_spent_twd": 438500},
        {"email": "sales@wakou-demo.com", "role": "sales", "display_name": "銷售", "created_at": "2025-12-15T09:00:00Z", "total_orders": 0, "total_spent_twd": 0},
        {"email": "maint@wakou-demo.com", "role": "maintenance", "display_name": "維護", "created_at": "2026-01-05T10:00:00Z", "total_orders": 0, "total_spent_twd": 0},
        {"email": "vip@wakou-demo.com", "role": "buyer", "display_name": "VIP 會員", "created_at": "2025-11-20T16:00:00Z", "total_orders": 5, "total_spent_twd": 890000},
    ])
    ORDERS.update(
        {
            1: {
                "id": 1,
                "product_id": 1,
                "mode": "buy_now",
                "buyer_email": "admin@wakou-demo.com",
                "product_name": "Rolex Submariner 5513",
                "amount_twd": 380000,
                "final_amount_twd": 365000,
                "status": "completed",
                "comm_room_id": 1,
                "created_at": "2026-02-16T09:20:00Z",
            },
            2: {
                "id": 2,
                "product_id": 3,
                "mode": "inquiry",
                "buyer_email": "admin@wakou-demo.com",
                "product_name": "Tiffany & Co. 古董珍珠項鍊",
                "amount_twd": 68000,
                "final_amount_twd": 68000,
                "status": "waiting_quote",
                "comm_room_id": 2,
                "created_at": "2026-02-21T11:00:00Z",
            },
            3: {
                "id": 3,
                "product_id": 4,
                "mode": "inquiry",
                "buyer_email": "user@wakou-demo.com",
                "product_name": "Seven by Seven 重製丹寧外套",
                "amount_twd": 18500,
                "final_amount_twd": 18500,
                "status": "quoted",
                "comm_room_id": 3,
                "created_at": "2026-02-23T08:30:00Z",
            },
            4: {
                "id": 4,
                "product_id": 2,
                "mode": "buy_now",
                "buyer_email": "user@wakou-demo.com",
                "product_name": "Vintage Hermès Kelly 32",
                "amount_twd": 420000,
                "final_amount_twd": 420000,
                "status": "paid",
                "comm_room_id": 4,
                "created_at": "2026-02-25T14:00:00Z",
            },
        }
    )
    COMM_ROOMS.update(
        {
            1: {
                "id": 1,
                "order_id": 1,
                "buyer_email": "admin@wakou-demo.com",
                "product_id": 1,
                "product_name": "Rolex Submariner 5513",
                "status": "completed",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-14T09:00:00Z"},
                    {"id": 2, "from": "sales", "message": "已完成最終檢驗，準備出貨", "timestamp": "2026-02-16T09:00:00Z"},
                ],
                "created_at": "2026-02-14T09:00:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 220},
            },
            2: {
                "id": 2,
                "order_id": 2,
                "buyer_email": "admin@wakou-demo.com",
                "product_id": 3,
                "product_name": "Tiffany & Co. 古董珍珠項鍊",
                "status": "waiting_quote",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-21T11:00:00Z"},
                    {"id": 2, "from": "buyer", "message": "想確認珍珠材質與證書細節", "timestamp": "2026-02-21T11:20:00Z"},
                ],
                "created_at": "2026-02-21T11:00:00Z",
                "shipping_quote": None,
            },
            3: {
                "id": 3,
                "order_id": 3,
                "buyer_email": "user@wakou-demo.com",
                "product_id": 4,
                "product_name": "Seven by Seven 重製丹寧外套",
                "status": "quoted",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-23T08:30:00Z"},
                    {"id": 2, "from": "sales", "message": "可提供近拍與洗標照片", "timestamp": "2026-02-23T10:20:00Z"},
                ],
                "created_at": "2026-02-23T08:30:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 180},
            },
            4: {
                "id": 4,
                "order_id": 4,
                "buyer_email": "user@wakou-demo.com",
                "product_id": 2,
                "product_name": "Vintage Hermès Kelly 32",
                "status": "paid",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-25T14:00:00Z"},
                    {"id": 2, "from": "buyer", "message": "已完成匯款", "timestamp": "2026-02-25T15:30:00Z"},
                    {"id": 3, "from": "system", "message": "管理員已確認收款", "timestamp": "2026-02-25T16:00:00Z"},
                ],
                "created_at": "2026-02-25T14:00:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 350},
            },
        }
    )
    POINTS_LOGS.extend(
        [
            {
                "id": 1,
                "email": "admin@wakou-demo.com",
                "delta_points": 3650,
                "reason": "完成訂單 #1 回饋",
                "recorded_at": "2026-02-16T10:20:00Z",
            },
            {
                "id": 2,
                "email": "admin@wakou-demo.com",
                "delta_points": -500,
                "reason": "會員折抵使用",
                "recorded_at": "2026-02-18T08:00:00Z",
            },
            {
                "id": 3,
                "email": "user@wakou-demo.com",
                "delta_points": 185,
                "reason": "下單預估回饋",
                "recorded_at": "2026-02-23T12:20:00Z",
            },
        ]
    )
    COUPONS.extend(
        [
            {"id": 1, "code": "FIXED100", "type": "fixed", "value": 100, "min_order_twd": 5000, "description": "折扣 NT$100", "max_uses": None, "active": True},
            {"id": 2, "code": "FIXED500", "type": "fixed", "value": 500, "min_order_twd": 10000, "description": "折扣 NT$500", "max_uses": None, "active": True},
            {"id": 3, "code": "PERCENT95", "type": "percentage", "value": 95, "min_order_twd": 0, "description": "全單 95 折", "max_uses": None, "active": True},
            {"id": 4, "code": "PERCENT90", "type": "percentage", "value": 90, "min_order_twd": 0, "description": "全單 9 折", "max_uses": None, "active": True},
            {"id": 5, "code": "PERCENT80", "type": "percentage", "value": 80, "min_order_twd": 0, "description": "全單 8 折（最大獎）", "max_uses": None, "active": True},
        ]
    )
    next_coupon_id = 6
    GACHA_POOLS.extend(
        [
            {
                "id": 1,
                "name": "預設獎池",
                "is_default": True,
                "active": True,
                "prizes": [
                    {"type": "coupon", "coupon_id": 1, "label": "-100", "weight": 35},
                    {"type": "redraw", "coupon_id": None, "label": "再抽一次", "weight": 25},
                    {"type": "coupon", "coupon_id": 2, "label": "-500", "weight": 20},
                    {"type": "coupon", "coupon_id": 3, "label": "95折", "weight": 10},
                    {"type": "coupon", "coupon_id": 4, "label": "9折", "weight": 7},
                    {"type": "coupon", "coupon_id": 5, "label": "8折", "weight": 3},
                ],
                "bonus_draws": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    next_gacha_pool_id = 2
    GACHA_DRAW_QUOTA["admin@wakou-demo.com"] = 2
    _append_event(
        "order.completed",
        "sales@wakou-demo.com",
        "sales",
        order_id=1,
        room_id=1,
        title="完成出貨與驗收",
        detail="Rolex Submariner 5513 已完成交付並確認收貨。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "points.earned",
        "system",
        "admin",
        order_id=1,
        title="回饋點數入帳",
        detail="完成訂單獲得 3650 點。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "room.updated",
        "sales@wakou-demo.com",
        "sales",
        order_id=2,
        room_id=2,
        title="收到珍珠材質與證書詢問",
        detail="已加入待處理清單，將於 24 小時內回覆買家。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "quote.ready",
        "sales@wakou-demo.com",
        "sales",
        order_id=3,
        room_id=3,
        title="報價已更新",
        detail="Seven by Seven 外套報價與運費已上傳。",
        payload={"buyer_email": "user@wakou-demo.com"},
    )
    _append_event(
        "order.paid",
        "user@wakou-demo.com",
        "buyer",
        order_id=4,
        room_id=4,
        title="買家已完成付款",
        detail="Vintage Hermès Kelly 32 已確認匯款。",
        payload={"buyer_email": "user@wakou-demo.com"},
    )
    next_cost_id = 16
    next_revenue_id = len(REVENUE_RECORDS) + 1
    next_order_id = 5
    next_room_id = 5
    # ── 額外示範客戶 ──────────────────────────────────────────────────────────────
    for _email, _pw, _role in [
        ("yuki@demo.com", "demo123", "buyer"),
        ("kenji@demo.com", "demo123", "buyer"),
        ("mei@demo.com", "demo123", "buyer"),
    ]:
        try:
            register_user(SessionLocal(), _email, _pw, _role)
        except Exception:
            pass  # already registered in DB — skip
    USER_DISPLAY_NAMES.update({
        "yuki@demo.com": "佐藤 ゆき",
        "kenji@demo.com": "田中 健司",
        "mei@demo.com": "林 美惠",
    })
    USERS_LIST.extend([
        {"email": "yuki@demo.com", "role": "buyer", "display_name": "佐藤 ゆき",
         "created_at": "2026-01-15T10:00:00Z", "total_orders": 3, "total_spent_twd": 476500},
        {"email": "kenji@demo.com", "role": "buyer", "display_name": "田中 健司",
         "created_at": "2026-02-01T09:30:00Z", "total_orders": 1, "total_spent_twd": 380000},
        {"email": "mei@demo.com", "role": "buyer", "display_name": "林 美惠",
         "created_at": "2026-02-10T14:00:00Z", "total_orders": 2, "total_spent_twd": 86500},
    ])
    # ── 額外訂單與諮詢室 ──────────────────────────────────────────────────────────
    ORDERS.update({
        5: {
            "id": 5, "product_id": 5, "mode": "buy_now",
            "buyer_email": "yuki@demo.com",
            "product_name": "昭和銅製花器",
            "amount_twd": 12500, "final_amount_twd": 12500,
            "status": "completed", "comm_room_id": 5,
            "created_at": "2026-01-20T11:00:00Z",
        },
        6: {
            "id": 6, "product_id": 6, "mode": "inquiry",
            "buyer_email": "yuki@demo.com",
            "product_name": "Vintage Cartier 絲巾",
            "amount_twd": 9800, "final_amount_twd": 9800,
            "status": "quoted", "comm_room_id": 6,
            "created_at": "2026-01-28T15:00:00Z",
        },
        7: {
            "id": 7, "product_id": 1, "mode": "buy_now",
            "buyer_email": "kenji@demo.com",
            "product_name": "Rolex Submariner 5513",
            "amount_twd": 380000, "final_amount_twd": 380000,
            "status": "paid", "comm_room_id": 7,
            "created_at": "2026-02-05T10:00:00Z",
        },
        8: {
            "id": 8, "product_id": 3, "mode": "inquiry",
            "buyer_email": "mei@demo.com",
            "product_name": "Tiffany & Co. 古董珍珠項鍊",
            "amount_twd": 68000, "final_amount_twd": 68000,
            "status": "completed", "comm_room_id": 8,
            "created_at": "2026-02-12T09:00:00Z",
        },
        9: {
            "id": 9, "product_id": 4, "mode": "buy_now",
            "buyer_email": "mei@demo.com",
            "product_name": "Seven by Seven 重製丹寧外套",
            "amount_twd": 18500, "final_amount_twd": 18500,
            "status": "waiting_quote", "comm_room_id": 9,
            "created_at": "2026-02-26T08:00:00Z",
        },
    })
    COMM_ROOMS.update({
        5: {
            "id": 5, "order_id": 5, "buyer_email": "yuki@demo.com",
            "product_id": 5, "product_name": "昭和銅製花器",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-20T11:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這件花器的高度大概幾公分？", "timestamp": "2026-01-20T11:30:00Z"},
                {"id": 3, "from": "sales", "message": "高度約 28 公分，底部直徑 12 公分，重量約 850g。", "timestamp": "2026-01-20T14:00:00Z"},
                {"id": 4, "from": "buyer", "message": "太好了，我決定購買！", "timestamp": "2026-01-21T09:00:00Z"},
                {"id": 5, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-01-22T10:00:00Z"},
            ],
            "created_at": "2026-01-20T11:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 120},
        },
        6: {
            "id": 6, "order_id": 6, "buyer_email": "yuki@demo.com",
            "product_id": 6, "product_name": "Vintage Cartier 絲巾",
            "status": "quoted",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-28T15:00:00Z"},
                {"id": 2, "from": "buyer", "message": "可以提供絲巾的尺寸與成色照片嗎？", "timestamp": "2026-01-28T15:30:00Z"},
                {"id": 3, "from": "sales", "message": "尺寸 90x90cm，成色 9 成新，已附近拍照。", "timestamp": "2026-01-29T10:00:00Z"},
                {"id": 4, "from": "buyer", "message": "請問可以折扣嗎？", "timestamp": "2026-01-29T11:00:00Z"},
                {"id": 5, "from": "sales", "message": "此件為精選定價，暫無折扣空間，感謝理解。", "timestamp": "2026-01-29T13:00:00Z"},
            ],
            "created_at": "2026-01-28T15:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 80},
        },
        7: {
            "id": 7, "order_id": 7, "buyer_email": "kenji@demo.com",
            "product_id": 1, "product_name": "Rolex Submariner 5513",
            "status": "paid",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-05T10:00:00Z"},
                {"id": 2, "from": "buyer", "message": "這支錶的機芯是否有保養過？", "timestamp": "2026-02-05T10:30:00Z"},
                {"id": 3, "from": "sales", "message": "已於 2025 年底完成全機芯大保養，附保養證明。", "timestamp": "2026-02-05T14:00:00Z"},
                {"id": 4, "from": "buyer", "message": "好的，我確認購買，已完成匯款。", "timestamp": "2026-02-06T09:00:00Z"},
                {"id": 5, "from": "system", "message": "管理員已確認收款", "timestamp": "2026-02-06T10:00:00Z"},
            ],
            "created_at": "2026-02-05T10:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 350},
        },
        8: {
            "id": 8, "order_id": 8, "buyer_email": "mei@demo.com",
            "product_id": 3, "product_name": "Tiffany & Co. 古董珍珠項鍊",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-12T09:00:00Z"},
                {"id": 2, "from": "buyer", "message": "項鍊有附原廠包裝盒嗎？", "timestamp": "2026-02-12T09:30:00Z"},
                {"id": 3, "from": "sales", "message": "有原廠藍色珠寶盒與防塵袋，狀態完好。", "timestamp": "2026-02-12T11:00:00Z"},
                {"id": 4, "from": "buyer", "message": "完美，確認購買！", "timestamp": "2026-02-12T11:30:00Z"},
                {"id": 5, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-02-13T09:00:00Z"},
            ],
            "created_at": "2026-02-12T09:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 150},
        },
        9: {
            "id": 9, "order_id": 9, "buyer_email": "mei@demo.com",
            "product_id": 4, "product_name": "Seven by Seven 重製丹寧外套",
            "status": "open",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-26T08:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這件外套的尺寸標是多少？", "timestamp": "2026-02-26T08:30:00Z"},
            ],
            "created_at": "2026-02-26T08:00:00Z",
            "shipping_quote": None,
        },
    })
    # ── 評價資料 ────────────────────────────────────────────────────────────────
    REVIEWS.extend([
        {"id": 1, "order_id": 1, "product_id": 1, "product_name": "Rolex Submariner 5513",
         "buyer_email": "admin@wakou-demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 4, "service_rating": 5,
         "comment": "錶況與描述完全一致，包裝也非常細心，非常滿意這次的購買體驗！",
         "hidden": False, "seller_reply": "感謝您的支持，期待下次再為您服務。",
         "created_at": "2026-02-17T10:00:00Z"},
        {"id": 2, "order_id": 5, "product_id": 5, "product_name": "昭和銅製花器",
         "buyer_email": "yuki@demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5,
         "comment": "花器実物はとても美しい。写真以上の存在感でした。また購入したいです。",
         "hidden": False, "seller_reply": "ありがとうございます！またぜひよろしくお願いいたします。",
         "created_at": "2026-01-23T09:00:00Z"},
        {"id": 3, "order_id": 7, "product_id": 1, "product_name": "Rolex Submariner 5513",
         "buyer_email": "kenji@demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5,
         "comment": "保養証明書付きで安心して購入できました。機械の状態も完璧です。",
         "hidden": False, "seller_reply": None,
         "created_at": "2026-02-08T11:00:00Z"},
        {"id": 4, "order_id": 8, "product_id": 3, "product_name": "Tiffany & Co. 古董珍珠項鍊",
         "buyer_email": "mei@demo.com",
         "rating": 4, "quality_rating": 4, "delivery_rating": 5, "service_rating": 5,
         "comment": "珍珠項鍊非常漂亮，附原廠盒超加分，服務態度也很好。",
         "hidden": False, "seller_reply": "感謝您的評價，珍珠是我們最愛的品項之一！",
         "created_at": "2026-02-14T12:00:00Z"},
    ])
    next_review_id = 5
    # ── 財報：補充收入與成本 ─────────────────────────────────────────────────────
    # ── yuki 第3筆大額訂單（Hermès Kelly）───────────────────────────────────────
    ORDERS.update({
        10: {
            "id": 10, "product_id": 2, "mode": "inquiry",
            "buyer_email": "yuki@demo.com",
            "product_name": "Vintage Hermès Kelly 32 (二手 A 品)",
            "amount_twd": 464000, "final_amount_twd": 464000,
            "status": "completed", "comm_room_id": 10,
            "created_at": "2026-01-10T09:00:00Z",
        },
    })
    COMM_ROOMS.update({
        10: {
            "id": 10, "order_id": 10, "buyer_email": "yuki@demo.com",
            "product_id": 2, "product_name": "Vintage Hermès Kelly 32 (二手 A 品)",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-10T09:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這個 Kelly 32 的包款顏色是 Etoupe 嗎？包身有無明顯磨損？", "timestamp": "2026-01-10T09:30:00Z"},
                {"id": 3, "from": "sales", "message": "是的，顏色為 Etoupe（大象灰），包身 A 品成色，僅角落有輕微磨損，五金為金色 Palladium，保存狀況極佳。", "timestamp": "2026-01-10T11:00:00Z"},
                {"id": 4, "from": "buyer", "message": "有附原廠塵袋嗎？鎖扣運作正常？", "timestamp": "2026-01-10T14:00:00Z"},
                {"id": 5, "from": "sales", "message": "附原廠 Hermès 橘色塵袋，鎖扣運作完全正常，附實拍影片供您確認。", "timestamp": "2026-01-10T15:30:00Z"},
                {"id": 6, "from": "buyer", "message": "感謝詳細說明，我決定購買，請提供匯款資訊。", "timestamp": "2026-01-11T10:00:00Z"},
                {"id": 7, "from": "sales", "message": "感謝您的信任！匯款帳號已傳送至您的信箱，確認收款後我們會立即安排出貨。", "timestamp": "2026-01-11T10:30:00Z"},
                {"id": 8, "from": "buyer", "message": "已完成匯款，麻煩確認。", "timestamp": "2026-01-12T09:00:00Z"},
                {"id": 9, "from": "system", "message": "管理員已確認收款，訂單進入備貨流程", "timestamp": "2026-01-12T10:00:00Z"},
                {"id": 10, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-01-14T15:00:00Z"},
            ],
            "created_at": "2026-01-10T09:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 500},
        },
    })
    REVENUE_RECORDS.extend([
        # ── 1月份收入 ────────────────────────────────────────────────────────────
        {"id": 1, "order_id": 10, "type": "revenue", "title": "Hermès Kelly 32 (佐藤) — 成交收入", "amount_twd": 464000, "recorded_at": "2026-01-14"},
        {"id": 2, "order_id": 5, "type": "revenue", "title": "昭和銅製花器 — 成交收入", "amount_twd": 12500, "recorded_at": "2026-01-22"},
        # ── 2月份收入 ────────────────────────────────────────────────────────────
        {"id": 3, "order_id": 7, "type": "revenue", "title": "Rolex Submariner 5513 (田中) — 成交收入", "amount_twd": 380000, "recorded_at": "2026-02-06"},
        {"id": 4, "order_id": 8, "type": "revenue", "title": "Tiffany & Co. 古董珍珠項鍊 — 成交收入", "amount_twd": 68000, "recorded_at": "2026-02-13"},
        {"id": 5, "order_id": 1, "type": "revenue", "title": "Rolex Submariner 5513 (管理員) — 成交收入", "amount_twd": 365000, "recorded_at": "2026-02-16"},
        {"id": 6, "order_id": 4, "type": "revenue", "title": "Vintage Hermès Kelly 32 (user) — 成交收入", "amount_twd": 420000, "recorded_at": "2026-02-25"},
    ])
    COST_RECORDS.extend([
        # ── 1月份成本 ────────────────────────────────────────────────────────────
        {"id": 4, "title": "Hermès Kelly 32 — 採購成本", "amount_twd": 310000, "recorded_at": "2026-01-08", "type": "product", "product_id": 2},
        {"id": 5, "title": "國際運費與關稅 (1月批次)", "amount_twd": 22000, "recorded_at": "2026-01-09", "type": "misc"},
        {"id": 6, "title": "昭和銅製花器 — 採購成本", "amount_twd": 6500, "recorded_at": "2026-01-18", "type": "product", "product_id": 5},
        {"id": 7, "title": "倉儲與保險費 (1月)", "amount_twd": 5500, "recorded_at": "2026-01-31", "type": "misc"},
        # ── 2月份成本 ────────────────────────────────────────────────────────────
        {"id": 8, "title": "Rolex Submariner 5513 — 採購成本 (田中)", "amount_twd": 240000, "recorded_at": "2026-02-03", "type": "product", "product_id": 1},
        {"id": 9, "title": "Tiffany & Co. 古董珍珠項鍊 — 採購成本", "amount_twd": 42000, "recorded_at": "2026-02-08", "type": "product", "product_id": 3},
        {"id": 10, "title": "國際運費與關稅 (2月批次)", "amount_twd": 28000, "recorded_at": "2026-02-12", "type": "misc"},
        {"id": 11, "title": "攝影與商品拍攝費 (2月)", "amount_twd": 8000, "recorded_at": "2026-02-15", "type": "misc"},
        {"id": 12, "title": "Rolex Submariner 5513 — 採購成本 (管理員單)", "amount_twd": 240000, "recorded_at": "2026-02-10", "type": "product", "product_id": 1},
        {"id": 13, "title": "Vintage Hermès Kelly 32 — 採購成本", "amount_twd": 310000, "recorded_at": "2026-02-20", "type": "product", "product_id": 2},
        {"id": 14, "title": "包裝耗材與快遞費 (2月)", "amount_twd": 3500, "recorded_at": "2026-02-28", "type": "misc"},
        {"id": 15, "title": "倉儲與保險費 (2月)", "amount_twd": 5500, "recorded_at": "2026-02-28", "type": "misc"},
    ])
    next_cost_id = 16
    next_revenue_id = len(REVENUE_RECORDS) + 1
    next_order_id = 11
    next_room_id = 11

    _append_shipment_event(
        1,
        "payment_confirmed",
        "付款確認",
        "已確認收款，訂單進入備貨流程。",
        "Tokyo",
        "2026-02-16T10:30:00Z",
    )
    _append_shipment_event(
        1,
        "preparing",
        "備貨中",
        "專員完成品況複檢與包裝。",
        "Tokyo Warehouse",
        "2026-02-16T17:20:00Z",
    )
    _append_shipment_event(
        1,
        "shipped_jp",
        "已從日本出貨",
        "交由國際物流承運。",
        "Narita",
        "2026-02-17T09:10:00Z",
    )
    _append_shipment_event(
        1,
        "in_transit",
        "國際運送中",
        "航班已起飛，預計兩日後抵台。",
        "NRT -> TPE",
        "2026-02-17T14:50:00Z",
    )
    _append_shipment_event(
        1,
        "delivered",
        "已送達",
        "買家已簽收完成。",
        "Taipei",
        "2026-02-18T15:30:00Z",
    )

    _append_shipment_event(
        7,
        "payment_confirmed",
        "付款確認",
        "已收到款項，準備安排國際出貨。",
        "Tokyo",
        "2026-02-06T10:10:00Z",
    )
    _append_shipment_event(
        7,
        "preparing",
        "備貨中",
        "保卡與配件完成二次核對。",
        "Tokyo Warehouse",
        "2026-02-06T16:20:00Z",
    )
    _append_shipment_event(
        7,
        "shipped_jp",
        "已從日本出貨",
        "貨件已離開日本倉庫。",
        "Haneda",
        "2026-02-07T09:40:00Z",
    )
    _append_shipment_event(
        7,
        "customs_tw",
        "台灣海關清關",
        "已進入清關流程。",
        "Taoyuan Customs",
        "2026-02-07T19:35:00Z",
    )
    _append_shipment_event(
        7,
        "shipped_tw",
        "台灣境內配送",
        "交由宅配司機配送中。",
        "Taiwan Local Hub",
        "2026-02-08T08:10:00Z",
    )

    _append_shipment_event(
        10,
        "payment_confirmed",
        "付款確認",
        "高單價訂單已完成付款核對。",
        "Tokyo",
        "2026-01-12T10:10:00Z",
    )
    _append_shipment_event(
        10,
        "preparing",
        "備貨中",
        "完成防塵包裝與保固文件。",
        "Tokyo Warehouse",
        "2026-01-12T16:30:00Z",
    )
    _append_shipment_event(
        10,
        "shipped_jp",
        "已從日本出貨",
        "精品專線已接手出貨。",
        "Narita",
        "2026-01-13T08:55:00Z",
    )
    _append_shipment_event(
        10,
        "in_transit",
        "國際運送中",
        "航班運送至台灣中。",
        "NRT -> TPE",
        "2026-01-13T13:45:00Z",
    )
    _append_shipment_event(
        10,
        "delivered",
        "已送達",
        "買家完成驗收。",
        "Taipei",
        "2026-01-14T15:20:00Z",
    )

    _append_shipment_event(
        4,
        "payment_confirmed",
        "付款確認",
        "已收到款項，預計將從東京倉庫備貨出貨。",
        "Tokyo",
        "2026-02-25T15:00:00Z",
    )
    _append_shipment_event(
        4,
        "preparing",
        "備貨中",
        "Hermès Kelly 已完成品況複檢與防塵包裝。",
        "Tokyo Warehouse",
        "2026-02-26T10:30:00Z",
    )

    CATEGORIES.extend([
        {"id": "watch", "title": "經典腕錶", "image": "/Watches.png"},
        {"id": "bag", "title": "復古包款", "image": "/Handbags.png"},
        {"id": "jewelry", "title": "珠寶飾品", "image": "/Jewelry.png"},
        {"id": "apparel", "title": "珍藏服飾", "image": "/Apparel.png"},
        {"id": "lifestyle", "title": "藝術擺件", "image": "/Lifestyle.png"},
        {"id": "accessory", "title": "特選配件", "image": "/Wallets.png"},
    ])
    # Seed categories to DB
    _cat_session = SessionLocal()
    try:
        from sqlalchemy import delete as _delete_cat
        _cat_session.execute(_delete_cat(Category))
        seed_cats = [
            Category(id="watch", title_zh="經典腕錶", title_ja="クラシックウォッチ", title_en="Classic Watches", image_url="/Watches.png", sort_order=0),
            Category(id="bag", title_zh="復古包款", title_ja="ヴィンテージバッグ", title_en="Vintage Bags", image_url="/Handbags.png", sort_order=1),
            Category(id="jewelry", title_zh="珠寶飾品", title_ja="ジュエリー", title_en="Jewelry", image_url="/Jewelry.png", sort_order=2),
            Category(id="apparel", title_zh="珍藏服飾", title_ja="コレクションアパレル", title_en="Apparel", image_url="/Apparel.png", sort_order=3),
            Category(id="lifestyle", title_zh="藝術擺件", title_ja="ライフスタイル", title_en="Lifestyle", image_url="/Lifestyle.png", sort_order=4),
            Category(id="accessory", title_zh="特選配件", title_ja="セレクトアクセサリー", title_en="Accessories", image_url="/Wallets.png", sort_order=5),
        ]
        _cat_session.add_all(seed_cats)
        _cat_session.commit()
    finally:
        _cat_session.close()
    
    

    session = SessionLocal()
    try:
        session.execute(delete(Product))
        session.add_all(
            [
                Product(
                    id=int(item["id"]),
                    sku=str(item["sku"]),
                    category=str(item["category"]),
                    name_zh_hant=str(item["name"]["zh-Hant"]),
                    name_ja=str(item["name"]["ja"]),
                    name_en=str(item["name"]["en"]),
                    price_twd=int(item["price_twd"]),
                    grade=str(item["grade"]),
                    description_zh=str(item.get("description", {}).get("zh-Hant", "")),
                    description_ja=str(item.get("description", {}).get("ja", "")),
                    description_en=str(item.get("description", {}).get("en", "")),
                )
                for item in PRODUCTS
            ]
        )
        session.commit()
    finally:
        session.close()
             
    MAGAZINES.extend([{"id": 1, "brand": "Rolex", "contents": [{"title": {"zh-Hant": "時間的見證者：Rolex Submariner 5513", "ja": "時の証人：ロレックス サブマリーナ 5513", "en": "Witness of Time: Rolex Submariner 5513"}, "description": {"zh-Hant": "從深海到街頭，探討5513為何成為復古錶迷的終極指標。", "ja": "深海からストリートまで、なぜ5513がヴィンテージ時計ファンの究極の指標となったのか。", "en": "From the deep sea to the streets, why the 5513 is the ultimate grail for vintage collectors."}, "image_url": "/Watches.png", "body": {"zh-Hant": "沒有繁複的日期窗，只有純粹的時間顯示。Submariner 5513 以其無曆設計和亞克力鏡面，散發著獨特的溫潤光澤。歲月在膏藥面上留下的痕跡，每一抹泛黃都在訴說著一段故事。這不僅是一只潛水錶，更是跨越世代的美學傳承。", "ja": "複雑な日付表示はなく、純粋な時間表示のみ。サブマリーナ5513は、カレンダーなしのデザインとアクリル風防により、独特の温かみのある輝きを放ちます。時が文字盤に残した痕跡、その黄ばみの一つ一つが物語を語っています。これは単なるダイバーズウォッチではなく、世代を超えた美学の継承です。", "en": "No complex date windows, just pure time display. The Submariner 5513, with its no-date design and acrylic crystal, emits a uniquely warm luster. The traces left by time on the dial—every touch of patina tells a story. This is not just a dive watch; it's an aesthetic heritage spanning generations."}, "status": "published", "published_at": "2026-02-01T09:00:00Z"}]}, {"id": 2, "brand": "Seven by Seven", "contents": [{"title": {"zh-Hant": "舊物的煉金術：Seven by Seven 的重構美學", "ja": "古物の錬金術：Seven by Seven の再構築の美学", "en": "Alchemy of the Old: The Reconstructed Aesthetics of Seven by Seven"}, "description": {"zh-Hant": "解構、拼接、再造。看川上淳也如何賦予老舊丹寧新的生命。", "ja": "解体、パッチワーク、再創造。川上淳也がいかにして古いデニムに新たな命を吹き込むか。", "en": "Deconstruction, patchwork, and recreation. How Junya Kawakami breathes new life into vintage denim."}, "image_url": "/Apparel.png", "body": {"zh-Hant": "每一件 Seven by Seven 的重製單品都是一場與過去的對話。設計師親自挑選具有特殊褪色與磨損的老丹寧，將其解體後，以現代的廓形重新拼接。這不只是環保的升級再造，更是一種對時間痕跡的極致致敬。", "ja": "Seven by Seven のリメイクアイテムは、すべて過去との対話です。デザイナー自らが特殊な色落ちやスレのある古いデニムを選び、解体した後、現代的なシルエットで再構築します。これは単なる環境に配慮したアップサイクルではなく、時の痕跡に対する究極のオマージュです。", "en": "Every reconstructed piece from Seven by Seven is a conversation with the past. The designer personally selects vintage denim with unique fades and wear, deconstructs them, and pieces them back together in modern silhouettes. This is more than just eco-friendly upcycling; it's the ultimate homage to the traces of time."}, "status": "published", "published_at": "2026-02-15T09:00:00Z"}]}, {"id": 3, "brand": "Nanamica", "contents": [{"title": {"zh-Hant": "城市與自然的橋樑：Nanamica 的機能日常", "ja": "都市と自然の架け橋：Nanamica の機能的な日常", "en": "Bridge Between City and Nature: Nanamica's Functional Daily Wear"}, "description": {"zh-Hant": "將高科技面料隱藏於經典男裝輪廓之下，重新定義當代通勤裝束。", "ja": "ハイテク素材をクラシックなメンズウェアのシルエットに隠し、現代の通勤スタイルを再定義する。", "en": "Hiding high-tech fabrics beneath classic menswear silhouettes, redefining contemporary commuting attire."}, "image_url": "/Apparel.png", "body": {"zh-Hant": "『One Ocean, All Lands』是 Nanamica 的不變哲學。Gore-Tex Cruiser Jacket 完美體現了這一點。外觀是經典的軍裝風衣，內裡卻蘊含著頂級的防水透氣科技。無論是東京的梅雨季還是台北的午後雷陣雨，它都能讓你保持優雅與乾爽。", "ja": "「One Ocean, All Lands」は Nanamica の変わらぬ哲学です。Gore-Tex Cruiser Jacket はこれを完璧に体現しています。外見はクラシックなミリタリーコートですが、内側には最高クラスの防水透湿技術が隠されています。東京の梅雨でも台北の午後の雷雨でも、常にエレガントでドライな状態を保ちます。", "en": "'One Ocean, All Lands' is Nanamica's unchanging philosophy. The Gore-Tex Cruiser Jacket embodies this perfectly. It looks like a classic military coat on the outside, but conceals top-tier waterproof and breathable technology inside. Whether it's Tokyo's rainy season or Taipei's afternoon thunderstorms, it keeps you elegant and dry."}, "status": "published", "published_at": "2026-02-20T09:00:00Z"}]}])

    article_id_cursor = 1
    for block in MAGAZINES:
        for content in block.get("contents", []):
            if not content.get("article_id"):
                content["article_id"] = article_id_cursor
            if not content.get("slug"):
                content["slug"] = _slugify(content.get("title", {}).get("en", "") or content.get("title", {}).get("zh-Hant", ""))
            if not content.get("gallery_urls"):
                content["gallery_urls"] = [str(content.get("image_url") or "")]
            article_id_cursor = max(article_id_cursor, int(content["article_id"]) + 1)
    next_mag_article_id = article_id_cursor
    # Write magazine articles to DB
    _mag_session = SessionLocal()
    try:
        import json as _json
        _mag_session.execute(delete(MagazineArticle))
        for brand_block in MAGAZINES:
            brand = brand_block.get("brand", "")
            for content in brand_block.get("contents", []):
                article = MagazineArticle(
                    id=int(content.get("article_id", 0)),
                    brand=brand,
                    slug=str(content.get("slug", "")),
                    title_zh=str(content.get("title", {}).get("zh-Hant", "")),
                    title_ja=str(content.get("title", {}).get("ja", "")),
                    title_en=str(content.get("title", {}).get("en", "")),
                    desc_zh=str(content.get("description", {}).get("zh-Hant", "")),
                    desc_ja=str(content.get("description", {}).get("ja", "")),
                    desc_en=str(content.get("description", {}).get("en", "")),
                    body_zh=str(content.get("body", {}).get("zh-Hant", "")),
                    body_ja=str(content.get("body", {}).get("ja", "")),
                    body_en=str(content.get("body", {}).get("en", "")),
                    image_url=str(content.get("image_url", "")),
                    gallery_urls_json=_json.dumps(content.get("gallery_urls", [])),
                    published=content.get("status", "published") == "published",
                )
                _mag_session.add(article)
        _mag_session.commit()
    finally:
        _mag_session.close()

    # Write costs seed data to MySQL
    from datetime import date as _date
    _cost_session = SessionLocal()
    try:
        from sqlalchemy import delete as _delete_cost
        _cost_session.execute(_delete_cost(Cost))
        for record in COST_RECORDS:
            recorded = record.get("recorded_at", "2026-01-01")
            if isinstance(recorded, str):
                recorded = _date.fromisoformat(recorded)
            _cost_session.add(Cost(
                id=int(record["id"]),
                title=str(record.get("title", record.get("category", ""))),
                amount_twd=int(record["amount_twd"]),
                recorded_at=recorded,
                product_id=record.get("product_id"),
                cost_type=str(record.get("type", record.get("cost_type", "misc"))),
            ))
        _cost_session.commit()
    finally:
        _cost_session.close()

def bootstrap_state() -> None:
    Base.metadata.create_all(bind=engine)
    should_reset = os.getenv("RESET_STATE_ON_BOOT", "0") == "1"
    force_demo_seed = os.getenv("FORCE_DEMO_SEED", "1") == "1"

    session = SessionLocal()
    try:
        has_users = session.scalar(select(User.id)) is not None
        has_products = session.scalar(select(Product.id)) is not None
    finally:
        session.close()

    if should_reset or force_demo_seed or not has_users or not has_products:
        reset_state()
        return

    existing_meta: dict[int, dict[str, Any]] = {
        int(item.get("id") or 0): {
            "description": item.get("description", {}),
            "image_urls": item.get("image_urls", []),
        }
        for item in PRODUCTS
        if int(item.get("id") or 0) > 0
    }

    session = SessionLocal()
    try:
        db_products = list(session.scalars(select(Product).order_by(Product.id.asc())))
        db_users = list(session.scalars(select(User).order_by(User.id.asc())))
    finally:
        session.close()

    PRODUCTS.clear()
    for product in db_products:
        cached = existing_meta.get(product.id, {})
        description = cached.get("description", {})
        if not isinstance(description, dict):
            description = {}
        image_urls = cached.get("image_urls", [])
        if not isinstance(image_urls, list):
            image_urls = []

        PRODUCTS.append(
            {
                "id": product.id,
                "sku": product.sku,
                "category": product.category,
                "name": {
                    "zh-Hant": product.name_zh_hant,
                    "ja": product.name_ja,
                    "en": product.name_en,
                },
                "price_twd": product.price_twd,
                "grade": product.grade,
                "description": description,
                "image_urls": [str(url) for url in image_urls],
            }
        )

    CATEGORIES.clear()
    category_map: dict[str, dict[str, str]] = {}
    for item in PRODUCTS:
        category = str(item.get("category") or "").strip()
        if category and category not in category_map:
            category_map[category] = {"id": category, "title": category, "image": ""}
    CATEGORIES.extend(category_map.values())

    USERS_LIST.clear()
    for user in db_users:
        display_name = USER_DISPLAY_NAMES.get(user.email) or user.email.split("@", 1)[0]
        USERS_LIST.append({"email": user.email, "role": user.role, "display_name": display_name})
