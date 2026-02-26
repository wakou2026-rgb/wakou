def test_create_ecpay_checkout_form_for_order(client, buyer_token, payable_order_id):
    response = client.post(
        f"/api/v1/payments/ecpay/{payable_order_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 200
    assert "CheckMacValue" in response.json()["payload"]
