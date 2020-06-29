import json
from decimal import Decimal as d

with open("data/products/products.json", "r") as file:
    products = json.load(file)


EU_countries = [
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LI",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
    "UK",
    "FO"
    ]


def calculate_total_weight_of_order(order):
    weight = d(0)
    for item in order["line_items"]:
        product_item = products["id"][str(item["product_id"])]
        try:
            weight += d(product_item["weight"]) * item["quantity"]
        except: 
            print(item["name"] + " has no weight")
    return weight


def order_contains_only_spores(order):
    only_starters = True
    for item in order["line_items"]:
        product_item = products["id"][str(item["product_id"])]
        if (product_item["categories"][0]["slug"] not in ["koji", "tempeh", "natto"] or
            product_item["sku"] == "nattobeans"):
            only_starters = False
    return only_starters

def order_contains_only_food(order):
    only_food = True
    for item in order["line_items"]:
        product_item = products["id"][str(item["product_id"])]
        if product_item["categories"][0] not in ["miso", "shoyu"]:
            only_food = False
    return only_food