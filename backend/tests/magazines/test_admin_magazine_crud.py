def test_admin_can_create_update_delete_magazine_article(client, admin_token):
    create_response = client.post(
        "/api/v1/admin/magazines/articles",
        json={
            "brand": "Nanamica",
            "title": {
                "zh-Hant": "城市機能風格指南",
                "ja": "シティ機能スタイルガイド",
                "en": "Urban Functional Style Guide",
            },
            "description": {
                "zh-Hant": "結合防水素材與極簡輪廓的穿搭提案。",
                "ja": "防水素材とミニマルシルエットの提案。",
                "en": "A styling proposal that blends weatherproof fabrics and minimal silhouettes.",
            },
            "image_url": "https://picsum.photos/seed/mag-test-create/1200/800",
            "gallery_urls": [
                "https://picsum.photos/seed/mag-test-gallery-1/1200/800",
                "https://picsum.photos/seed/mag-test-gallery-2/1200/800",
            ],
            "body": {
                "zh-Hant": "段落一\n\n段落二",
                "ja": "第一段落\n\n第二段落",
                "en": "Paragraph one\n\nParagraph two",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert isinstance(created["article_id"], int)
    assert created["slug"] == "urban-functional-style-guide"
    assert len(created["gallery_urls"]) == 2

    list_response = client.get("/api/v1/magazines")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert any(
        item.get("article_id") == created["article_id"]
        for brand in list_payload["items"]
        for item in brand.get("contents", [])
    )

    update_response = client.patch(
        f"/api/v1/admin/magazines/articles/{created['article_id']}",
        json={
            "title": {"zh-Hant": "城市機能風格總覽"},
            "gallery_urls": [
                "https://picsum.photos/seed/mag-test-gallery-updated/1200/800",
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"]["zh-Hant"] == "城市機能風格總覽"
    assert updated["gallery_urls"] == ["https://picsum.photos/seed/mag-test-gallery-updated/1200/800"]

    delete_response = client.delete(
        f"/api/v1/admin/magazines/articles/{created['article_id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    list_after_delete = client.get("/api/v1/magazines").json()
    assert all(
        item.get("article_id") != created["article_id"]
        for brand in list_after_delete["items"]
        for item in brand.get("contents", [])
    )


def test_buyer_cannot_mutate_magazine_articles(client, buyer_token):
    response = client.post(
        "/api/v1/admin/magazines/articles",
        json={
            "brand": "Rolex",
            "title": {"zh-Hant": "X", "ja": "X", "en": "X"},
            "description": {"zh-Hant": "X", "ja": "X", "en": "X"},
            "image_url": "https://picsum.photos/seed/mag-test-deny/1200/800",
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 403
