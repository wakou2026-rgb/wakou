from pydantic import BaseModel


class ProductItem(BaseModel):
    id: int
    sku: str
    category: str
    name: str
    description: str
    image_urls: list[str]
    price_twd: int
    grade: str


class ProductListResponse(BaseModel):
    items: list[ProductItem]


class ProductDetailResponse(ProductItem):
    pass
