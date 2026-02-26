# Coupon System, Gacha System, Points Optimization & UI Consistency Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a coupon/discount voucher system, a gacha card-draw system, optimize the points mechanism, fix dashboard UI inconsistencies, and remove the "特權禮遇" section.

**Architecture:** All data is in-memory (dicts/lists in `backend/app/main.py`), matching the existing pattern. New features add `COUPONS`, `USER_COUPONS`, `GACHA_POOLS`, `GACHA_DRAW_QUOTA` data structures. Frontend adds new dashboard sections ("coupons", "gacha") and integrates coupon selection into checkout flow.

**Tech Stack:** FastAPI (backend), Vue 3 + Vite (frontend), in-memory data stores, existing CSS variable system.

---

## Overview of Tasks

| # | Task | Scope |
|---|------|-------|
| 1 | Backend: Coupon data model & CRUD APIs | backend |
| 2 | Backend: Gacha pool & draw APIs | backend |
| 3 | Backend: Points optimization (expiry, tier-based earn rates) | backend |
| 4 | Backend: Coupon application at order/checkout level | backend |
| 5 | Backend: Admin APIs for coupon issuance & gacha pool config | backend |
| 6 | Frontend: Fix dashboard UI consistency (point card) | frontend |
| 7 | Frontend: Remove "特權禮遇" section | frontend |
| 8 | Frontend: My Coupons section in dashboard | frontend |
| 9 | Frontend: Gacha draw UI | frontend |
| 10 | Frontend: Checkout coupon selection integration | frontend |
| 11 | Frontend: Points display optimization | frontend |
| 12 | Integration testing & verification | both |

---

## Task 1: Backend — Coupon Data Model & APIs

**Files:**
- Modify: `backend/app/main.py`

**Data structures to add (after line ~220, near other global stores):**

```python
COUPONS: list[dict[str, Any]] = []
USER_COUPONS: list[dict[str, Any]] = []
next_coupon_id = 1
next_user_coupon_id = 1
```

**Coupon template schema (COUPONS — defines coupon types):**
```python
{
    "id": int,
    "code": str,            # e.g. "FIXED100", "PERCENT95"
    "type": "fixed" | "percentage",  # fixed = NT$ off, percentage = discount rate
    "value": int,           # fixed: amount in TWD (100, 500), percentage: discount % (95, 90, 80)
    "min_order_twd": int,   # minimum order amount to use (0 = no minimum)
    "description": str,     # e.g. "折扣 NT$100", "全單 95 折"
    "max_uses": int | None, # None = unlimited
    "active": bool,
}
```

**User coupon instance schema (USER_COUPONS — user's owned coupons):**
```python
{
    "id": int,
    "coupon_id": int,       # references COUPONS[].id
    "user_email": str,
    "source": str,          # "gacha" | "admin" | "system"
    "is_used": bool,
    "used_at": str | None,
    "used_on_order_id": int | None,
    "expires_at": str,      # ISO datetime
    "created_at": str,
}
```

**Pydantic models to add:**
```python
class CouponCreatePayload(BaseModel):
    code: str
    type: str               # "fixed" or "percentage"
    value: int
    min_order_twd: int = 0
    description: str = ""
    max_uses: int | None = None

class AdminIssueCouponPayload(BaseModel):
    coupon_id: int
    user_email: str
    expires_days: int = 30
```

**API endpoints to add:**

1. `GET /api/v1/users/coupons` — List current user's coupons (with status/expiry)
2. `GET /api/v1/users/coupons/available` — List user's usable coupons for a given order amount (query param `order_amount_twd`)

**Helper functions:**
```python
def _user_coupons(email: str) -> list[dict[str, Any]]:
    """Return all coupons for user, enriched with coupon template details."""
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for uc in USER_COUPONS:
        if uc["user_email"] != email:
            continue
        template = next((c for c in COUPONS if c["id"] == uc["coupon_id"]), None)
        if template is None:
            continue
        is_expired = uc["expires_at"] < now
        results.append({
            **uc,
            "coupon": template,
            "is_expired": is_expired,
            "is_usable": not uc["is_used"] and not is_expired,
        })
    results.sort(key=lambda x: x["id"], reverse=True)
    return results

def _issue_coupon_to_user(coupon_id: int, email: str, source: str, expires_days: int = 30) -> dict[str, Any]:
    """Create a USER_COUPON entry for the given user."""
    global next_user_coupon_id
    template = next((c for c in COUPONS if c["id"] == coupon_id), None)
    if template is None:
        raise HTTPException(status_code=404, detail="coupon template not found")
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
    entry = {
        "id": next_user_coupon_id,
        "coupon_id": coupon_id,
        "user_email": email,
        "source": source,
        "is_used": False,
        "used_at": None,
        "used_on_order_id": None,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    next_user_coupon_id += 1
    USER_COUPONS.append(entry)
    return entry
```

**Add `timedelta` import** at the top:
```python
from datetime import datetime, timedelta, timezone
```

**Seed data in `reset_state()`:**
```python
# Default coupon templates
COUPONS.extend([
    {"id": 1, "code": "FIXED100", "type": "fixed", "value": 100, "min_order_twd": 5000, "description": "折扣 NT$100", "max_uses": None, "active": True},
    {"id": 2, "code": "FIXED500", "type": "fixed", "value": 500, "min_order_twd": 10000, "description": "折扣 NT$500", "max_uses": None, "active": True},
    {"id": 3, "code": "PERCENT95", "type": "percentage", "value": 95, "min_order_twd": 0, "description": "全單 95 折", "max_uses": None, "active": True},
    {"id": 4, "code": "PERCENT90", "type": "percentage", "value": 90, "min_order_twd": 0, "description": "全單 9 折", "max_uses": None, "active": True},
    {"id": 5, "code": "PERCENT80", "type": "percentage", "value": 80, "min_order_twd": 0, "description": "全單 8 折（最大獎）", "max_uses": None, "active": True},
])
next_coupon_id = 6
```

**Also clear in `reset_state()`:**
```python
COUPONS.clear()
USER_COUPONS.clear()
next_coupon_id = 1
next_user_coupon_id = 1
```

---

## Task 2: Backend — Gacha Pool & Draw APIs

**Files:**
- Modify: `backend/app/main.py`

**Data structures to add:**
```python
import random

GACHA_POOLS: list[dict[str, Any]] = []
GACHA_DRAW_QUOTA: dict[str, int] = {}  # email -> available draws
next_gacha_pool_id = 1
```

**Gacha pool schema:**
```python
{
    "id": int,
    "name": str,           # e.g. "預設獎池", "春節特別活動"
    "is_default": bool,
    "active": bool,
    "prizes": [
        {
            "type": "coupon" | "redraw",
            "coupon_id": int | None,   # references COUPONS[].id (None for redraw)
            "label": str,              # display name, e.g. "-100", "再抽一次"
            "weight": int,             # probability weight
        }
    ],
    "bonus_draws": int,    # extra draws granted by this event pool (0 for default)
    "created_at": str,
}
```

**Pydantic models:**
```python
class GachaDrawRequest(BaseModel):
    pool_id: int | None = None  # None = use default pool
```

**API endpoints:**

1. `POST /api/v1/gacha/draw` — Draw once from the gacha pool
   - Check user has draws available (GACHA_DRAW_QUOTA[email] > 0)
   - Weighted random selection from pool prizes
   - If prize is "redraw", automatically draw again (max 3 redraws to prevent infinite loops)
   - Issue coupon to user on win
   - Decrement draw quota
   - Return: `{ "draws_remaining": int, "results": [{ "label": str, "coupon": {...} | null }] }`

2. `GET /api/v1/gacha/status` — Get user's available draws and pool info
   - Return: `{ "draws_available": int, "pool": {...} }`

**Default pool seed data (in `reset_state()`):**
```python
GACHA_POOLS.extend([{
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
}])
next_gacha_pool_id = 2
```

**Draw logic helper:**
```python
def _weighted_draw(prizes: list[dict[str, Any]]) -> dict[str, Any]:
    """Weighted random selection from prize list."""
    weights = [p["weight"] for p in prizes]
    return random.choices(prizes, weights=weights, k=1)[0]

def _perform_gacha_draw(email: str, pool: dict[str, Any], max_redraws: int = 3) -> list[dict[str, Any]]:
    """Perform a gacha draw, handling redraws. Returns list of results."""
    results = []
    draws_done = 0
    while draws_done <= max_redraws:
        prize = _weighted_draw(pool["prizes"])
        draws_done += 1
        if prize["type"] == "redraw":
            results.append({"label": prize["label"], "coupon": None, "is_redraw": True})
            continue  # draw again
        # Issue coupon
        user_coupon = _issue_coupon_to_user(prize["coupon_id"], email, "gacha", expires_days=30)
        template = next((c for c in COUPONS if c["id"] == prize["coupon_id"]), {})
        results.append({
            "label": prize["label"],
            "coupon": {**user_coupon, "coupon": template},
            "is_redraw": False,
        })
        break  # got a real prize, stop
    return results
```

**Grant draws on order completion:**
In the `complete_order` endpoint (around line 1341), add after points are awarded:
```python
# Grant 1 gacha draw per completed order
GACHA_DRAW_QUOTA[order["buyer_email"]] = GACHA_DRAW_QUOTA.get(order["buyer_email"], 0) + 1
```

**Also clear in `reset_state()`:**
```python
GACHA_POOLS.clear()
GACHA_DRAW_QUOTA.clear()
next_gacha_pool_id = 1
```

**Seed demo draws for admin user:**
```python
GACHA_DRAW_QUOTA["admin@wakou-demo.com"] = 2  # demo draws
```

---

## Task 3: Backend — Points Optimization

**Files:**
- Modify: `backend/app/main.py`

**Enhancements:**

1. **Points expiry check** — Add expiry field to POINTS_LOGS entries and filter expired points from balance calculation:
```python
def _user_points_balance(email: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    expiry_months = POINTS_POLICY.get("expiry_months", 12)
    return sum(
        int(entry.get("delta_points") or 0)
        for entry in POINTS_LOGS
        if entry.get("email") == email
        and not _is_point_expired(entry, expiry_months)
    )

def _is_point_expired(entry: dict[str, Any], expiry_months: int) -> bool:
    """Check if a positive point entry has expired."""
    if int(entry.get("delta_points", 0)) <= 0:
        return False  # deductions don't expire
    recorded = entry.get("recorded_at", "")
    if not recorded:
        return False
    try:
        recorded_dt = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
        expiry_dt = recorded_dt + timedelta(days=expiry_months * 30)
        return datetime.now(timezone.utc) > expiry_dt
    except (ValueError, TypeError):
        return False
```

2. **Tier-based earn rates** — Already exists in `_resolve_membership`, ensure it's used in `complete_order`. Currently working correctly.

3. **Points redemption at checkout** — Add to order creation flow (see Task 4).

4. **Expose expiry info in growth API** — In `user_growth_center`, add point expiry date for each log item:
```python
for item in points_items:
    if int(item.get("delta_points", 0)) > 0:
        try:
            recorded_dt = datetime.fromisoformat(item["recorded_at"].replace("Z", "+00:00"))
            item["expires_at"] = (recorded_dt + timedelta(days=POINTS_POLICY["expiry_months"] * 30)).isoformat()
        except (ValueError, TypeError, KeyError):
            pass
```

---

## Task 4: Backend — Coupon Application at Order/Checkout Level

**Files:**
- Modify: `backend/app/main.py`

**Changes to `OrderPayload`:**
```python
class OrderPayload(BaseModel):
    product_id: int
    mode: str
    coupon_id: int | None = None      # USER_COUPONS[].id (not COUPONS[].id)
    points_to_redeem: int | None = 0  # points to use as discount
```

**Changes to `create_order` endpoint:**
After creating the order dict, before returning:

```python
# Apply coupon discount
coupon_discount_twd = 0
applied_coupon = None
if payload.coupon_id is not None:
    uc = next((c for c in USER_COUPONS if c["id"] == payload.coupon_id and c["user_email"] == user["email"]), None)
    if uc is None:
        raise HTTPException(status_code=400, detail="coupon not found")
    if uc["is_used"]:
        raise HTTPException(status_code=400, detail="coupon already used")
    now = datetime.now(timezone.utc).isoformat()
    if uc["expires_at"] < now:
        raise HTTPException(status_code=400, detail="coupon expired")
    template = next((c for c in COUPONS if c["id"] == uc["coupon_id"]), None)
    if template is None:
        raise HTTPException(status_code=400, detail="coupon template invalid")
    order_amount = int(product["price_twd"]) if product else 0
    if order_amount < template.get("min_order_twd", 0):
        raise HTTPException(status_code=400, detail=f"order amount must be >= NT${template['min_order_twd']}")
    
    if template["type"] == "fixed":
        coupon_discount_twd = template["value"]
    elif template["type"] == "percentage":
        coupon_discount_twd = order_amount - int(order_amount * template["value"] / 100)
    
    uc["is_used"] = True
    uc["used_at"] = now
    uc["used_on_order_id"] = order_id
    applied_coupon = {**uc, "coupon": template}

# Apply points redemption
points_discount_twd = 0
if payload.points_to_redeem and payload.points_to_redeem > 0:
    balance = _user_points_balance(user["email"])
    redeemable = min(payload.points_to_redeem, balance)
    points_value = POINTS_POLICY.get("point_value_twd", 1)
    points_discount_twd = redeemable * points_value
    if redeemable > 0:
        POINTS_LOGS.append({
            "id": len(POINTS_LOGS) + 1,
            "email": user["email"],
            "delta_points": -redeemable,
            "reason": f"訂單 #{order_id} 點數折抵",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

# Update order with discounts
total_discount = coupon_discount_twd + points_discount_twd
base_amount = int(product["price_twd"]) if product else 0
ORDERS[order_id]["coupon_discount_twd"] = coupon_discount_twd
ORDERS[order_id]["points_discount_twd"] = points_discount_twd
ORDERS[order_id]["final_amount_twd"] = max(base_amount - total_discount, 0)
ORDERS[order_id]["applied_coupon_id"] = payload.coupon_id
```

Add `applied_coupon` to the return value.

---

## Task 5: Backend — Admin APIs for Coupon & Gacha Management

**Files:**
- Modify: `backend/app/main.py`

**API endpoints:**

1. `GET /api/v1/admin/coupons` — List all coupon templates
2. `POST /api/v1/admin/coupons` — Create coupon template
3. `POST /api/v1/admin/coupons/issue` — Issue coupon to specific user (AdminIssueCouponPayload)
4. `GET /api/v1/admin/gacha/pools` — List gacha pools
5. `POST /api/v1/admin/gacha/pools` — Create/update gacha pool
6. `POST /api/v1/admin/gacha/grant-draws` — Grant extra draws to a user

**Pydantic models:**
```python
class AdminGrantDrawsPayload(BaseModel):
    user_email: str
    draws: int
    reason: str | None = None

class GachaPoolCreatePayload(BaseModel):
    name: str
    prizes: list[dict[str, Any]]
    bonus_draws: int = 0
    is_default: bool = False
```

**Implementation pattern:** Follow existing admin endpoint patterns (`_require_admin` or `_require_roles`).

---

## Task 6: Frontend — Fix Dashboard UI Consistency

**Files:**
- Modify: `frontend/src/app/views/DashboardView.vue`

**Problem:** The `/dashboard` main page renders a centered `point-card` while `/dashboard/:section` pages render a sidebar `point-box` with tier benefit cards. The user wants them to look the same.

**Solution:** Update `DashboardView.vue` to use the same layout as `AccountSectionView.vue`'s point-box — specifically adding the tier benefit cards below the progress bar (replacing the simple `point-perks` list).

**Changes:**
1. Replace the `<ul class="point-perks">` section with tier benefit cards matching AccountSectionView:
```html
<div class="tier-benefits" aria-label="membership benefits by tier">
  <article
    v-for="tier in membershipSnapshot.tiers.filter((item) => Number(item.threshold) > 0)"
    :key="`benefit-${tier.key}`"
    class="tier-benefit-card"
    :class="Number(membershipSnapshot.totalSpentTwd) >= Number(tier.threshold) ? 'active' : ''"
  >
    <p class="tier-benefit-title">{{ tier.name }}（NT$ {{ Number(tier.threshold).toLocaleString() }}）</p>
    <p class="tier-benefit-desc">{{ tier.perks.join("／") }}</p>
  </article>
</div>
```

2. Add matching CSS for `.tier-benefits`, `.tier-benefit-card`, `.tier-benefit-title`, `.tier-benefit-desc` (copy from AccountSectionView.vue styles).

3. Update point-card label from `可用回饋點數` to `可用點數` to match the sidebar version.

4. Remove `未讀訊息` from the `point-meta` line (it belongs elsewhere, not in the point card).

---

## Task 7: Frontend — Remove "特權禮遇" Section

**Files:**
- Modify: `frontend/src/app/views/DashboardView.vue`
- Modify: `frontend/src/app/views/AccountSectionView.vue`
- Modify: `frontend/src/app/router.js`

**Changes:**

1. **DashboardView.vue:** Remove the `benefits` board-row article (lines 233-240).

2. **AccountSectionView.vue:**
   - Remove `benefits` from `sectionMeta` object (lines 41-44).
   - Remove `benefits` from `navItems` array (line 58).
   - Remove `benefits` case from `sectionItems` computed (line 67).
   - Remove `benefits` case from `rowTitle` (line 117).
   - Remove `benefits` case from `rowDesc` (line 127).

3. **router.js:** Remove `benefits` from the route param regex:
   - Change `(timeline|rooms|orders|messages|benefits|points)` 
   - To `(timeline|rooms|orders|messages|points|coupons|gacha)`

---

## Task 8: Frontend — My Coupons Section in Dashboard

**Files:**
- Modify: `frontend/src/modules/account/service.js` — Add `fetchMyCoupons()` API call
- Modify: `frontend/src/app/views/AccountSectionView.vue` — Add "coupons" section with template

**Service function:**
```javascript
export async function fetchMyCoupons() {
  const response = await fetch("/api/v1/users/coupons", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load coupons", response.status);
  }
  return response.json();
}
```

**AccountSectionView changes:**

1. Add `coupons` to `sectionMeta`:
```javascript
coupons: {
  title: "我的折扣券",
  subtitle: "My coupons",
},
```

2. Add to `navItems`:
```javascript
{ key: "coupons", label: "我的折扣券", en: "My coupons" },
```

3. Import `fetchMyCoupons` from service.

4. Add `coupons` ref and load in `loadSection`:
```javascript
const coupons = ref([]);
// In loadSection, after main data load:
if (section.value === "coupons") {
  const couponData = await fetchMyCoupons();
  coupons.value = couponData.items || [];
}
```

5. Add coupon list template (new `v-else-if` section):
```html
<!-- Coupons: user's discount vouchers -->
<section v-else-if="section === 'coupons'" class="coupon-list">
  <article v-for="item in coupons" :key="item.id" class="coupon-card" :class="{ used: item.is_used, expired: item.is_expired }">
    <div class="coupon-value">
      <span v-if="item.coupon.type === 'fixed'">-NT${{ item.coupon.value }}</span>
      <span v-else>{{ item.coupon.value }}折</span>
    </div>
    <div class="coupon-info">
      <p class="coupon-desc">{{ item.coupon.description }}</p>
      <p class="coupon-condition" v-if="item.coupon.min_order_twd > 0">滿 NT${{ Number(item.coupon.min_order_twd).toLocaleString() }} 可用</p>
      <p class="coupon-condition" v-else>無門檻</p>
      <p class="coupon-expiry">
        <template v-if="item.is_used">已使用</template>
        <template v-else-if="item.is_expired">已過期</template>
        <template v-else>有效期限：{{ formatDate(item.expires_at) }}</template>
      </p>
    </div>
  </article>
</section>
```

6. Add coupon CSS styles matching the existing design language.

**DashboardView changes:**

Add new board-row for coupons (replacing the removed benefits row):
```html
<article class="board-row" role="button" tabindex="0" @click="navigateBoard('coupons')" @keydown.enter="navigateBoard('coupons')">
  <div class="row-head">
    <p class="row-ja">我的折扣券</p>
    <p class="row-en">My coupons</p>
  </div>
  <p class="row-desc">查看持有的折扣券與使用狀態。</p>
  <button class="row-link" type="button" @click.stop="navigateBoard('coupons')">&gt;</button>
</article>
```

---

## Task 9: Frontend — Gacha Draw UI

**Files:**
- Modify: `frontend/src/modules/account/service.js` — Add gacha API calls
- Modify: `frontend/src/app/views/AccountSectionView.vue` — Add "gacha" section

**Service functions:**
```javascript
export async function fetchGachaStatus() {
  const response = await fetch("/api/v1/gacha/status", {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw buildHttpError("load gacha status", response.status);
  }
  return response.json();
}

export async function performGachaDraw(poolId) {
  const body = {};
  if (poolId) body.pool_id = poolId;
  const response = await fetch("/api/v1/gacha/draw", {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw buildHttpError("gacha draw", response.status);
  }
  return response.json();
}
```

**AccountSectionView changes:**

1. Add `gacha` to `sectionMeta`:
```javascript
gacha: {
  title: "幸運抽獎",
  subtitle: "Lucky draw",
},
```

2. Add to `navItems`:
```javascript
{ key: "gacha", label: "幸運抽獎", en: "Lucky draw" },
```

3. Add gacha state refs:
```javascript
const gachaStatus = ref({ draws_available: 0, pool: null });
const gachaResults = ref([]);
const isDrawing = ref(false);
const showResult = ref(false);
```

4. Load gacha status in `loadSection`:
```javascript
if (section.value === "gacha") {
  const status = await fetchGachaStatus();
  gachaStatus.value = status;
}
```

5. Add draw function:
```javascript
async function drawGacha() {
  if (isDrawing.value || gachaStatus.value.draws_available <= 0) return;
  isDrawing.value = true;
  showResult.value = false;
  try {
    const result = await performGachaDraw();
    gachaResults.value = result.results || [];
    gachaStatus.value.draws_available = result.draws_remaining;
    showResult.value = true;
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : "抽獎失敗";
  } finally {
    isDrawing.value = false;
  }
}
```

6. Add gacha template:
```html
<!-- Gacha: lucky draw -->
<section v-else-if="section === 'gacha'" class="gacha-section">
  <div class="gacha-info">
    <p class="gacha-draws">剩餘抽獎次數：<strong>{{ gachaStatus.draws_available }}</strong> 次</p>
    <p class="gacha-hint">每購買一件商品可獲得一次抽獎機會</p>
  </div>

  <div class="gacha-pool" v-if="gachaStatus.pool">
    <p class="pool-title">{{ gachaStatus.pool.name }}</p>
    <div class="prize-grid">
      <div v-for="(prize, idx) in gachaStatus.pool.prizes" :key="idx" class="prize-card">
        <span class="prize-label">{{ prize.label }}</span>
      </div>
    </div>
  </div>

  <button
    class="gacha-draw-btn"
    type="button"
    :disabled="isDrawing || gachaStatus.draws_available <= 0"
    @click="drawGacha"
  >
    {{ isDrawing ? "抽獎中..." : gachaStatus.draws_available > 0 ? "開始抽獎" : "沒有抽獎次數" }}
  </button>

  <div v-if="showResult && gachaResults.length > 0" class="gacha-result">
    <div v-for="(result, idx) in gachaResults" :key="idx" class="result-card" :class="{ redraw: result.is_redraw }">
      <p class="result-label">{{ result.is_redraw ? "🔄 再抽一次！" : "🎉 恭喜獲得" }}</p>
      <p class="result-prize">{{ result.label }}</p>
      <p v-if="result.coupon" class="result-detail">{{ result.coupon.coupon.description }}</p>
    </div>
  </div>
</section>
```

7. Add gacha CSS.

**DashboardView changes:**
Add new board-row for gacha:
```html
<article class="board-row" role="button" tabindex="0" @click="navigateBoard('gacha')" @keydown.enter="navigateBoard('gacha')">
  <div class="row-head">
    <p class="row-ja">幸運抽獎</p>
    <p class="row-en">Lucky draw</p>
  </div>
  <p class="row-desc">每次購買即可抽獎，贏取折扣券！</p>
  <button class="row-link" type="button" @click.stop="navigateBoard('gacha')">&gt;</button>
</article>
```

---

## Task 10: Frontend — Checkout Coupon Selection

**Files:**
- Modify: `frontend/src/app/views/CheckoutView.vue`
- Modify: `frontend/src/modules/checkout/service.js`

**Changes to CheckoutView.vue:**

1. Import `fetchMyCoupons` from account service (or add a new `fetchAvailableCoupons` to checkout service).

2. Add coupon selection state:
```javascript
const availableCoupons = ref([]);
const selectedCouponId = ref(null);
const pointsToRedeem = ref(0);
const userPointsBalance = ref(0);

onMounted(async () => {
  try {
    const [couponResp, growthResp] = await Promise.all([
      fetch("/api/v1/users/coupons/available?order_amount_twd=" + (cartItems.value[0]?.price_twd || 0), { headers: authHeaders() }).then(r => r.json()),
      fetch("/api/v1/users/growth", { headers: authHeaders() }).then(r => r.json()),
    ]);
    availableCoupons.value = couponResp.items || [];
    userPointsBalance.value = growthResp.points?.balance || 0;
  } catch { /* non-critical */ }
});
```

3. Add coupon selection UI between mode selection and action footer:
```html
<!-- Coupon & Points Section -->
<div class="discount-section" v-if="availableCoupons.length > 0 || userPointsBalance > 0">
  <h3>優惠折抵</h3>
  
  <!-- Coupon selection -->
  <div v-if="availableCoupons.length > 0" class="coupon-select">
    <label>選擇折扣券</label>
    <select v-model="selectedCouponId">
      <option :value="null">不使用折扣券</option>
      <option v-for="c in availableCoupons" :key="c.id" :value="c.id">
        {{ c.coupon.description }} (有效至 {{ formatDate(c.expires_at) }})
      </option>
    </select>
  </div>
  
  <!-- Points redemption -->
  <div v-if="userPointsBalance > 0" class="points-redeem">
    <label>使用回饋點數 (可用 {{ userPointsBalance }} 點)</label>
    <input type="number" v-model.number="pointsToRedeem" :max="userPointsBalance" min="0" />
    <small>1 點 = NT$1 折抵</small>
  </div>
</div>
```

4. Update `submitCheckout` to pass coupon_id and points_to_redeem:
```javascript
const created = await createOrder({
  product_id: items[0].id,
  mode: checkoutForm.mode,
  coupon_id: selectedCouponId.value,
  points_to_redeem: pointsToRedeem.value,
});
```

5. Update checkout service's `createOrder` to accept the new fields.

---

## Task 11: Frontend — Points Display Optimization

**Files:**
- Modify: `frontend/src/app/views/AccountSectionView.vue`

**Changes to points section display:**

When `section === 'points'`, show enhanced point history with expiry info:
```html
<section v-else-if="section === 'points'" class="points-list">
  <article v-for="item in sectionItems" :key="item.id" class="points-row">
    <div>
      <p class="title">{{ item.reason || "點數紀錄" }}</p>
      <p class="desc">
        {{ item.delta_points > 0 ? "+" : "" }}{{ item.delta_points }} 點 ・ {{ formatDate(item.recorded_at) }}
      </p>
      <p v-if="item.delta_points > 0 && item.expires_at" class="expiry-hint">
        有效期限：{{ formatDate(item.expires_at) }}
      </p>
    </div>
  </article>
</section>
```

Add CSS for `.expiry-hint`:
```css
.expiry-hint {
  color: #8c7b6c;
  font-size: 0.72rem;
  margin: 0.15rem 0 0;
}
```

---

## Task 12: Integration Testing & Verification

**Files:**
- Backend tests in `backend/tests/`
- Frontend build check

**Steps:**

1. Run existing backend tests to ensure no regressions:
```bash
pytest backend/tests -v
```

2. Run frontend build:
```bash
npm --prefix frontend run build
```

3. Run frontend tests:
```bash
npm --prefix frontend run test
```

4. Manual verification checklist:
   - [ ] Dashboard point card matches section view point box
   - [ ] "特權禮遇" section fully removed
   - [ ] Coupon list shows on /dashboard/coupons
   - [ ] Gacha draw works on /dashboard/gacha
   - [ ] Coupon selection available at checkout
   - [ ] Points expiry shown in point history
   - [ ] Admin can issue coupons via API
   - [ ] Admin can configure gacha pools via API
   - [ ] Order completion grants gacha draw
