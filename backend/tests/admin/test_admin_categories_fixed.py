def test_admin_cannot_create_new_category(client, admin_token):
    response = client.post(
        "/api/v1/admin/categories",
        json={
            "id": "new-category",
            "title": {"zh-Hant": "新分類", "ja": "新カテゴリ", "en": "New Category"},
            "image": "/main.png",
            "sort_order": 99,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


def test_admin_cannot_delete_fixed_category(client, admin_token):
    response = client.delete(
        "/api/v1/admin/categories/watch",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


def test_admin_can_update_fixed_category_title_and_image(client, admin_token):
    update_response = client.patch(
        "/api/v1/admin/categories/watch",
        json={
            "title": {"zh-Hant": "腕錶調整", "ja": "クラシックウォッチ", "en": "Classic Watches"},
            "image": "/Watches.png",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["id"] == "watch"
    assert body["title"]["zh-Hant"] == "腕錶調整"
    assert body["image"] == "/Watches.png"
