"""
Database seed script - Run this to populate the database with sample data
Usage: python -c "from backend.app.seed_data import seed_all; seed_all()"
"""
from datetime import datetime, timedelta, timezone
import json
import random

from app.core.db import SessionLocal, engine, Base
from app.modules.auth.models import User
from app.modules.auth.security import hash_password
from app.modules.orders.models import Order, CommRoom, CommMessage
from app.modules.products.models import Product
from app.modules.magazines.models import MagazineArticle
from app.modules.crm.models import BuyerNote, PointsLedger
from app.modules.reviews.models import Review


def seed_all():
    """Seed all sample data"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        seed_users(session)
        seed_products(session)
        session.flush()
        seed_magazines(session)
        seed_orders(session)
        session.flush()
        seed_comm_rooms(session)
        seed_crm_notes(session)
        seed_reviews(session)

        session.commit()
        print("✅ Seed data created successfully!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        session.close()


def seed_users(session):
    """Create sample buyer users"""
    sample_users = [
        ("customer1@wakou.com", "Customer1!", "buyer", "田中太郎"),
        ("customer2@wakou.com", "Customer2!", "buyer", "林美香"),
        ("customer3@wakou.com", "Customer3!", "buyer", "Chen Wei"),
        ("customer4@wakou.com", "Customer4!", "buyer", "Sarah Kim"),
        ("customer5@wakou.com", "Customer5!", "buyer", "佐藤健一"),
        ("admin@wakou-demo.com", "Admin123!", "admin", "和光管理員"),
    ]

    for email, password, role, display_name in sample_users:
        existing = session.query(User).filter_by(email=email).first()
        if not existing:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role=role,
                display_name=display_name,
            )
            session.add(user)
            print(f"✅ Created user: {email} ({role})")


def seed_products(session):
    """Create sample products covering watches, bags, apparel, and accessories"""
    existing_count = session.query(Product).count()
    if existing_count >= 10:
        print(f"⏭️  Products already seeded ({existing_count} found), skipping")
        return

    now = datetime.now(timezone.utc)

    sample_products = [
        {
            "sku": "WAKOU-WATCH-001",
            "category": "watches",
            "name_zh_hant": "Rolex Submariner 16610 黑水鬼",
            "name_ja": "ロレックス サブマリーナー 16610 ブラック",
            "name_en": "Rolex Submariner 16610 Black Bezel",
            "price_twd": 380000,
            "grade": "A",
            "availability": "available",
            "brand": "Rolex",
            "size": "40mm",
            "tags_json": json.dumps(["watch", "rolex", "luxury", "dive"]),
            "description_zh": "經典 Rolex Submariner，旋轉錶圈，黑色錶盤，附原廠錶帶及盒裝。狀態極佳，保卡齊全。",
            "description_ja": "クラシックなロレックス サブマリーナー、回転ベゼル、ブラックダイアル、純正ブレスレット付き。状態は非常に良好。",
            "description_en": "Classic Rolex Submariner with rotating bezel, black dial, original bracelet and box. Excellent condition with warranty card.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1547996160-81dfa63595aa?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=5),
        },
        {
            "sku": "WAKOU-WATCH-002",
            "category": "watches",
            "name_zh_hant": "Omega Seamaster 300M 鈦金屬",
            "name_ja": "オメガ シーマスター 300M チタニウム",
            "name_en": "Omega Seamaster 300M Titanium",
            "price_twd": 128000,
            "grade": "A",
            "availability": "available",
            "brand": "Omega",
            "size": "42mm",
            "tags_json": json.dumps(["watch", "omega", "titanium", "dive"]),
            "description_zh": "Omega Seamaster 300M 鈦金屬款，007 電影聯名版，附完整配件及保卡。",
            "description_ja": "オメガ シーマスター 300M チタニウムモデル、007限定版、完全付属品・保証書付き。",
            "description_en": "Omega Seamaster 300M Titanium in 007 edition. Full set with box and papers.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1548169874-53e85f753f1e?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=3),
        },
        {
            "sku": "WAKOU-BAG-001",
            "category": "bags",
            "name_zh_hant": "Hermès Birkin 30 Togo 黑色金扣",
            "name_ja": "エルメス バーキン30 トゴ ブラック ゴールド金具",
            "name_en": "Hermès Birkin 30 Togo Black Gold Hardware",
            "price_twd": 580000,
            "grade": "A",
            "availability": "available",
            "brand": "Hermès",
            "size": "30cm",
            "tags_json": json.dumps(["bag", "hermes", "birkin", "luxury"]),
            "description_zh": "Hermès Birkin 30，Togo 皮革，黑色配金色扣件，附防塵袋及原廠盒。狀態 A 級，幾乎全新。",
            "description_ja": "エルメス バーキン30、トゴレザー、ブラック×ゴールド金具、ダストバッグ・箱付き。Aランク、ほぼ新品。",
            "description_en": "Hermès Birkin 30 in Togo leather, black with gold hardware. Comes with dustbag and box. Grade A, near mint condition.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=7),
        },
        {
            "sku": "WAKOU-BAG-002",
            "category": "bags",
            "name_zh_hant": "Louis Vuitton Neverfull MM 棋盤格",
            "name_ja": "ルイヴィトン ネヴァーフル MM ダミエ",
            "name_en": "Louis Vuitton Neverfull MM Damier Ebene",
            "price_twd": 42000,
            "grade": "B",
            "availability": "available",
            "brand": "Louis Vuitton",
            "size": "MM",
            "tags_json": json.dumps(["bag", "lv", "tote", "damier"]),
            "description_zh": "LV Neverfull MM 棋盤格，B 級品，皮革部分有自然氧化，包體完整無損。",
            "description_ja": "LV ネヴァーフル MM ダミエ、Bランク、レザー部分に自然なエイジングあり、本体良好。",
            "description_en": "LV Neverfull MM Damier Ebene, Grade B. Natural patina on leather trim, bag body in excellent condition.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=2),
        },
        {
            "sku": "WAKOU-APP-001",
            "category": "apparel",
            "name_zh_hant": "Nanamica GORE-TEX 連帽外套 海軍藍",
            "name_ja": "ナナミカ ゴアテックス フーデッドジャケット ネイビー",
            "name_en": "Nanamica GORE-TEX Hooded Jacket Navy",
            "price_twd": 18500,
            "grade": "A",
            "availability": "available",
            "brand": "Nanamica",
            "size": "M",
            "tags_json": json.dumps(["jacket", "nanamica", "gore-tex", "japanese"]),
            "description_zh": "Nanamica GORE-TEX 防水連帽外套，日本製，幾乎未使用，附原標籤。",
            "description_ja": "ナナミカ ゴアテックス フーデッドジャケット、日本製、ほぼ未使用、タグ付き。",
            "description_en": "Nanamica GORE-TEX hooded jacket, Made in Japan, barely worn. Tags still attached.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=1),
        },
        {
            "sku": "WAKOU-APP-002",
            "category": "apparel",
            "name_zh_hant": "Engineered Garments 格紋 Overshirt",
            "name_ja": "エンジニアードガーメンツ チェック オーバーシャツ",
            "name_en": "Engineered Garments Plaid Overshirt",
            "price_twd": 8800,
            "grade": "A",
            "availability": "available",
            "brand": "Engineered Garments",
            "size": "S",
            "tags_json": json.dumps(["shirt", "eg", "workwear", "american"]),
            "description_zh": "Engineered Garments 美式格紋 Overshirt，S 尺寸，狀態 A+，無任何使用痕跡。",
            "description_ja": "エンジニアードガーメンツ チェック オーバーシャツ、Sサイズ、Aランク、使用感なし。",
            "description_en": "Engineered Garments plaid overshirt, Size S. Grade A+, no signs of wear.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=4),
        },
        {
            "sku": "WAKOU-ACC-001",
            "category": "accessories",
            "name_zh_hant": "Tiffany & Co. 永恆系列鑽石項鍊",
            "name_ja": "ティファニー エタニティ ダイヤモンド ネックレス",
            "name_en": "Tiffany & Co. Eternity Diamond Necklace",
            "price_twd": 68000,
            "grade": "A",
            "availability": "available",
            "brand": "Tiffany & Co.",
            "size": "45cm",
            "tags_json": json.dumps(["jewelry", "tiffany", "diamond", "necklace"]),
            "description_zh": "Tiffany & Co. 永恆系列鑽石項鍊，白金底座，附正品證書及原廠藍盒。",
            "description_ja": "ティファニー エタニティ ダイヤモンドネックレス、プラチナ台、正規証明書・ブルーボックス付き。",
            "description_en": "Tiffany & Co. Eternity Diamond Necklace, platinum setting. Comes with certificate of authenticity and original blue box.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=6),
        },
        {
            "sku": "WAKOU-ACC-002",
            "category": "accessories",
            "name_zh_hant": "Porter Tanker 腰包 黑色",
            "name_ja": "ポーター タンカー ウエストバッグ ブラック",
            "name_en": "Porter Tanker Waist Bag Black",
            "price_twd": 7200,
            "grade": "A",
            "availability": "available",
            "brand": "Porter",
            "size": "One Size",
            "tags_json": json.dumps(["bag", "porter", "tanker", "japanese"]),
            "description_zh": "吉田包 Porter Tanker 腰包，日本製，黑色，使用次數極少，無損傷。",
            "description_ja": "吉田カバン ポーター タンカー ウエストバッグ、日本製、ブラック、使用回数極少、傷なし。",
            "description_en": "Yoshida Kaban Porter Tanker waist bag, Made in Japan. Black, minimal use, no damage.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600",
            ]),
            "stock_qty": 2,
            "listed_at": now - timedelta(days=8),
        },
        {
            "sku": "WAKOU-WATCH-003",
            "category": "watches",
            "name_zh_hant": "Seiko SARB033 自動機械錶",
            "name_ja": "セイコー SARB033 オートマチック",
            "name_en": "Seiko SARB033 Automatic",
            "price_twd": 22000,
            "grade": "A",
            "availability": "available",
            "brand": "Seiko",
            "size": "38mm",
            "tags_json": json.dumps(["watch", "seiko", "automatic", "japanese"]),
            "description_zh": "Seiko SARB033 經典自動機械錶，日本製，附完整原廠配件，已停產絕版款。",
            "description_ja": "セイコー SARB033 クラシック オートマチック、日本製、完全付属品付き、廃番モデル。",
            "description_en": "Seiko SARB033 classic automatic, Made in Japan. Full set, discontinued model.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=10),
        },
        {
            "sku": "WAKOU-APP-003",
            "category": "apparel",
            "name_zh_hant": "Levi's 501 復刻牛仔褲 1947年版",
            "name_ja": "リーバイス 501 リプロダクション 1947",
            "name_en": "Levi's 501 Reproduction 1947",
            "price_twd": 15800,
            "grade": "B",
            "availability": "available",
            "brand": "Levi's",
            "size": "W32 L32",
            "tags_json": json.dumps(["denim", "levis", "vintage", "reproduction"]),
            "description_zh": "Levi's 501 復刻 1947 年版，日本製，已自然水洗，呈現優美的褪色效果。",
            "description_ja": "リーバイス 501 1947リプロダクション、日本製、自然なウォッシュ、美しいフェード。",
            "description_en": "Levi's 501 1947 reproduction, Made in Japan. Naturally washed with beautiful fade.",
            "preview_images_json": json.dumps([
                "https://images.unsplash.com/photo-1542272604-787c3835535d?w=600",
            ]),
            "stock_qty": 1,
            "listed_at": now - timedelta(days=9),
        },
    ]

    for data in sample_products:
        existing = session.query(Product).filter_by(sku=data["sku"]).first()
        if not existing:
            product = Product(**data)
            session.add(product)
            print(f"✅ Created product: {data['sku']} - {data['name_en']}")


def seed_magazines(session):
    """Create sample magazine articles"""
    existing_count = session.query(MagazineArticle).count()
    if existing_count >= 3:
        print(f"⏭️  Magazine articles already seeded ({existing_count} found), skipping")
        return

    now = datetime.now(timezone.utc)

    sample_articles = [
        {
            "brand": "Rolex",
            "slug": "rolex-submariner-guide-2026",
            "title_zh": "Rolex Submariner 完全指南：如何辨別真品與鑑賞要點",
            "title_ja": "ロレックス サブマリーナー 完全ガイド：真贋鑑定と鑑賞のポイント",
            "title_en": "The Complete Rolex Submariner Guide: Authentication & Connoisseur Tips",
            "desc_zh": "深入解析 Submariner 的歷史演變、各代版本特徵，以及在二手市場中如何鑑定真偽。",
            "desc_ja": "サブマリーナーの歴史的変遷、各世代の特徴、中古市場での真贋鑑定方法を詳しく解説。",
            "desc_en": "An in-depth analysis of the Submariner's historical evolution, generation characteristics, and how to authenticate in the secondary market.",
            "body_zh": "Rolex Submariner 自 1953 年問世以來，已成為腕錶界最具代表性的潛水錶款之一...",
            "body_ja": "ロレックス サブマリーナーは1953年の登場以来、時計界で最も象徴的なダイバーズウォッチの一つとなっています...",
            "body_en": "Since its introduction in 1953, the Rolex Submariner has become one of the most iconic dive watches in horology...",
            "image_url": "https://images.unsplash.com/photo-1547996160-81dfa63595aa?w=800",
            "published": True,
            "sort_order": 1,
            "created_at": now - timedelta(days=14),
            "updated_at": now - timedelta(days=14),
        },
        {
            "brand": "Hermès",
            "slug": "hermes-birkin-investment-value",
            "title_zh": "Hermès Birkin：超越時尚的資產保值神話",
            "title_ja": "エルメス バーキン：ファッションを超えた資産価値の神話",
            "title_en": "Hermès Birkin: The Investment Asset Beyond Fashion",
            "desc_zh": "探討 Birkin 包作為資產配置工具的可行性，以及如何在二手市場尋找保值潛力最高的款式。",
            "desc_ja": "バーキンを資産配分ツールとしての可能性と、二次市場で最も保値力の高いモデルの選び方を探る。",
            "desc_en": "Exploring the viability of the Birkin bag as an investment vehicle and how to identify the highest-value models in the secondary market.",
            "body_zh": "在過去十年中，Hermès Birkin 的市場價值平均每年增長 14.2%，超越了黃金和標準普爾 500 指數...",
            "body_ja": "過去10年間、エルメス バーキンの市場価値は平均年率14.2%上昇し、金やS&P500を上回っています...",
            "body_en": "Over the past decade, the Hermès Birkin has averaged 14.2% annual market value growth, outperforming gold and the S&P 500...",
            "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=800",
            "published": True,
            "sort_order": 2,
            "created_at": now - timedelta(days=7),
            "updated_at": now - timedelta(days=7),
        },
        {
            "brand": "Japanese Fashion",
            "slug": "japanese-vintage-fashion-scene",
            "title_zh": "東京中古時尚：理解日本 Vintage 市場的獨特文化",
            "title_ja": "東京ヴィンテージファッション：日本の古着市場の独自文化を理解する",
            "title_en": "Tokyo Vintage Fashion: Understanding Japan's Unique Secondhand Culture",
            "desc_zh": "從 Harajuku 的古著聖地到 Mercari 的數位化二手市場，探索日本 Vintage 文化的魅力與特色。",
            "desc_ja": "原宿のヴィンテージの聖地からメルカリのデジタル二次市場まで、日本のヴィンテージ文化の魅力と特色を探る。",
            "desc_en": "From Harajuku's vintage mecca to Mercari's digital secondhand market, exploring the allure and characteristics of Japan's vintage culture.",
            "body_zh": "日本二手市場以其高品質的物品保存標準和誠信的交易文化聞名於世...",
            "body_ja": "日本の中古市場は、高品質なアイテムの保存基準と誠実な取引文化で世界的に有名です...",
            "body_en": "Japan's secondhand market is world-renowned for its high standards of item preservation and honest trading culture...",
            "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
            "published": True,
            "sort_order": 3,
            "created_at": now - timedelta(days=3),
            "updated_at": now - timedelta(days=3),
        },
    ]

    for data in sample_articles:
        existing = session.query(MagazineArticle).filter_by(slug=data["slug"]).first()
        if not existing:
            article = MagazineArticle(**data)
            session.add(article)
            print(f"✅ Created magazine article: {data['slug']}")


def seed_orders(session):
    """Create sample orders"""
    existing_count = session.query(Order).count()
    if existing_count >= 8:
        print(f"⏭️  Orders already seeded ({existing_count} found), skipping")
        return

    products = session.query(Product).limit(10).all()
    if not products:
        print("⚠️ No products found, skipping order creation")
        return

    users = session.query(User).filter_by(role="buyer").all()
    if not users:
        print("⚠️ No buyer users found, skipping order creation")
        return

    order_data = [
        {"status": "completed", "days_ago": 30},
        {"status": "completed", "days_ago": 25},
        {"status": "completed", "days_ago": 20},
        {"status": "payment_confirmed", "days_ago": 5},
        {"status": "payment_confirmed", "days_ago": 3},
        {"status": "shipped", "days_ago": 2},
        {"status": "shipped", "days_ago": 1},
        {"status": "pending", "days_ago": 0},
        {"status": "pending", "days_ago": 0},
        {"status": "cancelled", "days_ago": 10},
    ]

    for i, data in enumerate(order_data):
        product = products[i % len(products)]
        user = users[i % len(users)]

        order = Order(
            buyer_email=user.email,
            product_id=product.id,
            product_name=product.name_zh_hant or product.name_en or f"Product {product.id}",
            status=data["status"],
            amount_twd=product.price_twd,
            final_amount_twd=int(product.price_twd * 0.9) if data["status"] != "cancelled" else None,
            created_at=datetime.now(timezone.utc) - timedelta(days=data["days_ago"])
        )
        session.add(order)

    session.flush()
    print(f"✅ Created {len(order_data)} sample orders")


def seed_comm_rooms(session):
    """Create sample communication rooms with messages"""
    orders = session.query(Order).filter(Order.status != "cancelled").limit(8).all()
    if not orders:
        print("⚠️ No orders found, skipping comm room creation")
        return

    messages_samples = [
        [
            ("您好，我想購買這款 Rolex，請問還有現貨嗎？", "buyer"),
            ("您好，感謝您的詢問！這款 Rolex Submariner 還有現貨，狀態非常好，附原廠盒子及保卡。", "admin"),
            ("太好了！請問可以議價嗎？", "buyer"),
            ("這款目前價格已經非常優惠了，是日本中古市場的優質藏品。如果一次付清可以再優惠 2000 元。", "admin"),
            ("好的，那我下單了！", "buyer"),
        ],
        [
            ("請問這件 Nanamica 外套有什麼尺寸？", "buyer"),
            ("這件是 M 尺寸，日本製，幾乎沒有使用痕跡。", "admin"),
            ("好的，我要訂購，請問運費是多少？", "buyer"),
            ("國際運費 1500 元，台灣境內運費 150 元。", "admin"),
        ],
        [
            ("我想購買這個 Hermès 包包，請確認庫存。", "buyer"),
            ("確認還有庫存，請問您要使用什麼付款方式？", "admin"),
            ("我要匯款，請給我帳號。", "buyer"),
            ("請匯款至以下帳號：玉山銀行 123-456-789，戶名：和光精選有限公司。", "admin"),
        ],
        [
            ("請問這個珠寶項鍊是真的嗎？", "buyer"),
            ("我們所有商品都經過專業鑑定，這款 Tiffany 項鍊附有正品證書。", "admin"),
            ("好的，我想了解更多細節...", "buyer"),
            ("當然！我們可以安排視訊鑑賞，讓您近距離確認每個細節。", "admin"),
        ],
        [
            ("我的訂單已經出貨了嗎？", "buyer"),
            ("是的，已經出貨了！物流單號：SF1234567890，預計 3-5 個工作天送達。", "admin"),
            ("收到，謝謝！", "buyer"),
        ],
    ]

    admin_users = session.query(User).filter(User.role.in_(["admin", "super_admin"])).all()
    admin_email = admin_users[0].email if admin_users else "admin@wakou-demo.com"

    for i, order in enumerate(orders):
        existing_room = session.query(CommRoom).filter_by(order_id=order.id).first()
        if existing_room:
            continue

        comm_room = CommRoom(
            order_id=order.id,
            buyer_email=order.buyer_email,
            status="open" if order.status == "pending" else "closed",
            final_price_twd=order.final_amount_twd,
            shipping_fee_twd=300,
            discount_twd=2000 if order.final_amount_twd else 0,
            created_at=order.created_at
        )
        session.add(comm_room)
        session.flush()

        if i < len(messages_samples):
            for msg_data in messages_samples[i]:
                message = CommMessage(
                    room_id=comm_room.id,
                    sender_email=order.buyer_email if msg_data[1] == "buyer" else admin_email,
                    sender_role=msg_data[1],
                    message=msg_data[0],
                    created_at=comm_room.created_at + timedelta(hours=random.randint(1, 48))
                )
                session.add(message)

    print(f"✅ Created {len(orders)} comm rooms with messages")


def seed_crm_notes(session):
    """Create sample CRM buyer notes and points"""
    users = session.query(User).filter_by(role="buyer").all()
    if not users:
        return

    notes_data = [
        ("customer1@wakou.com", "VIP 客戶，對 Rolex 和 Omega 特別感興趣。偏好日本中古市場來源。"),
        ("customer2@wakou.com", "喜歡高端皮革製品，曾詢問過 Hermès 及 Chanel。"),
        ("customer3@wakou.com", "對日本古著非常了解，特別關注 Nanamica 和 Engineered Garments。"),
    ]

    for email, note_text in notes_data:
        existing = session.query(BuyerNote).filter_by(buyer_email=email).first()
        if not existing:
            note = BuyerNote(
                buyer_email=email,
                note=note_text,
                author="admin@wakou-demo.com",
            )
            session.add(note)

    points_data = [
        ("customer1@wakou.com", 3800, "首次購物回饋"),
        ("customer2@wakou.com", 1280, "首次購物回饋"),
        ("customer3@wakou.com", 850, "會員紅利"),
    ]

    for email, points, reason in points_data:
        existing = session.query(PointsLedger).filter_by(buyer_email=email).first()
        if not existing:
            ledger = PointsLedger(
                buyer_email=email,
                delta=points,
                reason=reason,
            )
            session.add(ledger)

    print("✅ Created CRM notes and points data")


def seed_reviews(session):
    """Create sample buyer reviews"""
    existing_count = session.query(Review).count()
    if existing_count >= 8:
        print(f"⏭️  Reviews already seeded ({existing_count} found), skipping")
        return

    review_data = [
        {"order_id": 1, "buyer_email": "customer1@wakou.com", "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5, "comment": "包裝精美，商品狀態與描述完全一致，非常滿意！Rolex 保卡齊全，值得信賴。", "hidden": False, "seller_reply": "感謝您的支持！期待再次為您服務。"},
        {"order_id": 2, "buyer_email": "customer2@wakou.com", "rating": 5, "quality_rating": 5, "delivery_rating": 4, "service_rating": 5, "comment": "Hermès 包包品質非常好，幾乎看不出使用痕跡。客服回覆很快，整體體驗極佳。", "hidden": False, "seller_reply": "謝謝您的好評！包包保養得很好是因為我們嚴格的品質把關。"},
        {"order_id": 3, "buyer_email": "customer3@wakou.com", "rating": 4, "quality_rating": 4, "delivery_rating": 5, "service_rating": 4, "comment": "Nanamica 外套品質不錯，配送速度很快。唯一小遺憾是沒有附上品牌防塵袋。", "hidden": False, "seller_reply": None},
        {"order_id": 4, "buyer_email": "customer1@wakou.com", "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5, "comment": "第二次購買了，依然完美！Tiffany 項鍊閃閃發光，老婆非常開心。", "hidden": False, "seller_reply": "感謝老客戶的信任！祝您們幸福快樂。"},
        {"order_id": 5, "buyer_email": "customer4@wakou.com", "rating": 3, "quality_rating": 3, "delivery_rating": 4, "service_rating": 3, "comment": "商品有些微使用痕跡比照片上看起來明顯，但整體還是可以接受的品質。", "hidden": False, "seller_reply": "感謝您的回饋，我們會加強照片拍攝的準確度，讓客戶能更真實了解商品狀態。"},
        {"order_id": 6, "buyer_email": "customer5@wakou.com", "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5, "comment": "Seiko SARB033 停產錶款在這裡找到了！狀態超乎預期，走時精準。大推！", "hidden": False, "seller_reply": None},
        {"order_id": 7, "buyer_email": "customer2@wakou.com", "rating": 4, "quality_rating": 5, "delivery_rating": 3, "service_rating": 4, "comment": "LV 包包品質很好，但國際運送花了比較長的時間，希望能改善物流速度。", "hidden": False, "seller_reply": "感謝您的建議！我們正在優化國際物流合作夥伴，未來會更快速。"},
        {"order_id": 8, "buyer_email": "customer3@wakou.com", "rating": 2, "quality_rating": 2, "delivery_rating": 4, "service_rating": 3, "comment": "收到的 Levi's 牛仔褲有一處小破損未在商品描述中說明，有些失望。", "hidden": True, "seller_reply": "非常抱歉造成您的困擾，我們已安排全額退款並改善品檢流程。"},
        {"order_id": 9, "buyer_email": "customer4@wakou.com", "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5, "comment": "Porter 腰包超可愛！日本製的品質果然不同凡響，包裝也很用心。", "hidden": False, "seller_reply": None},
        {"order_id": 10, "buyer_email": "customer1@wakou.com", "rating": 4, "quality_rating": 4, "delivery_rating": 4, "service_rating": 5, "comment": "Omega 手錶整體狀態很好，客服人員非常專業地解答了我的鑑定問題。推薦！", "hidden": False, "seller_reply": "感謝您選擇和光精選！我們的鑑定師都經過嚴格培訓。"},
    ]

    existing_order_ids = {
        row[0]
        for row in session.query(Review.order_id).all()
    }
    created_count = 0
    now = datetime.now(timezone.utc)

    for data in review_data:
        if data["order_id"] in existing_order_ids:
            continue

        review = Review(
            **data,
            created_at=now - timedelta(days=random.randint(1, 30)),
        )
        session.add(review)
        created_count += 1

    print(f"✅ Created {created_count} sample reviews")


if __name__ == "__main__":
    seed_all()
