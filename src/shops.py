from woocommerce import API
from settings import credentials

shops = {}

for shop in credentials["shops"]:
    shops[shop["url"]] = API(
        url=shop["url"],
        consumer_key=shop["consumer_key"],
        consumer_secret=shop["consumer_secret"],
        wp_api=True,
        version="wc/v3",
        timeout=20
        )