import math
import re
from typing import List
from datetime import datetime
from flask import Flask, request, jsonify
from uuid import uuid4

flask_app = Flask(__name__)

receipts = {}  # this is the dictionary used to store the (receipt id -> reward points) mapping
required_receipt_attributes = ["retailer", "total", "items", "purchaseDate", "purchaseTime"]
required_item_attributes = ["shortDescription", "price"]
RECEIPT_DATE_FORMAT = '%Y-%m-%d'
RECEIPT_TIME_FORMAT = '%H:%M'
POINTS_RETAILER_NAME_ALPHANUM_CHARACTER = 1
POINTS_TOTAL_HAS_NO_CENTS = 50
POINTS_TOTAL_IS_MULTIPLE_OF_QUARTERS = 25
POINTS_ITEMS_COUNT = 5
POINTS_ITEM_DESCRIPTION = 0.2
POINTS_ODD_PURCHASE_DAY = 6
POINTS_VALID_PURCHASE_HOUR = 10
REWARD_ITEM_DESCRIPTION_LENGTH_FACTOR = 3
REWARD_HOUR_START = 14
REWARD_HOUR_END = 16
HOST = "0.0.0.0"
PORT = 5000


def validate_retailer_name(retailer_name: str):
    """ Validates if retailer name contains at least 1 non-whitespace character """
    if not re.match(r"\S+", retailer_name):
        raise ValueError(f"Error: invalid receipt retailer name ({retailer_name})")


def score_retailer(retailer_name: str) -> int:
    """ Validates retailer name and calculates its points """
    validate_retailer_name(retailer_name)
    return sum(int(c.isalnum()) * POINTS_RETAILER_NAME_ALPHANUM_CHARACTER for c in retailer_name)


def validate_total(total: str):
    """ Validates receipt total amount """
    if not re.match(r"^\d+\.\d{2}$", total):
        raise ValueError(f"Error: invalid receipt total ({total})")


def score_total(total: str) -> int:
    """ Validates total amount and calculates its points """
    validate_total(total)
    parsed_total = float(total)
    rounded_total = round(parsed_total)
    points = 0
    if parsed_total == rounded_total:
        points += POINTS_TOTAL_HAS_NO_CENTS
    if parsed_total % 0.25 == 0:
        points += POINTS_TOTAL_IS_MULTIPLE_OF_QUARTERS
    return points


def validate_item(description: str, price: str):
    """ Validates both the item description and item price formats """
    if not re.match(r"^[\w\s\-]+$", description):
        raise ValueError(f"Error: invalid item description ({description})")
    if not re.match(r"^\d+\.\d{2}$", price):
        raise ValueError(f"Error: invalid item price ({price})")


def score_items(items: List[dict]) -> int:
    """ Validates item formats and calculate its points """
    count = len(items)
    points = (count // 2) * POINTS_ITEMS_COUNT
    for item in items:
        description = item["shortDescription"]
        price = item["price"]
        validate_item(description, price)
        if len(description.strip()) % REWARD_ITEM_DESCRIPTION_LENGTH_FACTOR == 0:
            points += math.ceil(float(price) * POINTS_ITEM_DESCRIPTION)
    return points


def validate_and_parse_date_time(date: str, time: str) -> tuple[datetime, datetime]:
    """ Validates date and time formats using try-except """
    try:
        date_obj = datetime.strptime(date, RECEIPT_DATE_FORMAT)
    except ValueError:
        raise ValueError(f"Error: invalid receipt purchase date ({date})")
    try:
        time_obj = datetime.strptime(time, RECEIPT_TIME_FORMAT)
    except ValueError:
        raise ValueError(f"Error: invalid receipt purchase time ({time})")
    # here we use two try-except blocks to provide more granularity
    return date_obj, time_obj


def score_date_time(date: str, time: str) -> int:
    """ Validates date and time formats and calculate its points """
    points = 0
    date_obj, time_obj = validate_and_parse_date_time(date, time)
    if date_obj.day % 2 != 0:
        points += POINTS_ODD_PURCHASE_DAY
    if REWARD_HOUR_START <= time_obj.hour < REWARD_HOUR_END:
        points += POINTS_VALID_PURCHASE_HOUR
    return points


def validate_receipt_json_structure(receipt: dict):
    """ Validates structure of the json input """
    for attribute in required_receipt_attributes:
        if attribute not in receipt:  # check if attribute is missing
            raise ValueError(f"Error: missing {attribute} in receipt")
        if attribute != "items" and not isinstance(receipt[attribute], str):  # check attribute type
            raise ValueError(f"Error: invalid {attribute} format")

    if not isinstance(receipt["items"], List):
        raise ValueError("Error: invalid receipt items list format")
    if len(receipt["items"]) < 1:  # check if the items list is empty
        raise ValueError("Error: receipt items list is empty")
    for item in receipt["items"]:
        if not isinstance(item, dict):
            raise ValueError("Error: invalid receipt item format")
        for attribute in required_item_attributes:
            if not isinstance(item[attribute], str):
                raise ValueError("Error: invalid receipt item format")


def calculate_points(receipt: dict) -> int:
    """ Calculates points earned from each component of the receipt """
    points = 0
    points += score_retailer(receipt['retailer'])
    points += score_total(receipt['total'])
    points += score_items(receipt['items'])
    points += score_date_time(receipt['purchaseDate'], receipt['purchaseTime'])
    return points


@flask_app.route('/receipts/process', methods=['POST'])
def process_receipt():
    """
    Router for receipt processing requests, which first generates a unique id for
    each receipt. The input JSON is validated and points are calculated for the
    receipt. The results are persisted in the application's memory and the id is
    returned to the user.

    Returns:
        400 Error if input JSON is invalid
        200 OK and generated receipt id if input JSON is valid
    """
    receipt = request.json
    receipt_id = str(uuid4())
    try:
        validate_receipt_json_structure(receipt)
        receipts[receipt_id] = calculate_points(receipt)
        # Here we update the (receipt id -> reward points) mapping without using locks. This is because,
        # as per the design doc, each request to the process receipt api is not idempotent. Therefore, the
        # only modifications to the receipt scores map would be adding new key value pairs, and race
        # condition is impossible even when concurrently handling requests.
    except ValueError as e:
        return jsonify({"error": str(e)}), 400  # return appropriate error messages
    else:
        return jsonify({"id": receipt_id})


@flask_app.route('/receipts/<receipt_id>/points', methods=['GET'])
def get_points(receipt_id):
    """
    Router for receipt processing requests. The input receipt id is used
    to look up its associated receipt in the application's memory.

    Returns:
        404 Error if the receipt id is not found
        200 OK and the calculated points for the receipt if receipt id is present in memory
    """
    if receipt_id not in receipts:
        return jsonify({"error": f"ERROR: receipt id not found ({receipt_id})"}), 404
    else:
        return jsonify({"points": receipts[receipt_id]})  # read the previously computed score


if __name__ == '__main__':
    flask_app.run(host=HOST, port=PORT, threaded=True)
    # setting threaded=True allows Flask to concurrently handle requests
