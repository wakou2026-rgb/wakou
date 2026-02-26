export async function browseCatalog({ lang = "zh-Hant", category = "" } = {}) {
  const query = new URLSearchParams({ lang });
  if (category) {
    query.set("category", category);
  }
  const response = await fetch(`/api/v1/products?${query.toString()}`, { method: "GET" });
  if (!response.ok) {
    throw new Error("load catalog failed");
  }

  const data = await response.json();
  return data.items.map((item) => ({
    id: item.id,
    sku: item.sku,
    category: item.category,
    name: item.name,
    description: item.description,
    imageUrls: Array.isArray(item.image_urls) ? item.image_urls : [],
    priceTwd: item.price_twd,
    grade: item.grade
  }));
}

export async function fetchProductDetail(productId, { lang = "zh-Hant" } = {}) {
  const response = await fetch(`/api/v1/products/${productId}?lang=${encodeURIComponent(lang)}`, {
    method: "GET"
  });
  if (!response.ok) {
    throw new Error("load product detail failed");
  }
  const item = await response.json();
  return {
    id: item.id,
    sku: item.sku,
    name: item.name,
    category: item.category,
    priceTwd: item.price_twd,
    grade: item.grade,
    description: item.description,
    imageUrls: Array.isArray(item.image_urls) ? item.image_urls : []
  };
}


export async function fetchPublicMagazines() {
  const response = await fetch("/api/v1/magazines");
  if (!response.ok) {
    throw new Error("load magazines failed");
  }
  return response.json();
}
