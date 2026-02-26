const CART_KEY = "wakou_cart_lines";

function normalizeCartLine(line) {
  if (!line || typeof line !== "object") {
    return null;
  }

  const rawId = line.id ?? line.product_id ?? line.productId;
  const id = Number(rawId);
  if (!Number.isInteger(id) || id <= 0) {
    return null;
  }

  const qty = Math.max(1, Number(line.qty || 1));
  const priceTwd = Number(line.priceTwd ?? line.price_twd ?? 0);
  const imageUrls = Array.isArray(line.imageUrls)
    ? line.imageUrls
    : Array.isArray(line.image_urls)
      ? line.image_urls
      : [];

  return {
    ...line,
    id,
    qty,
    priceTwd,
    imageUrls
  };
}

function readStoredCart() {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(CART_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.map(normalizeCartLine).filter(Boolean);
  } catch {
    return [];
  }
}

function writeStoredCart(lines) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(CART_KEY, JSON.stringify(lines));
}

export function getCartItems() {
  return readStoredCart();
}

export function addCartItem(product) {
  const lines = readStoredCart();
  const existing = lines.find((line) => line.id === product.id);
  if (existing) {
    existing.qty += 1;
  } else {
    lines.push({ ...product, qty: 1 });
  }
  writeStoredCart(lines);
  return lines;
}

export function updateCartQty(productId, qty) {
  const lines = readStoredCart().map((line) => {
    if (line.id !== productId) {
      return line;
    }
    return { ...line, qty: Math.max(1, qty) };
  });
  writeStoredCart(lines);
  return lines;
}

export function removeCartItem(productId) {
  const lines = readStoredCart().filter((line) => line.id !== productId);
  writeStoredCart(lines);
  return lines;
}

export function clearCartItems() {
  writeStoredCart([]);
}

export function createCart() {
  const lines = [];
  return {
    add(product) {
      lines.push(product);
    },
    items() {
      return lines.slice();
    }
  };
}
