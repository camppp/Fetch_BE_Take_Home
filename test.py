import json
import uuid
import pytest
from concurrent.futures import ThreadPoolExecutor
from app import flask_app

valid_receipts = {
    json.dumps({
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:01",
        "items": [
            {
                "shortDescription": "Mountain Dew 12PK",
                "price": "6.49"
            }, {
                "shortDescription": "Emils Cheese Pizza",
                "price": "12.25"
            }, {
                "shortDescription": "Knorr Creamy Chicken",
                "price": "1.26"
            }, {
                "shortDescription": "Doritos Nacho Cheese",
                "price": "3.35"
            }, {
                "shortDescription": "   Klarbrunn 12-PK 12 FL OZ  ",
                "price": "12.00"
            }
        ],
        "total": "35.35"
    }): 28,
    json.dumps({
        "retailer": "M&M Corner Market",
        "purchaseDate": "2022-03-20",
        "purchaseTime": "14:33",
        "items": [
            {
                "shortDescription": "Gatorade",
                "price": "2.25"
            }, {
                "shortDescription": "Gatorade",
                "price": "2.25"
            }, {
                "shortDescription": "Gatorade",
                "price": "2.25"
            }, {
                "shortDescription": "Gatorade",
                "price": "2.25"
            }
        ],
        "total": "9.00"
    }): 109,
    json.dumps({
        "retailer": "Walgreens",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "08:13",
        "total": "2.65",
        "items": [
            {"shortDescription": "Pepsi - 12-oz", "price": "1.25"},
            {"shortDescription": "Dasani", "price": "1.40"}
        ]
    }): 15,
    json.dumps({
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [
            {"shortDescription": "Pepsi - 12-oz", "price": "1.25"}
        ]
    }): 31
}

required_receipt_attributes = ["retailer", "total", "items", "purchaseDate", "purchaseTime"]


@pytest.fixture
def app():
    app = flask_app
    app.config['DEBUG'] = True
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def simple_receipt_skeleton():
    return {
        "retailer": "Target",
        "purchaseDate": "2022-01-02",
        "purchaseTime": "13:13",
        "total": "1.25",
        "items": [
            {"shortDescription": "Pepsi - 12-oz", "price": "1.25"}
        ]
    }


def test_process_valid_receipts(client):
    for test_json, expected_points in valid_receipts.items():
        expected = {"points": expected_points}
        process_response = client.post('/receipts/process', content_type='application/json', data=test_json)
        receipt_id = json.loads(process_response.data)["id"]
        assert process_response.status_code == 200
        try:
            uuid.UUID(receipt_id)
            assert True
        except ValueError:
            assert False
        get_response = client.get(f'/receipts/{receipt_id}/points')
        assert get_response.status_code == 200
        assert expected == json.loads(get_response.data)


def test_process_receipts_unique_ids(client, simple_receipt_skeleton):
    receipt_ids = []
    for i in range(10):
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        receipt_ids.append(json.loads(process_response.data)["id"])
    assert len(set(receipt_ids)) == len(receipt_ids)


def test_process_receipts_invalid_retailer_name(client, simple_receipt_skeleton):
    invalid_names = ["   ", "    ", "", "             "]
    for name in invalid_names:
        expected = {"error": f"Error: invalid receipt retailer name ({name})"}
        simple_receipt_skeleton["retailer"] = name
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_purchase_date(client, simple_receipt_skeleton):
    invalid_dates = ["test", "0000-01-01", "2023-15-15", "2023-10-99", "dummydummydummy", "", '9999-99-99']
    for date in invalid_dates:
        expected = {"error": f"Error: invalid receipt purchase date ({date})"}
        simple_receipt_skeleton["purchaseDate"] = date
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_attribute_formats_except_items(client, simple_receipt_skeleton):
    invalid_elements = [None, [], 25, 3.88, {}]
    for attribute in required_receipt_attributes:
        if attribute != "items":
            original = simple_receipt_skeleton[attribute]
            expected = {"error": f"Error: invalid {attribute} format"}
            for elem in invalid_elements:
                simple_receipt_skeleton[attribute] = elem
                process_response = client.post('/receipts/process',
                                               content_type='application/json',
                                               data=json.dumps(simple_receipt_skeleton))
                assert process_response.status_code == 400
                assert json.loads(process_response.data) == expected
            simple_receipt_skeleton[attribute] = original


def test_process_receipts_invalid_items_format(client, simple_receipt_skeleton):
    invalid_elements = [None, 25, 3.88, {}, ""]
    expected = {"error": f"Error: invalid receipt items list format"}
    for elem in invalid_elements:
        simple_receipt_skeleton["items"] = elem
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_items_list_length(client, simple_receipt_skeleton):
    expected = {"error": "Error: receipt items list is empty"}
    simple_receipt_skeleton["items"] = []
    process_response = client.post('/receipts/process',
                                   content_type='application/json',
                                   data=json.dumps(simple_receipt_skeleton))
    assert process_response.status_code == 400
    assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_item_formats(client, simple_receipt_skeleton):
    invalid_elements = [None, 25, 3.88, [], ""]
    expected = {"error": "Error: invalid receipt item format"}
    original = simple_receipt_skeleton["items"][0]
    for elem in invalid_elements:
        simple_receipt_skeleton["items"][0] = elem
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected
    simple_receipt_skeleton["items"][0] = original
    invalid_elements = [None, 25, 3.88, [], {}]
    for elem in invalid_elements:
        simple_receipt_skeleton["items"][0]["price"] = elem
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected
        simple_receipt_skeleton["items"][0] = original
        simple_receipt_skeleton["items"][0]["shortDescription"] = elem
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_item_descriptions(client, simple_receipt_skeleton):
    invalid_descriptions = ["", "???", "&&&&", "<<<<>>>>", "\\\\"]
    for description in invalid_descriptions:
        expected = {"error": f"Error: invalid item description ({description})"}
        simple_receipt_skeleton["items"][0]["shortDescription"] = description
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_item_price(client, simple_receipt_skeleton):
    invalid_prices = ["test", "0", "333", "", "5.310", ".22"]
    for price in invalid_prices:
        expected = {"error": f"Error: invalid item price ({price})"}
        simple_receipt_skeleton["items"][0]["price"] = price
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_purchase_time(client, simple_receipt_skeleton):
    invalid_times = ["test", "13:99", "99:13", "99:99", "dummydummydummy", "", '13-13']
    for time in invalid_times:
        expected = {"error": f"Error: invalid receipt purchase time ({time})"}
        simple_receipt_skeleton["purchaseTime"] = time
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_process_receipts_invalid_total(client, simple_receipt_skeleton):
    invalid_totals = ["test", "0", "333", "", "5.310", ".22"]
    for total in invalid_totals:
        expected = {"error": f"Error: invalid receipt total ({total})"}
        simple_receipt_skeleton["total"] = total
        process_response = client.post('/receipts/process',
                                       content_type='application/json',
                                       data=json.dumps(simple_receipt_skeleton))
        assert process_response.status_code == 400
        assert json.loads(process_response.data) == expected


def test_get_points_nonexistent_id(client):
    res = client.get('/receipts/test/points')
    assert res.status_code == 404
    expected = {'error': 'ERROR: receipt id not found (test)'}
    assert json.loads(res.data) == expected


def test_get_points_idempotency(client, simple_receipt_skeleton):
    process_response = client.post('/receipts/process',
                                   content_type='application/json',
                                   data=json.dumps(simple_receipt_skeleton))
    receipt_id = json.loads(process_response.data)["id"]
    for i in range(5):
        get_response = client.get(f'/receipts/{receipt_id}/points')
        assert get_response.status_code == 200
        assert json.loads(get_response.data)["points"] == 31


def test_process_receipts_concurrency(client, simple_receipt_skeleton):
    params = [simple_receipt_skeleton] * 3000

    def test_post(json_param):
        return client.post('/receipts/process', content_type='application/json', json=json_param).text

    with ThreadPoolExecutor(max_workers=50) as pool:
        for _ in list(pool.map(test_post, params)):
            pass


def test_get_points_concurrency(client, simple_receipt_skeleton):
    process_response = client.post('/receipts/process',
                                   content_type='application/json',
                                   data=json.dumps(simple_receipt_skeleton))
    receipt_id = json.loads(process_response.data)["id"]
    params = [receipt_id] * 3000
    
    def test_get(id_param):
        return client.post(f'/receipts/{id_param}/points').text

    with ThreadPoolExecutor(max_workers=50) as pool:
        for _ in list(pool.map(test_get, params)):
            pass
