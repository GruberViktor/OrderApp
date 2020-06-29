from zeep import Client
from zeep import xsd
from zeep import helpers
import pprint
import base64
import cups
import webbrowser
from decimal import Decimal as d
from datetime import date
import os

import settings
from settings import credentials
import helper_funcs
import orderfile_handler
import emails
from shops import shops

pretty = pprint.PrettyPrinter(4).pprint
conn = cups.Connection()

### Live or Test ####
post_plc_live = True
#####################

if post_plc_live == True:
    plc = credentials["PLC_Live"]

    api = Client(plc["api"])
    ClientID = plc["ClientID"]
    OrgUnitID = plc["OrgUnitID"]
    OrgUnitGuid = plc["OrgUnitGuid"]

elif post_plc_live == False:
    plc = credentials["PLC_Test"]
    
    api = Client(plc["api"])
    ClientID = plc["ClientID"]
    OrgUnitID = plc["OrgUnitID"]
    OrgUnitGuid = plc["OrgUnitGuid"]

dir_ = "/tmp/post_labels/"
if not os.path.exists(dir_):
    os.makedirs(dir_)


printer_row = [{
    "LanguageID": "PDF",
    "LabelFormatID": "100x150",
    "PaperLayoutID": "2xA5inA4"
    }]

collo_list_template = api.get_element("ns1:ArrayOfColloRow")
collo_article_list_template = api.get_element("ns1:ArrayOfColloArticleRow")
feature_list_template = api.get_element("ns1:ArrayOfAdditionalInformationRow")


def post_shipment(widget, order, parcel_type, instructions, collo_weight, xs, breakable):
    ship = order["shipping"]

    name = ship["first_name"] + " " + ship["last_name"]
    if name == "":
        address_row = [{
            "Name1": ship["company"],
            "AddressLine1": ship["address_1"],
            "AddressLine2": ship["address_2"],
            "PostalCode": ship["postcode"],
            "CountryID": ship["country"],
            "City": ship["city"],
            "Email": order["billing"]["email"],
            "Tel1": order["billing"]["phone"]
            }]
    else: 
        address_row = [{
            "Name1": name,
            "Name2": ship["company"],
            "AddressLine1": ship["address_1"],
            "AddressLine2": ship["address_2"],
            "PostalCode": ship["postcode"],
            "CountryID": ship["country"],
            "City": ship["city"],
            "Email": order["billing"]["email"],
            "Tel1": order["billing"]["phone"]
            }]

    if order["website"] == "https://www.luvifermente.eu":
        sender_row = [{
            "Name1": "LUVI Fermente",
            "AddressLine1": "Gallabergerstrasse 28",
            "PostalCode": "4860",
            "CountryID": "AT",
            "City": "Lenzing",
            "Email": "office@luvifermente.eu",
            "Tel1": "00436801309731"
            }]
    elif order["website"] == "https://www.fermentationculture.eu":
        sender_row = [{
            "Name1": "fermentationculture.eu",
            "AddressLine1": "Gallabergerstrasse 28",
            "PostalCode": "4860",
            "CountryID": "AT",
            "City": "Lenzing",
            "Email": "office@fermentationculture.eu",
            "Tel1": "00436801309731"
            }]

    ### Artikel
    collo_article_list = []
    
    for item in order["line_items"]:
        product = helper_funcs.products["id"][str(item["product_id"])]
        # quantity
        quantity = str(item["quantity"])
        name = item["name"]
        

        if len(product["variations"]) == 0:
            weight = d(product["weight"]) * d(item["quantity"]) / 1000 
            value_d = d(item["total"])
            unit_net_weight = d(product["weight"]) / 1000
        else: 
            var_id = str(item["variation_id"])
            weight = d(product["variations"][var_id]["weight"]) * d(item["quantity"]) / 1000
            unit_net_weight = d(product["variations"][var_id]["weight"]) / 1000
            value_d = d(item["total"])


        origin = ""
        hsnumber = ""

        if product["categories"][0]["slug"] == "koji":
            hsnumber = "30029050"
            origin = "Japan"
        else:
            for j in range(len(product["attributes"])):
                if product["attributes"][j]["name"] == "origin":
                    origin = product["attributes"][j]["options"][0]
                elif product["attributes"][j]["name"] == "hsnumber":
                    hsnumber = product["attributes"][j]["options"][0]

        if origin == "Japan":
            origin = "JP"
        elif origin == "Austria":
            origin = "AT"
        elif origin == "Indonesia":
            origin = "ID"
        elif origin == "Germany":
            origin = "DE"
        
        collo_article_row = {
            "ArticleName": name,
            "Quantity": quantity,
            "UnitID": "PCE",
            "HSTariffNumber": hsnumber,
            "CountryOfOriginID": origin,
            "ValueOfGoodsPerUnit": str(round(item["price"], 2)),
            "CurrencyID": "EUR",
            "ConsumerUnitNetWeight": str(unit_net_weight),
            "CustomsOptionID": 1
            }
        collo_article_list.append(collo_article_row)

    collo_article_list_ = collo_article_list_template(collo_article_list)
    
    ### Größe und Gewicht des Pakets
    if xs == True:
        collo = [{
            "Length": 22,
            "Height": 2,
            "Width": 15,
            "Weight": round(float(collo_weight), 2),
            "ColloArticleList": collo_article_list_
            }]
    else:    
        collo = [{
            "Weight": round(float(collo_weight), 2),
            "ColloArticleList": collo_article_list_
            }]

    
    collo_list = collo_list_template(collo)

    ### Zusatzleistungen
    if breakable == True:
        feature_row = [{"ThirdPartyID": "004"}]
    else: 
        feature_row = []
    feature_list = feature_list_template(feature_row)

    print(feature_list_template(feature_row))

    shipment_row = {
        "ClientID": ClientID,
        "OrgUnitID": OrgUnitID,
        "OrgUnitGuid": OrgUnitGuid,
        "DeliveryServiceThirdPartyID": parcel_type,
        "OURecipientAddress": address_row,
        "OUShipperAddress": sender_row,
        "PrinterObject": printer_row,
        "ColloList": collo_list,
        "DeliveryInstruction": instructions,
        "FeatureList": feature_list
        }


    ### Post Shipment ###
    response = api.service.ImportShipment(row=shipment_row)
    response = helpers.serialize_object(response)
    pretty(response)
    code = response['ImportShipmentResult']['ColloRow'][0]['ColloCodeList']['ColloCodeRow'][0]['Code']
    
    
    
    file = f"/tmp/post_labels/{code}.pdf"
    with open(file, "wb+") as pdf_file:
        pdf_file.write(base64.b64decode(response["pdfData"]))
    conn.printFile(settings.printers["A4"], file, f"Postlabel - {ship['last_name']}", {})
    #webbrowser.open_new_tab(file)

    data = {
        "meta_data": [
                    {
                    "key": "_tracking_code", 
                    "value": code
                    }]}

    print(shops[order["website"]].put("orders/{}".format(order["id"]), data))
    print(code)

    order["meta_data"].append(
        {"key": "_tracking_code", 
        "value": code}
        )
    orderfile_handler.save_all_orders()

    emails.send_tracking_email(order, code)


def end_of_day():
    ### Perform End Of Day
    user = {
        "clientID": ClientID,
        "orgUnitID": OrgUnitID,
        "orgUnitGuid": OrgUnitGuid
        }

    end = api.service.PerformEndOfDay(**user)

    today = date.today()
    
    file = f"/tmp/post_labels/endofday-{today.day}.{today.month}.pdf"
    with open(file, "wb+") as pdf_file:
        pdf_file.write(base64.b64decode(end['PerformEndOfDayResult']))
        conn.printFile(settings.printers["A4"], file, "Packerl Zusammenfassung", {})
    #webbrowser.open_new_tab(file)