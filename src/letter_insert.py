"""Creates and prints a pdf with the correct item-"""
from datetime import date
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
import os
import json
import cups
from string import Template
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '4')
from gi.repository import Gtk, Gdk, GObject, GtkSource

import __main__ as m
import settings

import webbrowser

conn = cups.Connection()

font_config = FontConfiguration()
sourceCSS = CSS(
    string="""
    @page { 
        size: A4;
        margin: 7mm; 
    }

    @media print  
    {
        p {
            page-break-inside: avoid;
        }
    }

    * {
        box-sizing: border-box;
    }

    html {
        font-family: Myriad Pro;
        font-size: 4mm;
        }

    body {
        margin: 0;
        text-align: justify;
    }
    
    p {
        margin: 0.5rem 0;
    }

    h4 {
        margin: 0;
        font-weight: 400;
        font-size: 1.5rem;
    }

    section {
        margin: 3mm 0 0 0;
        padding: 0 0 2mm 0;
        border-bottom: 1px solid #000;
        /*margin-top: 5px;*/
    }

    .grower {
        margin: auto 0;
    }

    img {
        display: block;
        margin: auto auto 0 auto;
        width: 100px;
    }
    
    """,
    font_config=font_config,
)

with open("data/products/products.json", "r") as file:
    products = json.load(file)


def generate(widget, order):
    def add_text(key):
        try:
            with open(f"data/letter/{key}.html", "r") as file:
                return file.read()
        except FileNotFoundError:
            print(key + ": No text available")
            return ""


    ### Check if repeat customer
    with open("data/orders.json", "r") as file:
        orders = json.loads(file.read())
        
        repeat_customer = False
        for item in orders:
            if (
                item["billing"]["email"] == order["billing"]["email"] 
                and
                item["number"] != order["number"]
                ):

                repeat_customer = True
                break

    ### Product Query
    items = [products["id"][str(item["product_id"])] for item in order["line_items"]]
    item_categories = set([item["categories"][0]["slug"] for item in items])
    item_skus = [item["sku"] for item in items]

    ### Heading
    if len(order["shipping"]["first_name"]) > 0:
        first_name = order["shipping"]["first_name"]
    else:
        first_name = order["billing"]["first_name"]

    first_name = first_name.split()[0]
    first_name = first_name.capitalize() if not first_name[0].isupper() else first_name
    first_name = first_name.capitalize() if first_name[1].isupper() else first_name
    print(first_name)

    if len(first_name) > 0:
        main_text = "<h4>Hi " + first_name + ",</h4>"
    else:
        main_text = "<h4>Hi,</h4>"

    if repeat_customer == False:
        main_text += "<p>first off, thanks for your order!</p>"
    elif repeat_customer == True:
        main_text += "<p>thanks for ordering once again from our shop!</p>"

    ### Main text
    text_count = 0

    if "koji" in item_categories:
        main_text += add_text("koji")
        text_count += 1
    if "tempeh" in item_categories:
        main_text += add_text("tempeh")
        text_count += 1
    if "natto" in item_categories:
        if "koji" in item_categories:
            main_text += add_text("natto")
        else:
            main_text += add_text("natto_only")
        text_count += 1
    if "kojireis" in item_skus:
        main_text += add_text("dried_koji")
        text_count += 1
    if "kansui" in item_skus:
        main_text += add_text("kansui")
        text_count += 1
    if "mohnmiso" in item_skus:
        if text_count > 1:
            main_text += "<section><p>And by the way, that "
        else:
            main_text += "<section><p>The "
        main_text += add_text("mohnmiso")

    if main_text == "":
        print("Was hat der bitte bestellt")

    ### Regards
    if set(["koji", "tempeh", "natto"]) & item_categories:
        main_text += add_text("wish")
    main_text += add_text("regards")
    main_text += add_text("logo")
    main_text += add_text("ps")

    # Adjust page margin, depending on number of texts
    if text_count <= 3:
        style = """
            <style>
                @page { 
                    margin: 12mm; 
                }
                h4 {
                    margin-bottom: 4mm;
                    }
            </style>"""
    else:
        style = ""

    if text_count > 0:
        html = ("<html><body>"
                + style
                + main_text 
                + "</body></html>")

        doc = HTML(string=html, base_url=".")

        file = "temp/letter_insert.pdf"
        doc.write_pdf(
            file, stylesheets=[sourceCSS], font_config=font_config
        )

        # webbrowser.open_new_tab(file)

        conn.printFile(
            settings.printers["A4"], 
            file, 
            "Briefbeilage - {}".format(
                order["shipping"]["last_name"]
                ),
            {}
            )
    else:
        print("Nothing to print")
        # messagedialog = Gtk.MessageDialog(parent=widget.get_toplevel(),
        #                                   flags=Gtk.DialogFlags.MODAL,
        #                                   type=Gtk.MessageType.WARNING,
        #                                   buttons=Gtk.ButtonsType.OK_CANCEL,
        #                                   message_format="There is nothing to print.")
        # messagedialog.show_all()


if __name__ == "__main__":

    order = {
        "id": 35404,
        "parent_id": 0,
        "number": "2109",
        "order_key": "wc_order_c4LMT0p3NlK51",
        "created_via": "checkout",
        "version": "3.8.1",
        "status": "processing",
        "currency": "EUR",
        "date_created": "2020-02-08T19:15:12",
        "date_created_gmt": "2020-02-08T17:15:12",
        "date_modified": "2020-02-08T19:15:17",
        "date_modified_gmt": "2020-02-08T17:15:17",
        "discount_total": "0.00",
        "discount_tax": "0.00",
        "shipping_total": "10.91",
        "shipping_tax": "1.09",
        "cart_tax": "8.34",
        "total": "103.75",
        "total_tax": "9.43",
        "prices_include_tax": True,
        "customer_id": 641,
        "customer_ip_address": "31.27.102.132",
        "customer_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36",
        "customer_note": "",
        "billing": {
            "first_name": "Marco",
            "last_name": "Visciola",
            "company": "",
            "address_1": "CALATA CATTANEO 15",
            "address_2": "Porto antico Eataly Genova (GE)",
            "city": "GENOVA",
            "state": "GE",
            "postcode": "16128",
            "country": "IT",
            "email": "m.visciola@eataly.it",
            "phone": "",
        },
        "shipping": {
            "first_name": "Marco",
            "last_name": "Visciola",
            "company": "",
            "address_1": "CALATA CATTANEO 15",
            "address_2": "Porto antico Eataly Genova (GE)",
            "city": "GENOVA",
            "state": "GE",
            "postcode": "16128",
            "country": "IT",
        },
        "payment_method": "stripe",
        "payment_method_title": "Credit Card",
        "transaction_id": "ch_1G9wtjLnbaZTAM3ZyHzvBQiU",
        "date_paid": "2020-02-08T19:15:17",
        "date_paid_gmt": "2020-02-08T17:15:17",
        "date_completed": None,
        "date_completed_gmt": None,
        "cart_hash": "1488b851f0b11c194553a13ce02d92f5",
        "meta_data": [
        ],
        "line_items": [
            {
                "id": 9674,
                "name": "White Koji Spores",
                "product_id": 532,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "5.45",
                "subtotal_tax": "0.55",
                "total": "5.45",
                "total_tax": "0.55",
                "taxes": [{"id": 29, "total": "0.545455", "subtotal": "0.545455"}],
                "meta_data": [],
                "sku": "",
                "price": 5.454545,
            },
            {
                "id": 9675,
                "name": "A. Luchuensis Spores",
                "product_id": 1136,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "8.64",
                "subtotal_tax": "0.86",
                "total": "8.64",
                "total_tax": "0.86",
                "taxes": [{"id": 29, "total": "0.863636", "subtotal": "0.863636"}],
                "meta_data": [],
                "sku": "",
                "price": 8.636364,
            },
            {
                "id": 9676,
                "name": "Aspergillus Sojae Spores",
                "product_id": 63,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "5.45",
                "subtotal_tax": "0.55",
                "total": "5.45",
                "total_tax": "0.55",
                "taxes": [{"id": 29, "total": "0.545455", "subtotal": "0.545455"}],
                "meta_data": [],
                "sku": "",
                "price": 5.454545,
            },
            {
                "id": 9677,
                "name": "Organic Dried Koji Rice",
                "product_id": 4861,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "12.50",
                "subtotal_tax": "1.25",
                "total": "12.50",
                "total_tax": "1.25",
                "taxes": [{"id": 29, "total": "1.25", "subtotal": "1.25"}],
                "meta_data": [{"id": 76487, "key": "_reduced_stock", "value": "1"}],
                "sku": "kojireis",
                "price": 12.5,
            },
            {
                "id": 9678,
                "name": "Pumpkinseed Miso (organic)",
                "product_id": 27842,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "8.73",
                "subtotal_tax": "0.87",
                "total": "8.73",
                "total_tax": "0.87",
                "taxes": [{"id": 29, "total": "0.872727", "subtotal": "0.872727"}],
                "meta_data": [{"id": 76488, "key": "_reduced_stock", "value": "1"}],
                "sku": "kkmiso",
                "price": 8.727273,
            },
            {
                "id": 9679,
                "name": "Poppyseed Miso",
                "product_id": 25509,
                "variation_id": 0,
                "quantity": 2,
                "tax_class": "reduced-rate",
                "subtotal": "18.00",
                "subtotal_tax": "1.80",
                "total": "18.00",
                "total_tax": "1.80",
                "taxes": [{"id": 29, "total": "1.8", "subtotal": "1.8"}],
                "meta_data": [{"id": 76489, "key": "_reduced_stock", "value": "2"}],
                "sku": "mohnmiso",
                "price": 9,
            },
            {
                "id": 9680,
                "name": "Cashew Miso (organic)",
                "product_id": 25533,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "12.00",
                "subtotal_tax": "1.20",
                "total": "12.00",
                "total_tax": "1.20",
                "taxes": [{"id": 29, "total": "1.2", "subtotal": "1.2"}],
                "meta_data": [{"id": 76490, "key": "_reduced_stock", "value": "1"}],
                "sku": "cashewmiso",
                "price": 12,
            },
            {
                "id": 9681,
                "name": "Pumpkinseed Shoyu",
                "product_id": 26402,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "12.64",
                "subtotal_tax": "1.26",
                "total": "12.64",
                "total_tax": "1.26",
                "taxes": [{"id": 29, "total": "1.263636", "subtotal": "1.263636"}],
                "meta_data": [{"id": 76491, "key": "_reduced_stock", "value": "1"}],
                "sku": "kkshoyu",
                "price": 12.636364,
            },
        ],
        "tax_lines": [
            {
                "id": 9683,
                "rate_code": "10% VAT-1",
                "rate_id": 29,
                "label": "10% VAT",
                "compound": False,
                "tax_total": "8.34",
                "shipping_tax_total": "1.09",
                "rate_percent": 10,
                "meta_data": [],
            }
        ],
        "shipping_lines": [
            {
                "id": 9682,
                "method_title": "Priority",
                "method_id": "flat_rate",
                "instance_id": "11",
                "total": "10.91",
                "total_tax": "1.09",
                "taxes": [{"id": 29, "total": "1.091", "subtotal": ""}],
                "meta_data": [
                    {
                        "id": 76480,
                        "key": "Items",
                        "value": "White Koji Spores &times; 1, A. Luchuensis Spores &times; 1, Aspergillus Sojae Spores &times; 1, Organic Dried Koji Rice &times; 1, Pumpkinseed Miso (organic) &times; 1, Poppyseed Miso &times; 2, Cashew Miso (organic) &times; 1, Pumpkinseed Shoyu &times; 1",
                    }
                ],
            }
        ],
        "fee_lines": [],
        "coupon_lines": [],
        "refunds": [],
        "currency_symbol": "\u20ac",
        "_links": {
            "self": [
                {
                    "href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders/35404"
                }
            ],
            "collection": [
                {"href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders"}
            ],
            "customer": [
                {
                    "href": "https://www.fermentationculture.eu/wp-json/wc/v3/customers/641"
                }
            ],
        },
        "website": "FC",
    }
    """
    order = {
        "id": 40527,
        "parent_id": 0,
        "number": "2502",
        "order_key": "wc_order_5Pou5mZi6Rq7z",
        "created_via": "checkout",
        "version": "3.8.1",
        "status": "processing",
        "currency": "EUR",
        "date_created": "2020-04-06T16:19:56",
        "date_created_gmt": "2020-04-06T14:19:56",
        "date_modified": "2020-04-06T16:20:03",
        "date_modified_gmt": "2020-04-06T14:20:03",
        "discount_total": "0.00",
        "discount_tax": "0.00",
        "shipping_total": "10.91",
        "shipping_tax": "0.00",
        "cart_tax": "0.00",
        "total": "42.95",
        "total_tax": "0.00",
        "prices_include_tax": True,
        "customer_id": 802,
        "customer_ip_address": "85.246.80.161",
        "customer_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Safari/605.1.15",
        "customer_note": "",
        "billing": {
            "first_name": "Paula",
            "last_name": "Castro",
            "company": "Kyo Lda",
            "address_1": "Rua do Douro",
            "address_2": "92 Rebelva",
            "city": "S\u00e3o Domingos de Rana",
            "state": "",
            "postcode": "2785-806",
            "country": "PT",
            "email": "kyo@kyo.pt",
            "phone": "",
        },
        "shipping": {
            "first_name": "Paula",
            "last_name": "Castro",
            "company": "Kyo Lda",
            "address_1": "Rua do Douro",
            "address_2": "92 Rebelva",
            "city": "S\u00e3o Domingos de Rana",
            "state": "",
            "postcode": "2785-806",
            "country": "PT",
        },
        "payment_method": "stripe",
        "payment_method_title": "Credit Card",
        "transaction_id": "ch_1GUvnxLnbaZTAM3ZwVZtho9m",
        "date_paid": "2020-04-06T16:20:03",
        "date_paid_gmt": "2020-04-06T14:20:03",
        "date_completed": None,
        "date_completed_gmt": None,
        "cart_hash": "8fe43caa94eee36cbc4fd669c8f6d4a7",
        "meta_data": [
            {"id": 279937, "key": "_order_number", "value": "2502"},
            {
                "id": 279974,
                "key": "_billing_business_consumer_selector",
                "value": "business",
            },
            {"id": 279975, "key": "_billing_eu_vat", "value": "PT501948279"},
            {"id": 279976, "key": "_billing_it_sid_pec", "value": ""},
            {"id": 279977, "key": "is_vat_exempt", "value": "yes"},
            {"id": 279978, "key": "_tracking", "value": "NO"},
            {"id": 279979, "key": "ss_wc_mailchimp_opt_in", "value": "no"},
            {"id": 279980, "key": "terms", "value": "on"},
            {"id": 279983, "key": "_stripe_customer_id", "value": "cus_H31ru8VaVrF9K1"},
            {
                "id": 279984,
                "key": "_stripe_source_id",
                "value": "src_1GUvnqLnbaZTAM3Z9TT5AaxD",
            },
            {
                "id": 279985,
                "key": "_stripe_intent_id",
                "value": "pi_1GUvnwLnbaZTAM3Z9AEaVGBv",
            },
            {"id": 279986, "key": "_stripe_charge_captured", "value": "yes"},
            {"id": 279987, "key": "_stripe_fee", "value": "0.85"},
            {"id": 279988, "key": "_stripe_net", "value": "42.1"},
            {"id": 279989, "key": "_stripe_currency", "value": "EUR"},
            {
                "id": 280053,
                "key": "_bewpi_invoice_date",
                "value": "2020-04-06 16:20:05",
            },
            {"id": 280054, "key": "_bewpi_invoice_number", "value": "627"},
            {
                "id": 280055,
                "key": "_bewpi_invoice_pdf_path",
                "value": "2020/FC-2020-0627.pdf",
            },
            {"id": 280057, "key": "bewpi_pdf_invoice_sent", "value": "1"},
            {
                "id": 282759,
                "key": "order_notes",
                "value": "Senden, sobald es wieder m\u00f6glich ist",
            },
            {
                "key": "order_notes",
                "value": "Senden, sobald es wieder m\u00f6glich ist",
            },
            {"key": "order_notes", "value": "canceln"},
            {
                "key": "order_notes",
                "value": "Senden, sobald es wieder m\u00f6glich ist",
            },
        ],
        "line_items": [
            {
                "id": 11616,
                "name": "White Koji Spores",
                "product_id": 532,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "5.45",
                "subtotal_tax": "0.00",
                "total": "5.45",
                "total_tax": "0.00",
                "taxes": [],
                "meta_data": [],
                "sku": "",
                "price": 5.45,
            },
            {
                "id": 11617,
                "name": "Tempeh Spores - 10 g",
                "product_id": 598,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "8.18",
                "subtotal_tax": "0.00",
                "total": "8.18",
                "total_tax": "0.00",
                "taxes": [],
                "meta_data": [],
                "sku": "",
                "price": 8.18,
            },
            {
                "id": 11618,
                "name": "Organic Dried Koji Rice - 500 g",
                "product_id": 4861,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "12.50",
                "subtotal_tax": "0.00",
                "total": "12.50",
                "total_tax": "0.00",
                "taxes": [],
                "meta_data": [{"id": 91197, "key": "_reduced_stock", "value": "1"}],
                "sku": "kojireis",
                "price": 12.5,
            },
            {
                "id": 11619,
                "name": "Natto spores",
                "product_id": 32110,
                "variation_id": 0,
                "quantity": 1,
                "tax_class": "reduced-rate",
                "subtotal": "5.91",
                "subtotal_tax": "0.00",
                "total": "5.91",
                "total_tax": "0.00",
                "taxes": [],
                "meta_data": [],
                "sku": "",
                "price": 5.91,
            },
        ],
        "tax_lines": [],
        "shipping_lines": [
            {
                "id": 11620,
                "method_title": "Priority",
                "method_id": "flat_rate",
                "instance_id": "11",
                "total": "10.91",
                "total_tax": "0.00",
                "taxes": [],
                "meta_data": [
                    {
                        "id": 91167,
                        "key": "Items",
                        "value": "White Koji Spores &times; 1, Tempeh Spores - 10 g &times; 1, Organic Dried Koji Rice - 500 g &times; 1, Natto spores &times; 1",
                    }
                ],
            }
        ],
        "fee_lines": [],
        "coupon_lines": [],
        "refunds": [],
        "currency_symbol": "\u20ac",
        "_links": {
            "self": [
                {
                    "href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders/40527"
                }
            ],
            "collection": [
                {"href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders"}
            ],
            "customer": [
                {
                    "href": "https://www.fermentationculture.eu/wp-json/wc/v3/customers/802"
                }
            ],
        },
        "website": "https://www.fermentationculture.eu",
    }"""
    generate("??", order)
    file = os.path.abspath("temp/letter_insert.pdf")
    webbrowser.open_new_tab(file)
