# CommRoom & Order Flow Redesign

## Goal
Transform the purchase flow into an "inquiry-first" model where users enter a dedicated communication room (CommRoom) instead of direct checkout. This room serves as a manual consultation and negotiation space, capturing chat history, image evidence, final quote acceptance, and manual transfer proof upload.

## Architecture & Data Changes (Backend - `main.py`)
Currently, `COMM_ROOMS` holds basic `{from: str, message: str}` strings.
1. **Messages Update**: 
   - Need rich messages: `{"id": int, "from": "buyer|admin|system", "message": "...", "image_url": "...", "timestamp": "...", "is_deleted": False}`
2. **Order Model Update**:
   - `final_price_twd`: to store negotiated item price (defaults to `amount_twd`)
   - `shipping_fee_twd`: established during quote
   - `discount_twd`: optional discount
   - `transfer_proof_url`: string, for manual payment evidence
   - `transfer_status`: "pending" | "uploaded" | "confirmed"
   - Order Statuses: "inquiring" (new default) -> "quoted" -> "buyer_accepted" -> "proof_uploaded" -> "paid" -> "completed"
3. **New Endpoints**:
   - `POST /api/v1/comm-rooms/{room_id}/messages`: Allow buyer and admin to post messages + images.
   - `POST /api/v1/comm-rooms/{room_id}/final-quote`: Admin sets `final_price_twd`, `shipping_fee_twd`, `discount_twd`. Changes order status to "quoted".
   - `POST /api/v1/comm-rooms/{room_id}/accept-quote`: Buyer accepts. Status -> "buyer_accepted".
   - `POST /api/v1/comm-rooms/{room_id}/upload-proof`: Buyer uploads transfer proof. Status -> "proof_uploaded".
   - `POST /api/v1/orders/{order_id}/confirm-payment`: Admin verifies proof, status -> "paid".

## Frontend Components
1. **ProductDetailView.vue**: 
   - Change "直接下單" (Buy Now) to "發起諮詢並下單" (Inquiry & Order). 
   - Add confirm dialog: "此商品為手工/高價物件，將為您開啟專屬諮詢室確認細節..."
   - Change order creation to always use `mode: "inquiry"`.
2. **CommRoomView.vue**:
   - Left pane: Show product thumb, `amount_twd` (original), `final_price_twd` (negotiated), `shipping_fee_twd`.
   - Center pane:
     - Two-way chat UI (buyer/admin).
     - Image upload input (renders "官方認證" badge + timestamp for admin uploads).
     - Read-only system logs for price changes.
   - Right pane (Actions):
     - Admin: Set quote (Price, Shipping, Discount) -> "發送最終報價".
     - Buyer: If status is "quoted", show "接受報價並前往付款" button.
     - Buyer: If status is "buyer_accepted", show bank details and "Upload Transfer Proof" form.
     - Admin: If status is "proof_uploaded", show "確認收款" button.
3. **Service Logic**: Add API calls matching new backend endpoints.
