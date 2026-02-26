# 和光精選 (Wakou Vintage Select) — 系統功能全覽

> 最後更新：2026-02-26
> 用途：後端功能盤點 + 開發規劃參照文件

---

## 目錄

1. [已知 Bug](#已知-bug)
2. [已完成功能（現有系統）](#已完成功能)
3. [待開發功能（規劃中）](#待開發功能)
4. [系統架構摘要](#系統架構摘要)
5. [角色與權限設計](#角色與權限設計)

---

## 已知 Bug

### BUG-1：抽獎系統不顯示抽到的獎項

- **頁面**：`/dashboard/gacha`
- **現象**：按下「開始抽獎」後，畫面上不會顯示抽到了什麼獎項（coupon label）。使用者必須去「通知中心」(`/dashboard/messages`) 才能看到結果（例如「抽獎結果：-500」）。
- **預期**：抽獎完成後，應該在抽獎頁面本身直接、明確地顯示獎項名稱與折扣券資訊。
- **影響**：使用者體驗不直覺，不知道自己抽到了什麼。
- **相關檔案**：
  - 前端：`frontend/src/app/views/AccountSectionView.vue`（gacha section template）
  - 後端：`POST /api/v1/gacha/draw`（回傳 `results` 陣列含 `label`、`coupon`）
- **可能原因**：前端 gacha section 的結果顯示邏輯（`showResult` / `gachaResults`）可能沒有正確渲染，或者 CSS 層級問題導致結果被遮蓋。

### BUG-2：折扣券無法在結帳時使用

- **頁面**：`/checkout`
- **現象**：結帳頁面（交易流程頁）只有「使用回饋點數」的輸入框，沒有折扣券選擇器。使用者在 `/dashboard/coupons` 可以看到持有的折扣券（如 -NT$500、-NT$100），但結帳時無法選擇使用。
- **預期**：結帳頁應有一個折扣券下拉選單，讓使用者選擇要套用的折扣券，並即時顯示折扣後金額。
- **影響**：折扣券系統形同虛設，使用者無法實際使用獲得的優惠。
- **相關檔案**：
  - 前端：`frontend/src/app/views/CheckoutView.vue`
  - 前端 service：`frontend/src/modules/checkout/service.js`（`createOrder` 已支援 `coupon_id` 參數）
  - 後端：`POST /api/v1/orders`（已支援 `coupon_id` + 折扣計算邏輯）
  - 後端：`GET /api/v1/users/coupons/available?order_amount_twd=X`（已有 API）
- **可能原因**：後端 API 已完整支援折扣券套用，但前端 CheckoutView 尚未整合折扣券選擇 UI。

---

## 已完成功能

### 1. 商品管理系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 商品列表（含分頁、分類篩選、多語系） | 前+後 | `GET /api/v1/products` | ✅ |
| 商品詳情 | 前+後 | `GET /api/v1/products/:id` | ✅ |
| 分類列表 | 前+後 | `GET /api/v1/categories` | ✅ |
| 管理員新增商品（SKU、分類、名稱、描述、等級、價格、圖片） | 前+後 | `POST /api/v1/admin/products` | ✅ |
| 管理員編輯商品 | 前+後 | `PATCH /api/v1/admin/products/:id` | ✅ |
| 管理員刪除商品 | 前+後 | `DELETE /api/v1/admin/products/:id` | ✅ |
| 管理員商品列表 | 前+後 | `GET /api/v1/admin/products` | ✅ |

**商品資料結構：**
- `sku`、`category`（watch/apparel/bag/accessory/lifestyle）
- `name`（zh-Hant/ja/en 三語）、`description`（三語）
- `grade`（S/A/B）、`price_twd`、`image_urls`

### 2. 雜誌 / 專欄系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 雜誌列表（含品牌分組） | 前+後 | `GET /api/v1/magazines` | ✅ |
| 雜誌文章詳情頁 | 前 | `/magazine/:id` | ✅ |
| 管理員文章列表 | 前+後 | `GET /api/v1/admin/magazines/articles` | ✅ |
| 管理員新增文章（品牌、標題、描述、內文、封面圖、相簿、slug） | 後 | `POST /api/v1/admin/magazines/articles` | ✅ |
| 管理員編輯文章 | 後 | `PATCH /api/v1/admin/magazines/articles/:id` | ✅ |
| 管理員刪除文章 | 後 | `DELETE /api/v1/admin/magazines/articles/:id` | ✅ |

**文章資料結構：**
- `brand`、`title`（三語）、`description`（三語）、`body`（三語）
- `image_url`（封面）、`gallery_urls`（圖輯）
- `status`（published/draft）、`published_at`、`slug`

### 3. 客戶管理 / CRM 系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 客戶列表（全部使用者） | 後 | `GET /api/v1/admin/users` | ✅ |
| 單一客戶歷史（訂單、消費總額、轉換率、點數、備註） | 後 | `GET /api/v1/admin/crm/buyers/:email/history` | ✅ |
| 新增 CRM 備註 | 後 | `POST /api/v1/admin/crm/buyers/:email/notes` | ✅ |
| 手動調整客戶點數 | 後 | `POST /api/v1/admin/crm/buyers/:email/reward` | ✅ |
| 使用者個人資料修改（顯示名稱） | 前+後 | `PATCH /api/v1/users/me` | ✅ |

### 4. 訂單 / 交易流程

**交易流程（四步驟確認機制）：**

```
01 建立訂單 → 保留藏品並建立對話室
02 細節確認 → 職人提供近拍照與最終運費（管理員在 comm-room 報價）
03 買家確認 → 確認細節與費用後回覆同意
04 安全付款 → 匯款轉帳或導向 ECPay 完成付款
```

**訂單狀態流轉：**
```
inquiring → waiting_quote → quoted → buyer_accepted → proof_uploaded → paid → completed
                                                         ↓ (ECPay)
                                                    buyer_confirmed → paid → completed
```

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 建立訂單（inquiry / buy_now 兩種模式） | 前+後 | `POST /api/v1/orders` | ✅ |
| 我的訂單列表 | 前+後 | `GET /api/v1/orders/me` | ✅ |
| 專屬諮詢室（對話、圖片） | 前+後 | `GET /api/v1/comm-rooms/:id` | ✅ |
| 諮詢室發送訊息 | 前+後 | `POST /api/v1/comm-rooms/:id/messages` | ✅ |
| 管理員提交最終報價（商品價 + 運費 + 折扣） | 後 | `POST /api/v1/comm-rooms/:id/final-quote` | ✅ |
| 買家接受報價 | 前+後 | `POST /api/v1/comm-rooms/:id/accept-quote` | ✅ |
| 買家上傳匯款證明 | 前+後 | `POST /api/v1/comm-rooms/:id/upload-proof` | ✅ |
| 管理員確認收款 | 後 | `POST /api/v1/orders/:id/confirm-payment` | ✅ |
| 管理員完成訂單 | 後 | `POST /api/v1/orders/:id/complete` | ✅ |
| ECPay 付款整合（sandbox） | 後 | `POST /api/v1/payments/ecpay/:id` | ✅ |
| ECPay 回調 | 後 | `POST /api/v1/payments/ecpay/callback` | ✅ |
| 管理員訂單列表 | 前+後 | `GET /api/v1/admin/orders` | ✅ |
| 管理員修改訂單狀態 | 前+後 | `PATCH /api/v1/admin/orders/:id/status` | ✅ |
| 管理員工作流看板（按狀態分欄） | 前+後 | `GET /api/v1/admin/workflow-queues` | ✅ |
| 管理員訂單 CSV 匯出 | 後 | `GET /api/v1/admin/orders/export.csv` | ✅ |

**訂單 + 諮詢室重點：**
- 每筆訂單綁定一個專屬諮詢室 (`comm_room_id`)
- 買家與管理員都可以在諮詢室中對話、議價
- 所有對話與報價變更都有系統日誌 (`EVENT_LOGS`)
- 管理員後台可隨時調出任何客戶、任何商品的完整記錄

### 5. 點數 / 會員等級系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 會員等級自動升等（初見 → 生日禮遇 → 免運會員 → 尊榮會員） | 後 | 內建邏輯 | ✅ |
| 訂單完成自動回饋點數（依等級不同費率） | 後 | `POST /api/v1/orders/:id/complete` | ✅ |
| 點數過期機制（依 `expiry_months` 設定） | 後 | 內建邏輯 | ✅ |
| 點數折抵（結帳時使用，1 點 = NT$1） | 前+後 | `POST /api/v1/orders`（`points_to_redeem`） | ✅ |
| 點數餘額與歷史查詢 | 前+後 | `GET /api/v1/users/growth` | ✅ |
| 管理員點數政策設定 | 後 | `POST /api/v1/admin/points-policy` | ✅ |
| 評價贈送 30 點 | 後 | `POST /api/v1/reviews` | ✅ |

**會員等級門檻：**
| 等級 | 累計消費門檻 | 回饋費率 | 特殊福利 |
|------|------------|---------|---------|
| 初見 | NT$0 | 1% | — |
| 生日禮遇 | NT$20,000 | 1.2% | 生日禮金 NT$500 |
| 免運會員 | NT$50,000 | 1.5% | 免運券 1 張 |
| 尊榮會員 | NT$150,000 | 2% | 全站 95 折 / 不限次數免運 |

### 6. 折扣券系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 折扣券模板 CRUD | 後 | `GET/POST /api/v1/admin/coupons` | ✅ |
| 發放折扣券給指定使用者 | 後 | `POST /api/v1/admin/coupons/issue` | ✅ |
| 使用者折扣券列表 | 前+後 | `GET /api/v1/users/coupons` | ✅ |
| 可用折扣券查詢（依訂單金額篩選） | 後 | `GET /api/v1/users/coupons/available` | ✅ |
| 結帳時套用折扣券 | 後 | `POST /api/v1/orders`（`coupon_id`） | ✅ |
| **結帳頁面折扣券選擇器** | **前端** | — | **❌ 未完成** (BUG-2) |

**折扣券類型：**
- `fixed`：固定金額折扣（如 -NT$100、-NT$500）
- `percentage`：百分比折扣（如 95 折、9 折、8 折）
- 支援最低消費門檻 (`min_order_twd`)

### 7. 抽獎系統（Gacha）

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 獎池管理（CRUD） | 後 | `GET/POST /api/v1/admin/gacha/pools` | ✅ |
| 發放抽獎次數 | 後 | `POST /api/v1/admin/gacha/grant-draws` | ✅ |
| 抽獎狀態查詢 | 前+後 | `GET /api/v1/gacha/status` | ✅ |
| 執行抽獎（加權隨機 + 自動再抽） | 前+後 | `POST /api/v1/gacha/draw` | ✅ |
| 訂單完成自動獲得 1 次抽獎機會 | 後 | 內建邏輯 | ✅ |
| **抽獎結果即時顯示** | **前端** | — | **❌ 未完成** (BUG-1) |

**獎池獎品配置（預設）：**
| 獎品 | 權重 | 機率約 |
|------|------|-------|
| -100（NT$100 折扣券） | 35 | 35% |
| 再抽一次 | 25 | 25% |
| -500（NT$500 折扣券） | 20 | 20% |
| 95 折 | 10 | 10% |
| 9 折 | 7 | 7% |
| 8 折（最大獎） | 3 | 3% |

### 8. 通知系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 使用者通知列表（訂單、抽獎、點數等事件） | 前+後 | `GET /api/v1/users/private-salon` | ✅ |
| 標記通知已讀 | 前+後 | `POST /api/v1/users/notifications/read` | ✅ |
| 管理員事件日誌 | 前+後 | `GET /api/v1/admin/events` | ✅ |
| 管理員標記已讀 | 後 | `POST /api/v1/admin/events/read` | ✅ |

### 9. 評價系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 買家提交評價（評分、留言、圖片、匿名） | 前+後 | `POST /api/v1/reviews` | ✅ |
| 管理員評價列表 | 後 | `GET /api/v1/admin/reviews` | ✅ |
| 管理員隱藏/回覆評價 | 後 | `PATCH /api/v1/admin/reviews/:id` | ✅ |

### 10. 財務報表

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 營收紀錄（訂單付款自動入帳） | 後 | 內建邏輯 | ✅ |
| 成本紀錄 CRUD | 後 | `GET/POST /api/v1/admin/costs` | ✅ |
| 報表摘要（總收入、總支出、利潤 + 每日曲線圖資料） | 前+後 | `GET /api/v1/admin/report/summary` | ✅ |

**報表回傳格式：**
```json
{
  "totals": { "revenue_twd": N, "cost_twd": N, "profit_twd": N },
  "series": [{ "date": "YYYY-MM-DD", "income_twd": N, "cost_twd": N, "profit_twd": N }],
  "cost_items": [...],
  "revenue_items": [...]
}
```

### 11. 認證 / 權限系統

| 功能 | 端 | API | 狀態 |
|------|-----|-----|------|
| 註冊（含角色指定） | 前+後 | `POST /api/v1/auth/register` | ✅ |
| 登入（JWT access + refresh token） | 前+後 | `POST /api/v1/auth/login` | ✅ |
| Token 刷新 | 前+後 | `POST /api/v1/auth/refresh` | ✅ |
| 身份查詢 | 前+後 | `GET /api/v1/auth/me` | ✅ |

### 12. 其他已完成

| 功能 | 說明 |
|------|------|
| 日本倉庫時間軸 | `GET /api/v1/warehouse/timeline` — 到貨紀錄 |
| 購物車 | 前端 localStorage 管理，支援增刪改查 |
| 多語系 (i18n) | zh-Hant / ja / en 三語切換 |
| 管理員後台菜單（依角色動態生成） | `GET /api/v1/admin/console-config` |
| 管理員儀表板概覽 | `GET /api/v1/admin/overview` |

---

## 待開發功能

以下為你提到的規劃中功能，目前系統尚未實作：

### P1：修復已知 Bug（高優先）

| # | 功能 | 說明 | 難度 |
|---|------|------|------|
| P1-1 | 抽獎結果即時顯示 | 修復 gacha section，抽完直接在頁面顯示獎項名稱與折扣券資訊 | 低 |
| P1-2 | 結帳頁折扣券選擇器 | CheckoutView 加入折扣券下拉選單，後端 API 已就緒 | 中 |

### P2：頁面瀏覽分析（Analytics）

| # | 功能 | 說明 | 難度 |
|---|------|------|------|
| P2-1 | 頁面停留時間追蹤 | 記錄每個使用者在每個頁面的停留時間 | 中 |
| P2-2 | 點擊熱區統計 | 記錄各區塊的點擊次數，了解使用者興趣 | 中 |
| P2-3 | 管理員分析儀表板 | 後台可視化顯示上述數據 | 高 |

**建議實作方式：**
- 前端：在 router `beforeEach` / `afterEach` 埋點，記錄頁面進入/離開時間
- 後端：新增 `POST /api/v1/analytics/pageview` 與 `GET /api/v1/admin/analytics/summary`
- 可考慮使用第三方服務（如 Google Analytics、Plausible）降低開發成本

### P3：導流 / 推薦系統（Referral）

| # | 功能 | 說明 | 難度 |
|---|------|------|------|
| P3-1 | 專屬分享網址生成 | 每個客戶/管理員有獨特的推薦連結 | 中 |
| P3-2 | 導流來源追蹤 | 記錄從各推薦連結進站的人數 | 中 |
| P3-3 | 導流排行榜 | 顯示誰帶來最多流量 | 低 |
| P3-4 | 業績獎金制度（未來） | 根據導流成效計算獎金 | 高 |

**建議實作方式：**
- 推薦連結格式：`https://wakou.com/?ref=USER_CODE`
- 後端：新增 `referral_code` 欄位到 User、新增 `REFERRAL_LOGS` 資料結構
- API：`GET /api/v1/users/referral-link`、`GET /api/v1/admin/referrals/summary`

### P4：進階權限管控

| # | 功能 | 說明 | 難度 |
|---|------|------|------|
| P4-1 | 更細緻的角色權限矩陣 | 總管/老闆/銷售各有不同可操作區域 | 中 |

**現有角色：**
| 角色 | 代碼 | 現有權限 |
|------|------|---------|
| 買家 | `buyer` | 瀏覽、購買、諮詢室、個人後台 |
| 銷售 | `sales` | 訂單管理、諮詢室、工作流看板 |
| 維護 | `maintenance` | 商品管理、訂單管理 |
| 管理員 | `admin` | 全部功能 |
| 超級管理員 | `super_admin` | 全部功能 |

**建議擴充：**
- 老闆角色：可查看財報、分析，但不操作日常訂單
- 銷售角色：可操作訂單和諮詢室，但不能修改商品或系統設定
- 可在 `admin_console_menu` 中依角色動態控制選單顯示（已有基礎架構）

### P5：客戶深度管理增強

目前 CRM 已有基礎（客戶歷史、備註、點數調整），可擴充：

| # | 功能 | 說明 | 難度 |
|---|------|------|------|
| P5-1 | 客戶興趣標籤 | 記錄客戶瀏覽/收藏的商品類別 | 中 |
| P5-2 | 購物車內容查看（管理員端） | 管理員可看到客戶購物車 | 低 |
| P5-3 | 客戶對話歷史彙總 | 所有諮詢室對話的統一入口 | 低 |

---

## 系統架構摘要

```
┌─────────────────────────────────────────────┐
│                  Nginx (反向代理)              │
│         localhost:80 → frontend / backend     │
└───────┬──────────────────────┬───────────────┘
        │                      │
  ┌─────▼─────┐         ┌─────▼──────┐
  │  Frontend  │         │  Backend   │
  │  Vue 3     │  REST   │  FastAPI   │
  │  Vite      │◄───────►│  SQLAlchemy│
  │  Pinia     │  JSON   │  JWT Auth  │
  │  vue-i18n  │         │            │
  └────────────┘         └─────┬──────┘
                               │
                         ┌─────▼──────┐
                         │  MySQL 8   │
                         │  (持久化)    │
                         └────────────┘
```

**資料存儲模式：**
- MySQL：User、Product 表（持久化）
- In-memory（Python dicts/lists）：Orders、CommRooms、Coupons、Gacha、Points、Events 等
- LocalStorage（前端）：Cart、Token、Role

---

## 角色與權限設計

```
FULL_ADMIN_ROLES    = {admin, super_admin}           → 所有管理功能
PRODUCT_ADMIN_ROLES = {admin, super_admin, maintenance} → 商品 CRUD
ORDER_ADMIN_ROLES   = {admin, super_admin, sales, maintenance} → 訂單/諮詢室
```

| 功能區塊 | buyer | sales | maintenance | admin/super_admin |
|---------|-------|-------|-------------|-------------------|
| 瀏覽商品 | ✅ | ✅ | ✅ | ✅ |
| 購買/下單 | ✅ | — | — | ✅ |
| 諮詢室對話 | ✅(自己的) | ✅(全部) | ✅(全部) | ✅(全部) |
| 商品 CRUD | — | — | ✅ | ✅ |
| 訂單管理 | — | ✅ | ✅ | ✅ |
| 報價/確認付款 | — | ✅ | ✅ | ✅ |
| 雜誌管理 | — | — | — | ✅ |
| 財務報表 | — | — | — | ✅ |
| 使用者管理 | — | — | — | ✅ |
| 點數政策 | — | — | — | ✅ |
| 折扣券管理 | — | — | — | ✅ |
| 抽獎池管理 | — | — | — | ✅ |
| 系統設定 | — | ✅ | ✅ | ✅ |

---

## API 完整清單（快速參照）

### 認證
- `POST /api/v1/auth/register` — 註冊
- `POST /api/v1/auth/login` — 登入
- `POST /api/v1/auth/refresh` — 刷新 token
- `GET /api/v1/auth/me` — 取得身份

### 使用者
- `PATCH /api/v1/users/me` — 修改顯示名稱
- `GET /api/v1/users/dashboard-config` — 後台選單配置
- `GET /api/v1/users/growth` — 會員等級+點數+訂單
- `GET /api/v1/users/private-salon` — 完整個人資料（含通知）
- `POST /api/v1/users/notifications/read` — 標記通知已讀
- `GET /api/v1/users/coupons` — 折扣券列表
- `GET /api/v1/users/coupons/available` — 可用折扣券

### 商品
- `GET /api/v1/products` — 商品列表
- `GET /api/v1/products/:id` — 商品詳情
- `GET /api/v1/categories` — 分類列表

### 訂單 / 諮詢室
- `POST /api/v1/orders` — 建立訂單
- `GET /api/v1/orders/me` — 我的訂單
- `GET /api/v1/comm-rooms/me` — 我的諮詢室
- `GET /api/v1/comm-rooms/:id` — 諮詢室詳情
- `POST /api/v1/comm-rooms/:id/messages` — 發送訊息
- `POST /api/v1/comm-rooms/:id/final-quote` — 管理員報價
- `POST /api/v1/comm-rooms/:id/accept-quote` — 買家接受報價
- `POST /api/v1/comm-rooms/:id/upload-proof` — 上傳匯款證明
- `POST /api/v1/orders/:id/confirm-payment` — 確認收款
- `POST /api/v1/orders/:id/complete` — 完成訂單

### 付款
- `POST /api/v1/payments/ecpay/:id` — ECPay 付款
- `POST /api/v1/payments/ecpay/callback` — ECPay 回調

### 抽獎
- `GET /api/v1/gacha/status` — 抽獎狀態
- `POST /api/v1/gacha/draw` — 執行抽獎

### 評價
- `POST /api/v1/reviews` — 提交評價

### 倉庫
- `GET /api/v1/warehouse/timeline` — 倉庫時間軸

### 雜誌
- `GET /api/v1/magazines` — 雜誌列表

### 管理員
- `GET /api/v1/admin/console-config` — 後台配置
- `GET /api/v1/admin/overview` — 儀表板概覽
- `GET /api/v1/admin/products` — 商品列表
- `POST /api/v1/admin/products` — 新增商品
- `PATCH /api/v1/admin/products/:id` — 編輯商品
- `DELETE /api/v1/admin/products/:id` — 刪除商品
- `GET /api/v1/admin/orders` — 訂單列表
- `PATCH /api/v1/admin/orders/:id/status` — 修改訂單狀態
- `GET /api/v1/admin/orders/export.csv` — 訂單 CSV 匯出
- `GET /api/v1/admin/workflow-queues` — 工作流看板
- `GET /api/v1/admin/comm-rooms` — 諮詢室列表
- `GET /api/v1/admin/users` — 使用者列表
- `GET /api/v1/admin/revenue` — 營收紀錄
- `GET /api/v1/admin/costs` — 成本列表
- `POST /api/v1/admin/costs` — 新增成本
- `GET /api/v1/admin/points-policy` — 點數政策
- `POST /api/v1/admin/points-policy` — 更新點數政策
- `GET /api/v1/admin/report/summary` — 財務報表
- `GET /api/v1/admin/events` — 事件日誌
- `POST /api/v1/admin/events/read` — 標記事件已讀
- `GET /api/v1/admin/reviews` — 評價列表
- `PATCH /api/v1/admin/reviews/:id` — 管理評價
- `GET /api/v1/admin/coupons` — 折扣券模板列表
- `POST /api/v1/admin/coupons` — 新增折扣券模板
- `POST /api/v1/admin/coupons/issue` — 發放折扣券
- `GET /api/v1/admin/gacha/pools` — 獎池列表
- `POST /api/v1/admin/gacha/pools` — 新增獎池
- `POST /api/v1/admin/gacha/grant-draws` — 發放抽獎次數
- `GET /api/v1/admin/magazines/articles` — 文章列表
- `POST /api/v1/admin/magazines/articles` — 新增文章
- `PATCH /api/v1/admin/magazines/articles/:id` — 編輯文章
- `DELETE /api/v1/admin/magazines/articles/:id` — 刪除文章
- `GET /api/v1/admin/crm/buyers/:email/history` — 客戶歷史
- `POST /api/v1/admin/crm/buyers/:email/notes` — 新增備註
- `POST /api/v1/admin/crm/buyers/:email/reward` — 調整點數

---

## Demo 帳號

| 角色 | Email | 密碼 |
|------|-------|------|
| 管理員 | admin@wakou-demo.com | admin123 |
| 買家 | user@wakou-demo.com | user123 |
| 銷售 | sales@wakou-demo.com | sales123 |
| 維護 | maint@wakou-demo.com | maint123 |
