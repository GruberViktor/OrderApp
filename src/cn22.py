from datetime import date
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
from decimal import Decimal as d
import os
import json
import cups

import settings


font_config = FontConfiguration()


sourceCSS = CSS(string="""
    @page { size: 74mm 105mm; margin: 0 0 0 0; } 
    * {
        box-sizing: border-box;
    }
    html {
        font-family: Verdana;
        font-size: 2.4mm;
        }

    body {
        margin: 0;
    }
    
    .page {
        padding: 0mm;
        width: 70mm;
        height: 101mm;
        page-break-after: always; 
        margin: auto;
    }

    p {
        margin: 1mm 0mm;
    }

    .hline {
        position: relative;
        left: -5mm;
        height: 1px;
        width: 120%;
        background: black;
        margin: 0mm auto;
    }

    .tablewrap {
        width: 74mm;
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
    }

    .tablewrap .tablecell:nth-child(-n + 2) {
        border-right: 1px solid black;
    }

    .tablecell {
        padding: 0.5mm;
    }
    .tablecell p {
        margin: 0 0 1mm 0!important;
    }

    .quantity, .hstariff {
        width: 40mm;
    }

    .netweight, .totalweight {
        width: 16mm;
    }

    .value, .totalvalue {
        width: 10mm;
    }

    .cn_ueberschrift {
        font-size: 1.4rem;
        font-weight: 700;
        padding: 0.2rem;
        background: black;
        color: white;
        margin-top: 2mm;
    }

    .erklaerung {
        margin: 2mm 0mm;
    }

    .datumunterschrift {
        line-height: 4rem;
    }

    
    """, font_config=font_config)


def generate(widget, order):
    with open("data/products/products.json", "r") as file:
        products = json.load(file)

    quant_desc = ""
    netweight = ""
    value = ""
    total_weight = d(0)
    total_value = d(0)

    for i in range(len(order["line_items"])):
        # initial definitions
        order_item = order["line_items"][i]
        product_item = products["id"][str(order["line_items"][i]["product_id"])]
        
        # quantity
        quant_desc += "{quantity}x {name} <br>".format(
            quantity = str(order_item["quantity"]),
            name = order_item["name"]
        )

        if len(product_item["variations"]) == 0:
            try:
                weight = d(product_item["weight"]) * d(order_item["quantity"])
            except:
                weight = 0
                print(product_item["name"] + " has no weight")
            value_d = d(order_item["total"])
        else: 
            var_id = str(order_item["variation_id"])
            weight = d(product_item["variations"][var_id]["weight"]) * d(order_item["quantity"])
            value_d = d(order_item["total"])  
        
        netweight += str(weight) + " g<br>"

        # Value
        
        value += str(value_d) + "€<br>"

        # Totals addition
        total_value += value_d
        total_weight += weight

    hsnumber_country = "30029050 - JAPAN"
    totalweight = str(total_weight / 1000)
    totalvalue = str(total_value) + "€"
    
    today = date.today()
    form_date = "{d}.{m}.{y}".format(
        d = today.day,
        m = today.month,
        y = today.year
    )
     
    with open("data/other_labels/CN22.html", "r") as f:
        html = f.read().format(
        quant_desc = quant_desc,
        netweight = netweight,
        value = value,
        hsnumber_country = hsnumber_country,
        totalweight = totalweight,
        totalvalue = totalvalue,
        form_date = form_date
        )


    doc = HTML(string=html, base_url=".")

    doc.write_pdf('temp/CN22.pdf', 
    stylesheets=[sourceCSS], 
    font_config=font_config)

    if __name__ == "cn22":
        conn = cups.Connection()
        file = os.path.abspath("temp/CN22.pdf")
        conn.printFile(settings.printers["labels_groß"], file, "CN22 - Order{}".format(order["number"]), {"media": "74mmx105mm"})





if __name__ == "__main__":

    order = {'id': 34621, 'parent_id': 0, 'number': '2057', 'order_key': 'wc_order_ICvKsiKmfx4yV', 'created_via': 'checkout', 'version': '3.8.1', 'status': 'completed', 'currency': 'EUR', 'date_created': '2020-01-30T16:37:51', 'date_created_gmt': '2020-01-30T14:37:51', 'date_modified': '2020-01-31T14:04:30', 'date_modified_gmt': '2020-01-31T12:04:30', 'discount_total': '0.00', 'discount_tax': '0.00', 'shipping_total': '0.00', 'shipping_tax': '0.00', 'cart_tax': '0.00', 'total': '10.91', 'total_tax': '0.00', 'prices_include_tax': True, 'customer_id': 0, 'customer_ip_address': '194.244.26.116', 'customer_user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36', 'customer_note': '', 'billing': {'first_name': 'Ristorante', 'last_name': 'Tokuyoshi', 'company': 'Tokuysohi S.r.l', 'address_1': 'Via Sapeto 1', 'address_2': '', 'city': 'Milano', 'state': 'MI', 'postcode': '20123', 'country': 'IT', 'email': 'info@ristorantetokuyoshi.com', 'phone': ''}, 'shipping': {'first_name': 'Ristorante', 'last_name': 'Tokuyoshi', 'company': 'Tokuysohi S.r.l', 'address_1': 'Via Sapeto 1', 'address_2': '', 'city': 'Milano', 'state': 'MI', 'postcode': '20123', 'country': 'IT'}, 'payment_method': 'stripe', 'payment_method_title': 'Credit Card', 'transaction_id': 'ch_1G6e9WLnbaZTAM3Z8mp2Cguh', 'date_paid': '2020-01-30T16:37:56', 'date_paid_gmt': '2020-01-30T14:37:56', 'date_completed': '2020-01-31T14:04:30', 'date_completed_gmt': '2020-01-31T12:04:30', 'cart_hash': 'd21daf2572e578b19a656ea706362d36', 'meta_data': [{'id': 229913, 'key': '_order_number', 'value': '2057'}, {'id': 229950, 'key': '_billing_business_consumer_selector', 'value': 'business'}, {'id': 229951, 'key': '_billing_eu_vat', 'value': '09729740960'}, {'id': 229952, 'key': '_billing_it_sid_pec', 'value': ''}, {'id': 229953, 'key': 'is_vat_exempt', 'value': 'yes'}, {'id': 229954, 'key': '_tracking', 'value': 'NO'}, {'id': 229955, 'key': 'ss_wc_mailchimp_opt_in', 'value': 'no'}, {'id': 229958, 'key': '_stripe_customer_id', 'value': 'cus_Gdw1re7LrBgY3i'}, {'id': 229959, 'key': '_stripe_source_id', 'value': 'src_1G6e9SLnbaZTAM3ZL1Hgf8WP'}, {'id': 229960, 'key': '_stripe_intent_id', 'value': 'pi_1G6e9VLnbaZTAM3ZfdC5cxIZ'}, {'id': 229961, 'key': '_stripe_charge_captured', 'value': 'yes'}, {'id': 229962, 'key': '_stripe_fee', 'value': '0.4'}, {'id': 229963, 'key': '_stripe_net', 'value': '10.51'}, {'id': 229964, 'key': '_stripe_currency', 'value': 'EUR'}, {'id': 229982, 'key': '_bewpi_invoice_date', 'value': '2020-01-30 16:37:57'}, {'id': 229983, 'key': '_bewpi_invoice_number', 'value': '182'}, {'id': 229984, 'key': '_bewpi_invoice_pdf_path', 'value': '2020/FC-2020-0182.pdf'}, {'id': 229985, 'key': 'bewpi_pdf_invoice_sent', 'value': '1'}], 'line_items': [{'id': 9402, 'name': 'Barley Koji Spores', 'product_id': 61, 'variation_id': 0, 'quantity': 2, 'tax_class': 'reduced-rate', 'subtotal': '10.91', 'subtotal_tax': '0.00', 'total': '10.91', 'total_tax': '0.00', 'taxes': [], 'meta_data': [], 'sku': '', 'price': 5.455}], 'tax_lines': [], 'shipping_lines': [{'id': 9403, 'method_title': 'Free Shipping', 'method_id': 'advanced_free_shipping', 'instance_id': '0', 'total': '0.00', 'total_tax': '0.00', 'taxes': [], 'meta_data': []}], 'fee_lines': [], 'coupon_lines': [], 'refunds': [], 'currency_symbol': '€', '_links': {'self': [{'href': 'https://www.fermentationculture.eu/wp-json/wc/v3/orders/34621'}], 'collection': [{'href': 'https://www.fermentationculture.eu/wp-json/wc/v3/orders'}]}, 'website': 'FC'}
    if os.path.exists("data/products/products.json"):
            file = open("data/products/products.json", "r")
            products = json.load(file)
    generate("??", order)
