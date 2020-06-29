from datetime import date
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
from decimal import Decimal as d
import os
import json
import cups
from jinja2 import Template
import pycountry

import settings
import helper_funcs


font_config = FontConfiguration()


with open("data/other_labels/CN23.css", "r") as file:
    sourceCSS = CSS(
    string=file.read(),
    font_config=font_config,
    )

with open("data/other_labels/CN23.html", "r") as file:
    template = Template(file.read())

with open("data/products/products.json", "r") as file:
    products = json.load(file)


def generate(widget, order):
    items = ""
    total_gross_weight = d(0.0215) 
    total_net_weight = d(0.0)
    total_value = d(0)

    for i in range(len(order["line_items"])):
        # initial definitions
        order_item = order["line_items"][i]
        product_item = products["id"][str(order_item["product_id"])]

        # quantity
        quantity = str(order_item["quantity"])
        name = order_item["name"]
        

        if len(product_item["variations"]) == 0:
            weight = d(product_item["weight"]) * d(order_item["quantity"]) / 1000 
            value_d = d(order_item["total"])
        else: 
            var_id = str(order_item["variation_id"])
            weight = d(product_item["variations"][var_id]["weight"]) * d(order_item["quantity"]) / 1000
            value_d = d(order_item["total"])  

        origin = ""
        hsnumber = ""

        if product_item["categories"][0]["slug"] == "koji":
            hsnumber = "30029050"
            origin = "Japan"
        else:
            for j in range(len(product_item["attributes"])):
                if product_item["attributes"][j]["name"] == "origin":
                    origin = product_item["attributes"][j]["options"][0]
                elif product_item["attributes"][j]["name"] == "hsnumber":
                    hsnumber = product_item["attributes"][j]["options"][0]

        items += """
            <tr>
                <td></td>
                <td>{itemname}</td>
                <td>{quantity}</td>
                <td>{netweight}</td>
                <td>{value}</td>
                <td>{hsnumber}</td>
                <td>{origin}</td>
            </tr>""".format(
                itemname = name + " ",
                quantity = quantity,
                netweight = weight,
                value = str(value_d) + "€",
                hsnumber = hsnumber,
                origin = origin
            )
        
        # Totals addition
        total_value += value_d
        total_gross_weight += weight + d(0.82) / 1000
        total_net_weight += weight
    
    only_starters = helper_funcs.order_contains_only_spores(order)
    if only_starters == True:
        total_gross_weight = str(total_gross_weight.quantize(d("0.001"))) + " kg"
    else:
        total_gross_weight = ""

    total_net_weight = str(total_net_weight.quantize(d("0.001"))) + " kg"
    total_value = str(total_value) + " €"
    today = date.today()
    form_date = "{d}.{m}.{y}".format(
        d = today.day,
        m = today.month,
        y = today.year
    )


    ship = order["shipping"]
    country = pycountry.countries.get(alpha_2=ship["country"])
    
    if only_starters == True:
        doctypes = ["CN23"]
    else:
        doctypes = ["Receipt", "CP71", "CN23"]

    for doctype in doctypes:
        html = template.render(
            name = ship["first_name"] + " " + ship["last_name"],
            company = ship["company"],
            street = ship["address_1"] + "<br>" if ship["address_2"] is not None else "" + ship["address_2"],
            city = ship["city"],
            postcode = ship["postcode"],
            country = country.name,
            telephone = "-" if order["billing"]["phone"] == "" else order["billing"]["phone"],
            email = order["billing"]["email"],
            items = items,
            total_value = total_value,
            total_net_weight = total_net_weight,
            total_gross_weight = total_gross_weight,
            date = form_date,
            type_ = doctype
            )

        doc = HTML(string=html, base_url=".")

        file = f'temp/{doctype}.pdf'
        doc.write_pdf(file, 
            stylesheets=[sourceCSS], 
            font_config=font_config)

        if __name__ == "CN23":
            conn = cups.Connection()
            file = os.path.abspath(file)
            conn.printFile(settings.printers["A4"], 
                file, 
                f"CN23 - {doctype} Order {order['number']}",
                {})



if __name__ == "__main__":

    order = {"id": 35404, "parent_id": 0, "number": "2109", "order_key": "wc_order_c4LMT0p3NlK51", "created_via": "checkout", "version": "3.8.1", "status": "processing", "currency": "EUR", "date_created": "2020-02-08T19:15:12", "date_created_gmt": "2020-02-08T17:15:12", "date_modified": "2020-02-08T19:15:17", "date_modified_gmt": "2020-02-08T17:15:17", "discount_total": "0.00", "discount_tax": "0.00", "shipping_total": "10.91", "shipping_tax": "1.09", "cart_tax": "8.34", "total": "103.75", "total_tax": "9.43", "prices_include_tax": True, "customer_id": 641, "customer_ip_address": "31.27.102.132", "customer_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36", "customer_note": "", "billing": {"first_name": "Marco", "last_name": "Visciola", "company": "", "address_1": "CALATA CATTANEO 15", "address_2": "Porto antico Eataly Genova (GE)", "city": "GENOVA", "state": "GE", "postcode": "16128", "country": "IT", "email": "m.visciola@eataly.it", "phone": ""}, "shipping": {"first_name": "Marco", "last_name": "Visciola", "company": "", "address_1": "CALATA CATTANEO 15", "address_2": "Porto antico Eataly Genova (GE)", "city": "GENOVA", "state": "GE", "postcode": "16128", "country": "IT"}, "payment_method": "stripe", "payment_method_title": "Credit Card", "transaction_id": "ch_1G9wtjLnbaZTAM3ZyHzvBQiU", "date_paid": "2020-02-08T19:15:17", "date_paid_gmt": "2020-02-08T17:15:17", "date_completed": None, "date_completed_gmt": None, "cart_hash": "1488b851f0b11c194553a13ce02d92f5", "meta_data": [{"id": 236063, "key": "_order_number", "value": "2109"}, {"id": 236100, "key": "_billing_business_consumer_selector", "value": "consumer"}, {"id": 236101, "key": "_billing_eu_vat", "value": ""}, {"id": 236102, "key": "_billing_it_sid_pec", "value": ""}, {"id": 236103, "key": "is_vat_exempt", "value": "no"}, {"id": 236104, "key": "_tracking", "value": "NO"}, {"id": 236105, "key": "ss_wc_mailchimp_opt_in", "value": "no"}, {"id": 236106, "key": "terms", "value": "on"}, {"id": 236109, "key": "_stripe_customer_id", "value": "cus_GhLadffJEV9lUT"}, {"id": 236110, "key": "_stripe_source_id", "value": "src_1G9wteLnbaZTAM3ZD0A4BzIx"}, {"id": 236111, "key": "_stripe_intent_id", "value": "pi_1G9wtiLnbaZTAM3Z29JFOs5Z"}, {"id": 236112, "key": "_stripe_charge_captured", "value": "yes"}, {"id": 236113, "key": "_stripe_fee", "value": "1.7"}, {"id": 236114, "key": "_stripe_net", "value": "102.05"}, {"id": 236115, "key": "_stripe_currency", "value": "EUR"}, {"id": 236133, "key": "_bewpi_invoice_date", "value": "2020-02-08 19:15:24"}, {"id": 236134, "key": "_bewpi_invoice_number", "value": "233"}, {"id": 236135, "key": "_bewpi_invoice_pdf_path", "value": "2020/FC-2020-0233.pdf"}, {"id": 236136, "key": "bewpi_pdf_invoice_sent", "value": "1"}], "line_items": [{"id": 9674, "name": "White Koji Spores", "product_id": 532, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "5.45", "subtotal_tax": "0.55", "total": "5.45", "total_tax": "0.55", "taxes": [{"id": 29, "total": "0.545455", "subtotal": "0.545455"}], "meta_data": [], "sku": "", "price": 5.454545}, {"id": 9675, "name": "A. Luchuensis Spores", "product_id": 1136, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "8.64", "subtotal_tax": "0.86", "total": "8.64", "total_tax": "0.86", "taxes": [{"id": 29, "total": "0.863636", "subtotal": "0.863636"}], "meta_data": [], "sku": "", "price": 8.636364}, {"id": 9676, "name": "Aspergillus Sojae Spores", "product_id": 63, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "5.45", "subtotal_tax": "0.55", "total": "5.45", "total_tax": "0.55", "taxes": [{"id": 29, "total": "0.545455", "subtotal": "0.545455"}], "meta_data": [], "sku": "", "price": 5.454545}, {"id": 9677, "name": "Organic Dried Koji Rice", "product_id": 4861, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "12.50", "subtotal_tax": "1.25", "total": "12.50", "total_tax": "1.25", "taxes": [{"id": 29, "total": "1.25", "subtotal": "1.25"}], "meta_data": [{"id": 76487, "key": "_reduced_stock", "value": "1"}], "sku": "kojireis", "price": 12.5}, {"id": 9678, "name": "Pumpkinseed Miso (organic)", "product_id": 27842, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "8.73", "subtotal_tax": "0.87", "total": "8.73", "total_tax": "0.87", "taxes": [{"id": 29, "total": "0.872727", "subtotal": "0.872727"}], "meta_data": [{"id": 76488, "key": "_reduced_stock", "value": "1"}], "sku": "kkmiso", "price": 8.727273}, {"id": 9679, "name": "Poppyseed Miso", "product_id": 25509, "variation_id": 0, "quantity": 2, "tax_class": "reduced-rate", "subtotal": "18.00", "subtotal_tax": "1.80", "total": "18.00", "total_tax": "1.80", "taxes": [{"id": 29, "total": "1.8", "subtotal": "1.8"}], "meta_data": [{"id": 76489, "key": "_reduced_stock", "value": "2"}], "sku": "mohnmiso", "price": 9}, {"id": 9680, "name": "Cashew Miso (organic)", "product_id": 25533, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "12.00", "subtotal_tax": "1.20", "total": "12.00", "total_tax": "1.20", "taxes": [{"id": 29, "total": "1.2", "subtotal": "1.2"}], "meta_data": [{"id": 76490, "key": "_reduced_stock", "value": "1"}], "sku": "cashewmiso", "price": 12}, {"id": 9681, "name": "Pumpkinseed Shoyu", "product_id": 26402, "variation_id": 0, "quantity": 1, "tax_class": "reduced-rate", "subtotal": "12.64", "subtotal_tax": "1.26", "total": "12.64", "total_tax": "1.26", "taxes": [{"id": 29, "total": "1.263636", "subtotal": "1.263636"}], "meta_data": [{"id": 76491, "key": "_reduced_stock", "value": "1"}], "sku": "kkshoyu", "price": 12.636364}], "tax_lines": [{"id": 9683, "rate_code": "10% VAT-1", "rate_id": 29, "label": "10% VAT", "compound": False, "tax_total": "8.34", "shipping_tax_total": "1.09", "rate_percent": 10, "meta_data": []}], "shipping_lines": [{"id": 9682, "method_title": "Priority", "method_id": "flat_rate", "instance_id": "11", "total": "10.91", "total_tax": "1.09", "taxes": [{"id": 29, "total": "1.091", "subtotal": ""}], "meta_data": [{"id": 76480, "key": "Items", "value": "White Koji Spores &times; 1, A. Luchuensis Spores &times; 1, Aspergillus Sojae Spores &times; 1, Organic Dried Koji Rice &times; 1, Pumpkinseed Miso (organic) &times; 1, Poppyseed Miso &times; 2, Cashew Miso (organic) &times; 1, Pumpkinseed Shoyu &times; 1"}]}], "fee_lines": [], "coupon_lines": [], "refunds": [], "currency_symbol": "\u20ac", "_links": {"self": [{"href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders/35404"}], "collection": [{"href": "https://www.fermentationculture.eu/wp-json/wc/v3/orders"}], "customer": [{"href": "https://www.fermentationculture.eu/wp-json/wc/v3/customers/641"}]}, "website": "FC"}    
    if os.path.exists("data/products/products.json"):
            file = open("data/products/products.json", "r")
            products = json.load(file)
    generate("??", order)

