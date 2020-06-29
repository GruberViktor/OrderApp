import cups
import pycountry
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
from PyPDF2 import PdfFileReader
import os
import webbrowser

import __main__ as m
import settings

conn = cups.Connection()
font_config = FontConfiguration()

country_lang = {
    "DE": "de",
    "CH": "de",
    "AT": "de",
    "BG": "bg",
    "CZ": "cs",
    "DK": "da",
    "EE": "et",
    "FI": "fi",
    "FR": "fr",
    "GR": "el",
    "HR": "hr",
    "HU": "hu",
    "IS": "is",
    "IT": "it",
    "LV": "lv",
    "LT": "lt",
    "NL": "nl",
    "NO": "no",
    "PL": "pl",
    "PT": "pt",
    "RO": "ro",
    "ES": "es",
    "SK": "sk",
    "SL": "sl",
    "SE": "sv",
    "GB": "en",
    "UK": "en",
    "IR": "en",
    "MT": "en",
    "BE": "nl",
    "IE": "en",
    "LU": "fr",
    "AU": "en",
    "US": "en",
    "CA": "en",
    "IL": "he"
    }

def print_productlabels(widget, order):
    for i in range(len(order["line_items"])):
        product = order["line_items"][i]
        if not product["sku"] == "":
            print_label_on_BP730(
                "widget", 
                product["sku"], 
                product["quantity"],
                country_lang[order["shipping"]["country"]]
                )


def print_label_on_BP730(widget, sku, quantity, lang):
    if lang is False:
        parent = widget.get_toplevel()
        lang = parent.lang_selection_combobox.get_active_id()

    file = "data/products/labels/{}/{}.pdf".format(sku, lang)
    if os.path.exists(file):
        input1 = PdfFileReader(open(file, 'rb'))
        page = input1.getPage(0)
        width_pt = page.trimBox.getWidth()
        height_pt = page.trimBox.getHeight()
        width_mm = int(round(float(width_pt) / 2.835, 0))
        height_mm = int(round(float(height_pt) / 2.835, 0))
        
        for i in range(quantity):
            if sku == "kansui":
                conn.printFile(
                settings.printers["labels_groß"], 
                "data/products/labels/kansuiwarning/{}.pdf".format(lang), 
                "data/products/labels/kansuiwarning/{}.pdf".format(lang), 
                {"media": "{0}x{1}mm".format(height_mm, width_mm),
                "media-bottom-margin": "0"}
                )
            conn.printFile(
                settings.printers["labels_groß"], 
                file, 
                file, 
                {"media": "{0}x{1}mm".format(height_mm, width_mm),
                "media-bottom-margin": "0"}
            )
        print("Printing ", quantity, " copies of ", file)
    else:
        m.errorwindow("{} does not exist".format(file))


class print_addresslabels():
    def __init__(self, widget, order):
        if order == None:
            orders = m.mainwindow.toggled_orders
            if len(orders) > 0:
                self.make_address_label_pdf(orders)
        elif type(order) == dict:
            orders = [order]
            self.make_address_label_pdf(orders)
        else:
            print("No orders selected")

    def make_address_label_pdf(self, orders):
        label = "<html><body>"
        for i in range(len(orders)):

            # Tracking Query
            tracking_val = "No"
            for item in orders[i]["meta_data"]:
                if item["key"] == "_tracking":
                    tracking_val = item["value"]
                    break
            if orders[i]["shipping"]["country"] in ["US", "AU", "CA", "IL"]:
                tracking_val = "yes"

            state = pycountry.countries.get(
                alpha_2=orders[i]["shipping"]["country"])

            if tracking_val.lower() == "yes":
                label += """<div class="page"><div class="addresslabel" style="border-bottom: 1px solid black">"""
            else:
                label += """<div class="page"><div class="addresslabel">"""
            label += """
                    {company} 
                    {first_name} {last_name}<br>
                    {address_1} 
                    {address_2} <br>
                    {postcode} {city}<br>
                    {state}</div></div>""".format(
                        company    = "" if orders[i]["shipping"]["company"] == "" else orders[i]["shipping"]["company"] + "<br>",
                        first_name = orders[i]["shipping"]["first_name"],
                        last_name  = orders[i]["shipping"]["last_name"],
                        address_1  = orders[i]["shipping"]["address_1"],
                        address_2  = "" if orders[i]["shipping"]["address_2"] == "" else "<br>" + orders[i]["shipping"]["address_2"],
                        postcode   = orders[i]["shipping"]["postcode"],
                        city       = orders[i]["shipping"]["city"],
                        state      = state.name.upper()
                    )
        label += "</body></html>"

        width = "62"
        height = "40"

        sourceCSS = CSS(string="""
                                @page { size: %smm %smm; margin: 0 0 0 0; } 
                                body {
                                    font-family: Verdana;
                                    font-size: 14px;
                                    }
                                .addresslabel {
                                    position: relative;
                                    top: 50%%;
                                    transform: translateY(-50%%);
                                    }
                                .page {
                                    padding: 0mm;
                                    width: %smm;
                                    height: %smm;
                                    page-break-after: always; 
                            
                                }
                                """ % (width, height, str(int(width) - 2), height), font_config=font_config)
        doc = HTML(string=label, base_url=".")

        doc.write_pdf('temp/addresslabel.pdf', 
                        stylesheets=[sourceCSS], 
                        font_config=font_config)

        pdf = os.path.abspath("temp/addresslabel.pdf")
        
        conn.printFile(settings.printers["labels_klein"], pdf, "Addresslabels", {"media": "{}mmx{}mm".format(width, height)})


def Einkaufsliste():

    def get_products():
        to_get = {}

        for i in range(len(m.filtered_orders)):
            productsnum = len(m.filtered_orders[i]["line_items"])
            
            for k in range(0, productsnum):
                produktliste = m.filtered_orders[i].get("line_items", {})
                sku = produktliste[k]["sku"]
                name = produktliste[k]["name"]

                if not to_get.get(name, {}):
                    to_get[name] = produktliste[k].get("quantity")

                else:
                    to_get[name] += produktliste[k].get("quantity")

        for key in to_get:

            if key == "":
                to_get["Sporen"] = to_get[key]
                to_get.pop(key)

        return to_get

    def print_einkaufsliste(liste):

        einkaufsliste = ""
        for key in liste:
            einkaufsliste += "{0}x {1}<br>".format(liste[key], key)
        to_print = "<html><body>{0}</body></html>".format(einkaufsliste)

        sourceCSS = CSS(string="""
                                @page { size: 62mm 50mm; margin: 1mm 1mm 1mm 1mm; } 
                                body {
                                    font-family: Verdana;
                                    font-size: 10px;
                                    }
                                """, font_config=font_config)
        doc = HTML(string=to_print, base_url=".")

        doc.write_pdf('temp/einkaufsliste.pdf', 
                stylesheets=[sourceCSS], 
                font_config=font_config)

        pdf = os.path.abspath("temp/einkaufsliste.pdf")
        
        conn.printFile(settings.printers["labels_klein"], pdf, "Einkaufsliste", {"media": "62mmx70mm"})


    liste = get_products()
    print_einkaufsliste(liste)


def print_invoice(widget, order, _print):
    path = None
    
    for i in range(len(order["meta_data"])):
        if order["meta_data"][i]["key"] == "_bewpi_invoice_pdf_path":
            path = order["meta_data"][i]["value"]
            break
    
    if path is None:
        print("No Invoice available")
        webbrowser.open_new_tab(order["website"] + "/wp-admin/post.php?post={}&action=edit"
                        .format(order["id"]))
        return
    
    if order["website"] == "https://www.fermentationculture.eu":
        os.system(f"scp viktor@152.89.105.224:/var/www/fermentationculture.eu/public_html/wp-content/uploads/woocommerce-pdf-invoices/attachments/{path} temp/")
        file = os.path.abspath(f"temp/{path[5:]}")
    elif order["website"] == "https://www.luvifermente.eu":
        os.system(f"scp viktor@152.89.105.224:/var/www/luvifermente.eu/public_html/wp-content/uploads/woocommerce-pdf-invoices/attachments/{path} temp/")
        file = os.path.abspath(f"temp/{path[5:]}")

    if _print is False:
        webbrowser.open_new_tab(file)
        return
    
    conn.printFile(
        settings.printers["A4"], 
        file, 
        "Invoice - {}".format(
            order["shipping"]["last_name"]
            ),
        {}
            )


def print_sender():
    width = "62"
    height = "30"
    if not os.path.exists("temp/sender_label.pdf"):
        label = "<html><body>"
    
        label += """
                fermentationculture.eu / <br>
                LUVI Fermente KG <br>
                Gallabergerstrasse 28 <br>
                4860 Lenzing <br>
                AUSTRIA</div></div>"""
        label += "</body></html>"

        

        sourceCSS = CSS(string="""
                                @page { size: %smm %smm; margin: 0 0 0 0; } 
                                body {
                                    font-family: Verdana;
                                    font-size: 14px;
                                    }
                                .addresslabel {
                                    position: relative;
                                    top: 50%%;
                                    transform: translateY(-50%%);
                                    }
                                .page {
                                    padding: 0mm;
                                    width: %smm;
                                    height: %smm;
                                    page-break-after: always; 
                            
                                }
                                """ % (width, height, str(int(width) - 2), height), font_config=font_config)
        doc = HTML(string=label, base_url=".")

        doc.write_pdf("temp/sender_label.pdf", 
                        stylesheets=[sourceCSS], 
                        font_config=font_config)

    pdf = os.path.abspath("temp/sender_label.pdf")
    
    conn.printFile(settings.printers["labels_klein"], pdf, "Addresslabels", {"media": "{}mmx{}mm".format(width, height)})



def print_a4(widget, file):
    try:
        conn.printFile(settings.printers["A4"], file, file, {})
    except cups.IPPError:
        print("File does not exist")