from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from .schemas import ProductDetailResponse, ProductItem, ProductListResponse
from .service import get_product, list_products, resolve_name, resolve_product_extra

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def products_list(
    category: str | None = None,
    lang: str = "en",
    session: Session = Depends(get_db_session),
) -> ProductListResponse:
    items = []
    for product in list_products(session, category):
        description, image_urls = resolve_product_extra(product.id, lang)
        items.append(
            ProductItem(
                id=product.id,
                sku=product.sku,
                category=product.category,
                name=resolve_name(product, lang),
                description=description,
                image_urls=image_urls,
                price_twd=product.price_twd,
                grade=product.grade,
            )
        )
    return ProductListResponse(items=items)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def product_detail(
    product_id: int,
    lang: str = "en",
    session: Session = Depends(get_db_session),
) -> ProductDetailResponse:
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    description, image_urls = resolve_product_extra(product.id, lang)
    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        category=product.category,
        name=resolve_name(product, lang),
        description=description,
        image_urls=image_urls,
        price_twd=product.price_twd,
        grade=product.grade,
    )
