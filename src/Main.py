# BUG: 
# Reihenfolge wird bei Suche nicht anerkannt
# Frische Notizen verschwinden wenn von processing auf on-hold und zurück. 
# Notizen werden also lokal nicht gespeichert

from woocommerce import API
import json
import datetime
from datetime import date
import dateutil.parser
import time
import calendar
import pycountry
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
from google.cloud import translate_v3beta1 as translate
from decimal import Decimal as d
import os
import sys
from glob import glob
import webbrowser
import codecs
from bs4 import BeautifulSoup
import math
from concurrent import futures
import threading
import pprint
from collections import Counter

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '4')
from gi.repository import Gtk, Gdk, GObject, GtkSource

from printfunctions import *
import cn22
import CN23
import letter_insert
from shops import shops
import emails
import settings
from settings import credentials
import helper_funcs
import post

create_single_json = False # Creates a json of a single order in the temp folder
user = "employee"


pp = pprint.PrettyPrinter(indent=4)

### Google translate stuff
if os.path.exists('includes/googlecred.json'):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'includes/googlecred.json'
else:
    input("Google credentials not found. Please save as googlecred.json into the data folder.")
translator = translate.TranslationServiceClient()
project_id = 'shaped-entropy-248808'
location = 'global'
parent = translator.location_path(project_id, location)
###

font_config = FontConfiguration()
conn = cups.Connection()

# GUI elements
builder = Gtk.Builder()
builder.add_from_file("includes/OrderApp.glade")

window = builder.get_object("window1")
scrolledwindow1 = builder.get_object("scrolledwindow1")
refreshorders_button = builder.get_object("refreshorders_button")
searchentry = builder.get_object("searchentry")
orderfilterbox = builder.get_object("orderfilterbox")
combobox = builder.get_object("orderfilter")
statusbar = builder.get_object("statusbar")

gtk_lang_manager = GtkSource.LanguageManager()

statuses = {
    "processing": "Processing",
    "on-hold": "On-hold",
    "pending": "Pending",
    "shipped": "Versendet, offen"
    }


def gtk_style():
    css = b"""
        #processing {
            color: #222;
            background: #C6E1C6;
        }
        #on-hold {
            color: #222;
            background: #F8DDA7;
        }
        #on-hold-alt {
            color: #222;
            background: #F8C359}

        #pending-payment {
            color: #222;
            background: #E5E5E5;
        }
        #completed {
            color: #222;
            background: #C8D7E1;
        }
        #shipped {
            color: #222;
            background: #A0DFDB;
        }
        #faellig {
            color: #222;
            background: #DF9292
        }

        #legende {
            /*background: #F5F6F7;*/
            font-size: 16px;
            border-bottom: 1px solid #CCC
        }

        #produkt {
            font-size: 22px;
            }

        #CategoryName {
            font-size: 26px;
            border-bottom: 1px solid #CCC;
            padding-top: 20px;
        }

        #order_title {
            font-size: 28px;
            }

        #order_sendbutton {
            font-size: 24px;
            }

        #big_button {
            font-size: 28px;
            }

        #ProduktpopupAnzahl, #ProduktpopupName {
            font-size: 18px;
        }

        #ProduktpopupGrid {
            padding: 20px 20px 20px 20px;
        }

        #post_box {
            margin: 25px 0;}

        #progressbar {
            min-height: 20px;}

        #dialogtext {
            font-size: 28px;
            margin: 15px;}
        
        #ProductsSummary {
            font-size: 28px;}

        #OrderHints {
            font-size: 22px;
            color: #FF2F2F
            }

        """

    
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    ) 


class MainWindow():

    toggled_orders = []
    checkboxes = []

    def __init__(self):
        window.connect("key-press-event", self.on_key_press_event)
        self.load_all_orders()
        searchentry.connect(
            "activate",
            self.on_searchentry_activated
        )
        self.selection = "processing"
        self.total_label = Gtk.Label()

        radio_button_box = Gtk.Box()

        all_orders_button = Gtk.RadioButton()
        all_orders_button.set_active(False)
        all_orders_button.set_label("All")
        radio_button_box.add(all_orders_button)

        for key in statuses:
            status_button = Gtk.RadioButton.new_from_widget(all_orders_button)
            status_button.set_label(statuses[key])
            radio_button_box.add(status_button) 
            status_button.set_active(False)
            status_button.connect(
                "toggled",
                self.set_selection,
                key
            )
            if key == "processing":
                status_button.set_active(True)
            else:
                status_button.set_active(False)

        all_orders_button.connect(  # Needs to be here, otherwise it'll render all
            "toggled",              # orders before going on to render processing orders
            self.set_selection,
            "all"
        )

        orderfilterbox.pack_start(radio_button_box, 0, 0, 0)

        self.reverse_button = Gtk.CheckButton()
        self.reverse_button.set_label("Reihenfolge von Alt nach Neu")
        self.reverse_button.set_active(True)
        self.reverse_button.set_margin_left(100)
        self.reverse_button.connect("clicked", self.update_window)
        orderfilterbox.pack_end(self.reverse_button, 0, 0, 0)


        refreshorders_button.connect("button-press-event", self.on_refresh_orders_clicked)

        self.update_window()

    def render_orders(self, filtered_orders):
        """Renders a given list of order-objects into the main window.
        Each column is defined as a function, to make rearranging easy.
        """

        self.checkboxes = []
        self.toggled_orders = []

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(10)
        self.grid.set_row_spacing(10)

        def checkbox(self, k):
            if i == 0:
                self.leg_checkbox = Gtk.CheckButton()
                self.leg_checkbox.set_name("legende")
                self.leg_checkbox.connect("toggled", self.on_master_checkbox_toggled)
                self.leg_checkbox.set_name("master_checkbox")
                print(self.leg_checkbox.get_active())
                self.grid.attach(self.leg_checkbox, k, 1, 1, 1)


            self.checkbox = Gtk.CheckButton()
            self.grid.attach(self.checkbox, k, i+2, 1, 1)
            self.checkbox.connect("toggled",
                            self.on_checkbox_toggled,
                            filtered_orders[i])
            self.checkboxes.append(self.checkbox)

        def ordernumber(k):
            if i == 0:
                leg_nummerstatus = Gtk.Label()
                leg_nummerstatus.set_text("Order")
                leg_nummerstatus.set_name("legende")
                self.grid.attach(leg_nummerstatus, k, 1, 1, 1)
            

            owc = Gtk.LinkButton()
            owc.set_uri(filtered_orders[i]["website"] + "/wp-admin/post.php?post={}&action=edit"
                        .format(filtered_orders[i]["id"]))

            owc.set_label("{}".format(filtered_orders[i]["number"]))

            self.grid.attach(owc, k, i+2, 1, 1)

            owc.set_name(filtered_orders[i]["status"])
            date_delta = datetime.datetime.today() - dateutil.parser.isoparse(filtered_orders[i]["date_modified"])
            if (date_delta.days > 30 and filtered_orders[i]["status"] == "shipped"):
                owc.set_name("faellig")
            elif (date_delta.days > 7 and filtered_orders[i]["status"] == "on-hold"):
                owc.set_name("on-hold-alt")

        def invoice(k):
            button = Gtk.LinkButton()
            
            button.set_uri(filtered_orders[i]["website"] + "/wp-admin/post.php?post={}&action=edit&bewpi_action=view&nonce=bbf8cb611f"
                        .format(filtered_orders[i]["id"]))
            button.set_label("LF")

            self.grid.attach(button, k, i+2, 1, 1)

            button.set_name("invoice")

        def dates(k):
            if i == 0:
                leg_datum = Gtk.Label()
                leg_datum.set_text("Datum")
                leg_datum.set_name("legende")
                self.grid.attach(leg_datum, k, 1, 1, 1)


            label = Gtk.Label()
            date_created = dateutil.parser.isoparse(filtered_orders[i]["date_created"]).strftime("%d.%m.%y")
            date_modified = dateutil.parser.isoparse(filtered_orders[i]["date_modified"]).strftime("%d.%m.%y")
            if date_created == date_modified:
                date_modified = ""
            else:
                date_modified = "\nEdit: " + date_modified

            date_completed = ""
            date_text = "{}{}".format(date_created, date_modified)
            if filtered_orders[i]["date_completed"] is not None:
                date_completed = dateutil.parser.isoparse(filtered_orders[i]["date_completed"]).strftime("%d.%m.%y")
                date_text += "\nCompleted: {}".format(date_completed)
            
            label.set_markup(date_text)
            label.set_justify(Gtk.Justification.RIGHT)
            label.set_xalign(1)
            self.grid.attach(label, k, i+2, 1, 1)

        def name(k):
            if i == 0:
                leg_name = Gtk.Label()
                leg_name.set_text("Name")
                leg_name.set_name("legende")
                self.grid.attach(leg_name, k, 1, 1, 1)

            fname = filtered_orders[i]["shipping"]["first_name"]
            lname = filtered_orders[i]["shipping"]["last_name"]
            business = filtered_orders[i]["billing"]["company"]
            
            if fname == "":
                fname = "-"

            if not business == "":
                businesslabel = "\n" + business
            else:
                businesslabel = ""

            Name = Gtk.Button()

            if len(lname + fname) < 25:
                Name.set_label("{0} {1}{2}".format(fname, lname, businesslabel))
            else:
                Name.set_label("{0}\n{1}{2}".format(fname, lname, businesslabel))

            Name.set_alignment(0,0.5)
            Name.set_relief(Gtk.ReliefStyle.NONE)
            # Name.connect("clicked",
            #     order_details_popup,
            #     filtered_orders[i])
            Name.connect("button-press-event",
                on_name_clicked,
                filtered_orders[i])
            self.grid.attach(Name, k, i+2, 1, 1)
        
        def total(k):
            if i == 0:
                leg_total = Gtk.Label()
                leg_total.set_text("Total")
                leg_total.set_name("legende")
                self.grid.attach(leg_total, k, 1, 1, 1)

            total = Gtk.Label()
            total.set_text("{}€".format(filtered_orders[i]["total"]))
            #total.set_xalign(0)
            self.grid.attach(total, k, i+2, 1, 1)

        def shippingaddress(k):
            if i == 0:
                leg_shipping = Gtk.Label()
                leg_shipping.set_text("Versandadresse")
                leg_shipping.set_name("legende")
                self.grid.attach(leg_shipping, k, 1, 1, 1)
            try:
                country = pycountry.countries.get(alpha_2=filtered_orders[i]["shipping"]["country"]).name
            except:
                country = filtered_orders[i]["shipping"]["country"]

            shipping = (
                "{add_1}{add_2}\n{postcode} {city}\n{country}"
                    .format(
                        add_1 = filtered_orders[i]["shipping"]["address_1"],
                        add_2 = "" if filtered_orders[i]["shipping"]["address_2"] == "" else "\n" + filtered_orders[i]["shipping"]["address_2"],
                        postcode = filtered_orders[i]["shipping"]["postcode"],
                        city = filtered_orders[i]["shipping"]["city"],
                        country = country,
                ))

            shipping_label = Gtk.Label()
            shipping_label.set_text(shipping)
            shipping_label.set_selectable(True)
            shipping_label.set_xalign(0)
            self.grid.attach(shipping_label, k, i+2, 1, 1)

        def billingaddress(k):
            if i == 0:
                leg_billing = Gtk.Label()
                leg_billing.set_text("Rechnungsadresse")
                leg_billing.set_name("legende")
                self.grid.attach(leg_billing, k, 1, 1, 1)

            try:
                country = pycountry.countries.get(alpha_2=filtered_orders[i]["billing"]["country"]).name
            except:
                country = filtered_orders[i]["billing"]["country"]

            billing = (
                "{add_1}{add_2}\n{postcode} {city}\n{country}"
                    .format(
                        add_1 = filtered_orders[i]["billing"]["address_1"],
                        add_2 = "" if filtered_orders[i]["billing"]["address_2"] == "" else "\n" + filtered_orders[i]["billing"]["address_2"],
                        postcode = filtered_orders[i]["billing"]["postcode"],
                        city = filtered_orders[i]["billing"]["city"],
                        country = country,
                ))

            billing_label = Gtk.Label()
            billing_label.set_text(billing)
            billing_label.set_xalign(0)
            billing_label.set_selectable(True)
            self.grid.attach(billing_label, k, i+2, 1, 1)

        def email_button(k):
            if i == 0:
                leg_email = Gtk.Label()
                leg_email.set_text("Email")
                leg_email.set_name("legende")
                self.grid.attach(leg_email, k, 1, 1, 1)

            email = Gtk.Button.new_with_label("@")
            email.connect("clicked",
                            self.on_email_clicked,
                            filtered_orders[i]["billing"]["email"])
            email.set_tooltip_text(filtered_orders[i]["billing"]["email"])

            self.grid.attach(email, k, i+2, 1, 1)

        def tracking(k):
            if i == 0:
                leg_produkte = Gtk.Label()
                leg_produkte.set_text("Tracking")
                leg_produkte.set_name("legende")
                self.grid.attach(leg_produkte, k, 1, 2, 1)

            tracking_val = "-"
            for item in reversed(filtered_orders[i]["meta_data"]):
                if item["key"] == "_tracking":
                    tracking_val = item["value"]
                    break
            
            label = Gtk.Label()
            label.set_text(tracking_val)
            self.grid.attach(label, k, i+2, 1, 1)
        
        def tracking_entry(k):
            container = Gtk.Box()
            spacer = Gtk.Label()
            spacer.set_text(" ")

            entry = Gtk.Entry()
            entry.set_width_chars(15)
            entry.set_vexpand(False)
            entry.connect(
                "activate",
                self.on_tracking_entry_activated,
                filtered_orders[i]
                )
            container.add(entry)

            for item in reversed(filtered_orders[i]["meta_data"]):
                if item["key"] == "_tracking_code":
                    tracking_code = item["value"]
                    link = Gtk.LinkButton()
                    link.set_label(tracking_code)
                    link.set_uri("https://www.post.at/en/sv/item-details?snr={}".format(tracking_code))
                    container.add(link)
                    
                    info = Gtk.Label()
                    info.set_text("loading..")

                    status = filtered_orders[i].get("send_status")
                    info.set_text(str(status))

                    container.add(info)

                    # if not status == "Item at recipient‘s": 
                    #     print("pass:", status)
                    #     thread = threading.Thread(
                    #         target=trackingcheck.check_thread, 
                    #         args=(tracking_code, info, filtered_orders[i]))
                    #     thread.start()
                    break
            
            container.set_orientation(Gtk.Orientation.VERTICAL)
            #container.add(spacer)
            
            self.grid.attach(container, k, i+2, 1, 1)

            return entry

        def order_notes(k):
            if i == 0:
                leg_notes = Gtk.Label()
                leg_notes.set_text("Notizen")
                leg_notes.set_name("legende")
                self.grid.attach(leg_notes, k, 1, 1, 1)

            entry = Gtk.TextView()
            entry.set_size_request(400, -1)
            
            for item in filtered_orders[i]["meta_data"]:
                if item["key"] == "order_notes":
                    notes = item["value"]
                    break
                else:
                    notes = ""
            

            buffer = GtkSource.Buffer()
            buffer.set_text(notes)

            entry.set_buffer(buffer)
            entry.set_wrap_mode(2)

            entry.connect(
                "focus-out-event",
                self.order_notes_helper,
                buffer,
                filtered_orders[i]
            )

            self.grid.attach(entry, k, i+2, 1, 1)

        def payment_method(k):
            if filtered_orders[i]["status"] == "on-hold":
                label = Gtk.Label()
                method = filtered_orders[i]["payment_method"]
                label.set_text(method)
                self.grid.attach(label, k, i+2, 1, 1)

        # helper functions
        def on_name_clicked(widget, event, order):
            if event.button == 1:
                OrderDetailsPopup(widget, order)
            elif event.button == 3:
                menu = Gtk.Menu()

                new_order = Gtk.MenuItem("New order with the same data")
                new_order.connect("activate", NewOrderFromExistingPopup, order)
                menu.add(new_order)

                reminder = Gtk.MenuItem("Send reminder")
                reminder.connect("activate", ReminderEmailWindow, order, "reminder", self)
                menu.add(reminder)
                

                menu.show_all()
                #menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_EAST, Gdk.Gravity.SOUTH_WEST, None)
                menu.popup_at_pointer(event)

        # Renderloop
        for i in range(len(filtered_orders)):
            k = 1

            checkbox(self, k)
            k += 1

            ordernumber(k)
            k += 1

            dates(k)
            k += 1

            name(k)
            k += 1

            total(k)
            k += 1

            shippingaddress(k)
            k += 1

            billingaddress(k)
            k += 1

            email_button(k)
            k += 1

            tracking(k)
            k += 1

            # Assign first entry in list to variable, so it can be selected from search by hitting enter
            if i == 0:
                self.tracking_entry = tracking_entry(k)
            else:
                tracking_entry(k)
            k += 1

            order_notes(k)
            k += 1

            payment_method(k)
            k += 1
        
        q = scrolledwindow1.get_children()
        if len(q) > 0:
            q[0].destroy()
        scrolledwindow1.add_with_viewport(self.grid)
        window.show_all()
        print(f"Rendered {len(filtered_orders)} orders")

    def update_window(self, *args):
        """Filters all orders according to the selected status, then calls render_orders()"""

        global filtered_orders
        filtered_orders = []

        for i in range(len(self.all_orders)):
            if len(filtered_orders) > 100:
                break
            if self.all_orders[i]["status"] == self.selection:
                filtered_orders.append(self.all_orders[i])
            elif self.selection == "all":
                filtered_orders.append(self.all_orders[i])
        
        if self.reverse_button.get_active() == True:
            filtered_orders.reverse()

        self.render_orders(filtered_orders)
        self.status_bar_info(filtered_orders)

    def search_orders(self):
        
        text = searchentry.get_text()
        text = str(text).lower()
        text_liste = text.split() 

        if text == "":
            self.update_window()
            return
        elif len(text) < 3:
            return
        
        filtered_orders = []
        for i in range(len(self.all_orders)):
            if len(filtered_orders) > 30:
                break

            query_string = ""
            query_string += self.all_orders[i]["number"] + " "

            for key in self.all_orders[i]["billing"]:
                if key == "country":
                    try:
                        query_string += pycountry.countries.get(alpha_2=str(self.all_orders[i]["billing"][key])).name.lower() + " "
                    except:
                        print("Could not find country")
                        pass
                else:
                    query_string += str(self.all_orders[i]["billing"][key]).lower() + " "

            for key in self.all_orders[i]["shipping"]:
                query_string += str(self.all_orders[i]["shipping"][key]).lower() + " "
            for j in range(len(self.all_orders[i]["line_items"])):
                query_string += str(self.all_orders[i]["line_items"][j]["name"]).lower() + " "
            for j in range(len(self.all_orders[i]["meta_data"])):
                query_string += str(self.all_orders[i]["meta_data"][j]["value"]).lower() + " "
            query_string += str(self.all_orders[i]["website"])

            counter = 0
            for j in range(len(text_liste)):
                if query_string.__contains__(text_liste[j]):
                    counter += 1
            if counter == len(text_liste):
                filtered_orders.append(self.all_orders[i])

        self.render_orders(filtered_orders)
        self.status_bar_info(filtered_orders)
    
    def change_order_status(self, widget, order, status):
        data = {
            "status": status
            }

        shops[order["website"]].put(
            "orders/{}".format(order["id"]), 
            data
            )

        order["status"] = status
        
        orderfile_handler.save_all_orders()
        self.update_window()

    def post_to_order(self, widget, order, data):
        shops[order["website"]].put(
                    "orders/{}".format(order["id"]), 
                    data
                    )

    # Orderfile handling Stuff
    def load_all_orders(self):
        if os.path.exists("data/orders.json"):
            with open("data/orders.json", "r") as json_file:
                self.all_orders = json.load(json_file)
                if self.all_orders[0].get("nth_order") == False:
                    count_orders_by_email()
                else:
                    print("Orders already counted")

        else:
            self.all_orders = []
            self.get_orders(None, "All")

    def save_all_orders(self):
        with open("data/orders.json", "w") as json_file:
            json_file.write(json.dumps(self.all_orders))

    def count_orders_by_email(self):
        number_of_order_by_email = Counter()
        for order in self.all_orders:
            email = order["billing"]["email"].lower()
            number_of_order_by_email[email] += 1
            order["nth_order"] = number_of_order_by_email[email]

    def sort_orders(self):
        def return_date(order):
            return datetime.datetime.fromisoformat(order["date_created"])
        self.all_orders.sort(key=return_date)
        
    def refresh_orders(self):
        if not os.path.exists("sessioninfo.json"):
            open("sessioninfo.json", "w+")
        with open("sessioninfo.json", "r") as file:
            try:
                last_time = json.loads(file.read())["last_smart_refresh"]
            except json.JSONDecodeError:
                print("No data on last refresh, refreshing last 7 days.")
                last_time = datetime.datetime.now() - datetime.timedelta(days=7)
                last_time = last_time.replace(microsecond=0).isoformat()
        with open("sessioninfo.json", "w") as file:
            now = datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(hours=1)
            data = {
                "last_smart_refresh": now.isoformat()
                }
            file.write(json.dumps(data))

        new_orders = []

        for shop in shops:
            page = 1
            while True:
                orders_raw = shops[shop].get(f"orders?per_page=100&after={last_time}&page={page}")
                orders = orders_raw.json()
                for order in orders:
                    order["website"] = shop
                new_orders.extend(orders)
                
                page += 1

                if int(orders_raw.headers["X-WP-Total"]) < 100:
                    break
        
        orders_to_be_updated = []

        for i in range(len(self.all_orders)):
            ordernumber = self.all_orders[i]["number"]
            website = self.all_orders[i]["website"]

            if any(order["number"] == ordernumber and 
                order["website"] == website for order in new_orders):
                orders_to_be_updated.append(i)

        orders_to_be_updated = sorted(orders_to_be_updated, reverse=True)
    
        for i in range(len(orders_to_be_updated)):
            self.all_orders.pop(orders_to_be_updated[i])

        self.all_orders.extend(new_orders)
        
        self.sort_orders()
        self.count_orders_by_email()

        self.update_window()

    def get_orders(self, event, pages_requested):

        def get_page(args):
            shop = shops[args[0]]
            page = args[1]
            while True:
                try:
                    response = shop.get(f"orders?per_page=100&page={page}").json()
                    print(f"Getting page {page} from {shop.url}")
                    
                    for i in range(len(response)):
                        response[i]["website"] = shop.url
                    self.progress += 1
                    return response

                except ReadTimeout:
                    print(f"Page {page} timed out")

        def order_retriever():
            args = []
            
            for shop in shops:
                args.extend([(shop, page) for page in range(1, self.pages_per_shop[shop] + 1)])

                
            with futures.ThreadPoolExecutor(max_workers=4) as executor:
                results = executor.map(get_page, args) 
            requested_orders = []

            for result in results:
                requested_orders.extend(result)

            orders_to_be_popped = []

            for i in range(len(self.all_orders)):
                ordernumber = self.all_orders[i]["number"]
                website = self.all_orders[i]["website"]

                if any(
                    d["number"] == ordernumber 
                    and d["website"] == website 
                    for d in requested_orders
                    ):
                    orders_to_be_popped.append(i)

            orders_to_be_popped = sorted(orders_to_be_popped, reverse=True)

            for i in range(len(orders_to_be_popped)):
                self.all_orders.pop(orders_to_be_popped[i])

            self.all_orders.extend(requested_orders)
            
            GObject.idle_add(stop_process)

        def init_process():
            self.running = True
            GObject.timeout_add(200, update_progress)
            self.worker.start()

        def update_progress():
            if self.running:
                if self.progress + 1 <= self.pages_total:
                    self.progresstext.set_text(
                        f"Downloading orders ({(self.progress + 1) * 100} of {self.pages_total * 100})")
                else:
                    self.progresstext.set_text("Done")
                self.progressbar.set_fraction(self.progress / self.pages_total)
            return self.running

        def stop_process():
            self.running = False
            self.worker.join()
            self.dialog.destroy()

            self.sort_orders()
            self.count_orders_by_email()

            with open("data/orders.json", "w+") as file:
                file.write(json.dumps(self.all_orders))

            self.update_window()

        self.dialog = Gtk.Dialog(
            "",
            None,
            None,
            None)
        self.dialog.set_default_size(400,100)
        self.dialog.set_decorated(True)

        self.progresstext = Gtk.Label()
        self.progresstext.set_vexpand(True)
        self.progresstext.set_text("Starting...")

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_name("progressbar")
        
        self.dialogbox = self.dialog.get_content_area()
        self.dialogbox.add(self.progresstext)
        self.dialogbox.add(self.progressbar)

        self.dialog.show_all()

        self.new_orders = []
        self.running = False
        self.pages_per_shop = {shop: 0 for shop in shops}
        self.pages_total = 0
        if pages_requested == "All":
            for shop in shops:
                response = shops[shop].get("orders?per_page=100").headers
                self.pages_per_shop[shop] = int(response["X-WP-TotalPages"])
                self.pages_total += int(response["X-WP-TotalPages"])
                print(f"Getting {self.pages_per_shop[shop]} Pages from {shop}")
        else:
            for shop in shops:
                self.pages_per_shop[shop] = pages_requested
                self.pages_total += self.pages_per_shop[shop]
        
        
        self.worker = threading.Thread(target=order_retriever)
        init_process()        
        self.progress = 0 

    # GUI Stuff
    def status_bar_info(self, orders):
        total = d(0)
        for i in range(len(orders)):
            total += d(orders[i]["total"])
        if len(orders) > 0:
            self.total_label.set_text(
                str(len(orders)) + " Bestellungen, " +
                str(total.quantize(d("1.00"))) + "€ Gesamtwert, " +
                str( (total / len(orders)).quantize(d("1.00")) ) + "€ Durschnittswert"
            )

            statusbar.pack_start(self.total_label, 1, 1, 1)

    def on_email_clicked(self, widget, email):
        os.system("""thunderbird -compose "to='{}',subject='Your Order at fermentationculture.eu'" """.format(email))

    def on_checkbox_toggled(self, widget, order):
        if order not in self.toggled_orders:
            self.toggled_orders.append(order)
        else:
            self.toggled_orders.remove(order)

    def on_master_checkbox_toggled(self, widget):
        if Gtk.CheckButton.get_active(self.leg_checkbox) is True:
            print("active")
            for i in range(len(self.checkboxes)):
                Gtk.ToggleButton.set_active(self.checkboxes[i], True)
        else:
            print("inactive")
            for item in self.checkboxes:
                Gtk.ToggleButton.set_active(item, False)

    def on_key_press_event(self, widget, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl and event.keyval == Gdk.KEY_f:
            searchentry.set_text("")
            searchentry.grab_focus()

        if event.keyval == Gdk.KEY_F5:
            Handler.orderrefresh(Handler(), "")

    def on_searchentry_activated(self, widget):
        self.tracking_entry.grab_focus()

    def on_tracking_entry_activated(self, widget, order):
        code = widget.get_text()
        print("Received code")
        data = {
            "meta_data": [
                        {
                        "key": "_tracking_code", 
                        "value": code
                        }]}

        print("Posting to site")
        shops[order["website"]].put("orders/{}".format(order["id"]), data)
        print("done")
        order["meta_data"].append(
            {"key": "_tracking_code", 
            "value": code}
            )
        orderfile_handler.save_all_orders()

        print("Sending Email")
        emails.send_tracking_email(order, code)
        print("Sent Email")

        searchentry.set_text("")
        searchentry.grab_focus()

    def on_refresh_orders_clicked(self, widget, event):
        if event.button == 1:
            self.refresh_orders()
        elif event.button == 3:
            menu_orderrefresh = Gtk.Menu()

            refresh_all = Gtk.MenuItem("Alle Bestellungen neu laden")
            refresh_all.connect("activate", 
                ConfirmWindow,
                "Alle Bestellungen neu laden?",
                self.get_orders,
                None,
                "All")
            menu_orderrefresh.add(refresh_all)

            menu_orderrefresh.show_all()
            menu_orderrefresh.popup_at_widget(refreshorders_button, Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST, None)

    def order_notes_helper(self, widget, event, buffer, order):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        self.process_order_notes_text(text, order)
        
    def process_order_notes_text(self, text, order):
        data = {
            "meta_data": [
                {
                "key": "order_notes",
                "value": text
                }
            ]
        }
        
        shops[order["website"]].put(
            "orders/{0}".format(order["id"]), data
            ).json()["meta_data"]
                
        order["meta_data"].append(
            {"key": "order_notes",
                "value": text}
            )

    def set_selection(self, origin, status):
        self.selection = status
        self.update_window()


def retrieve_products():
    global products

    if os.path.exists("data/products/products.json"):
        file = open("data/products/products.json", "r")
        products = json.load(file)

    else:
        products = {
                    "sku": {},
                    "id": {}
                    }

        for key in shops:
            antwort = shops[key].get("products?per_page=100").json()
            sku_list = []

            for i in range(len(antwort)):
                sku = antwort[i]["sku"]
                productid = antwort[i]["id"]

                if len(antwort[i]["variations"]) > 0:
                    variations = shops[key].get(
                        "products/{}/variations".format(
                            antwort[i]["id"]
                        )).json()

                    antwort[i].pop("variations")
                    antwort[i]["variations"] = {}
                    for v in range(len(variations)):
                        antwort[i]["variations"][variations[v]["id"]] = variations[v]

                """ if sku not in sku_list:
                    sku_list.append(antwort[i]["sku"])
                    products["sku"][sku] = antwort[i]
                else: 
                    pass """
                    
                products["sku"][sku] = antwort[i]
                
                products["id"][productid] = antwort[i]

        with open("data/products/products.json", "a+") as file:
            json.dump(products, file)


class OrderDetailsPopup(Gtk.Window):
    instances = []
    def __init__(self, widget, order):
        for instance in self.instances:
            instance.destroy()

        self.instances.append(self)
        
        Gtk.Window.__init__(self, 0)
        self.connect("key-press-event", self.on_key_press_event, order)

        self.set_position(Gtk.WindowPosition(3))
        self.set_title("")

        self.order = order
    
        self.render_gui(order)

    def render_gui(self, order):    
        grid = Gtk.Grid()
        margin = 5
        grid.set_margin_top(margin)
        grid.set_margin_left(margin)
        grid.set_margin_right(margin)
        grid.set_margin_bottom(margin)

        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_hexpand(True)

        spacer = Gtk.Label()

        col = 1
        row = 1

        # TITLE
        title_label = Gtk.LinkButton()
        title_label.set_label("#{0} - {1}".format(order["number"], order["shipping"]["last_name"]))
        title_label.set_uri(order["website"] + "/wp-admin/post.php?post={}&action=edit"
                        .format(order["id"]))
        title_label.set_name("order_title")
        title_label.set_margin_bottom(20)
        grid.attach(title_label, col, row, 2, 1)

        row += 1

        # ORDER HINTS #
        if user == "employee":
            
            hints_label = Gtk.Label()
            text = ""

            # HINTS
            if order["shipping"]["country"] not in helper_funcs.EU_countries:
                text += "Zollformulare notwendig: "
                if (helper_funcs.order_contains_only_spores(order) == True and 
                    order["shipping"]["country"] not in ["CA", "US"]):
                    text += "CN22\n"
                else:
                    text += "CN23 & Rechnung\n"
            if helper_funcs.order_contains_only_food(order) == True:
                text += "Keine Beilage notwendig"
            
            hints_label.set_text(text)
            hints_label.set_alignment(0,0)
            hints_label.set_name("OrderHints")
            grid.attach(hints_label, col, row, 2, 1)

            row += 1


        # Nth Order
        nth_order_text = str(order["nth_order"]) + ". Bestellung"
        subtitle_label = Gtk.Label()
        subtitle_label.set_text(nth_order_text)
        subtitle_label.set_name("produkt")
        grid.attach(subtitle_label, col, row, 2, 1)
        
        row += 1

        # ADRESSEN
        grid.insert_column(2)

        leg_shipping_address = Gtk.Label()
        leg_shipping_address.set_text("Versandadresse")
        leg_shipping_address.set_name("legende")
        leg_shipping_address.set_hexpand(True)
        grid.attach(leg_shipping_address, col, row, 1, 1)

        col += 1

        leg_billing_address = Gtk.Label()
        leg_billing_address.set_text("Rechnungsadresse")
        leg_billing_address.set_name("legende")
        leg_billing_address.set_hexpand(True)
        grid.attach(leg_billing_address, col, row, 1, 1)

        col -= 1
        row += 1

        country = pycountry.countries.get(alpha_2=order["shipping"]["country"])
        shipping_address_str = (
            "{company}{fname} {lname}\n{add_1}{add_2}\n{postcode} {city}\n{country}"
                .format(
                    company = "" if order["shipping"]["company"] == "" else order["shipping"]["company"] + "\n",
                    fname = order["shipping"]["first_name"],
                    lname = order["shipping"]["last_name"],
                    add_1 = order["shipping"]["address_1"],
                    add_2 = "" if order["shipping"]["address_2"] == "" else "\n" + order["shipping"]["address_2"],
                    postcode = order["shipping"]["postcode"],
                    city = order["shipping"]["city"],
                    country = country.name,
            ))
        shipping_address = Gtk.Label()
        shipping_address.set_text(shipping_address_str)
        shipping_address.set_name("adresse")
        shipping_address.set_xalign(0)
        shipping_address.set_selectable(True)
        grid.attach(shipping_address, col, row, 1, 1)

        col += 1

        country = pycountry.countries.get(alpha_2=order["billing"]["country"])
        billing_address_str = (
            "{company}{fname} {lname}\n{add_1}{add_2}\n{postcode} {city}\n{country}"
            .format(
                company= "" if order["billing"]["company"] == "" else order["billing"]["company"] + "\n",
                fname= order["billing"]["first_name"],
                lname= order["billing"]["last_name"],
                add_1= order["billing"]["address_1"],
                add_2= "" if order["billing"]["address_2"] == "" else "\n" + order["billing"]["address_2"],
                postcode= order["billing"]["postcode"],
                city= order["billing"]["city"],
                country= country.name,
            ))

        billing_address = Gtk.Label()
        billing_address.set_text(billing_address_str)
        billing_address.set_name("adresse")
        billing_address.set_xalign(0)
        billing_address.set_margin_top(10)
        billing_address.set_selectable(True)
        grid.attach(billing_address, col, row, 1, 1)

        col -= 1
        row += 1

        # PRINT ADDRESS, CN22 and CN23 BUTTONs
        buttonbox = Gtk.Box()
        buttonbox.set_orientation(Gtk.Orientation.HORIZONTAL)

        
        print_label_button = Gtk.Button()
        
        print_label_button.set_label("<u>A</u>dresse drucken")
        print_label_button.get_child().set_use_markup(True)
        print_label_button.connect(
            "clicked",
            print_addresslabels,
            order)
        buttonbox.pack_start(print_label_button, 1, 1, 1)

        print_letter_button = Gtk.Button()
        print_letter_button.set_label("<u>B</u>eilage drucken")
        print_letter_button.get_child().set_use_markup(True)
        print_letter_button.connect(
            "clicked",
            letter_insert.generate,
            order
        )
        buttonbox.pack_start(print_letter_button, 1, 1, 1)


        print_cn22_button = Gtk.Button()
        print_cn22_button.set_label("CN2<u>2</u> drucken")
        print_cn22_button.get_child().set_use_markup(True)
        print_cn22_button.connect(
            "clicked",
            cn22.generate,
            order
        )
        buttonbox.pack_start(print_cn22_button, 1, 1, 1)

        print_cn23_button = Gtk.Button()
        print_cn23_button.set_label("CN2<u>3</u> drucken")
        print_cn23_button.get_child().set_use_markup(True)
        print_cn23_button.connect(
            "clicked",
            CN23.generate,
            order
        )
        buttonbox.pack_start(print_cn23_button, 1, 1, 1)

        if order["shipping"]["country"] in helper_funcs.EU_countries:
            print_cn22_button.set_sensitive(False)
            print_cn23_button.set_sensitive(False)

        print_invoice_button = Gtk.Button()
        print_invoice_button.set_label("<u>R</u>echnung drucken")
        print_invoice_button.get_child().set_use_markup(True)
        print_invoice_button.connect(
            "clicked",
            print_invoice,
            order,
            True
        )
        buttonbox.pack_start(print_invoice_button, 1, 1, 1)
        
        grid.attach(buttonbox, col, row, 2, 1)

        row += 1

        # ITEMS
        leg_items = Gtk.Label()
        leg_items.set_text("Produkte")
        leg_items.set_name("CategoryName")
        grid.attach(leg_items, col, row, 2, 1)

        row += 1
        for k in range(len(order["line_items"])):
            
            item = order["line_items"][k]
            itemlabel = Gtk.Label()
            itemlabel.set_text(f'{item["quantity"]}x {item["name"]}')
            itemlabel.set_halign(1)
            itemlabel.set_name("produkt")
            grid.attach(itemlabel, col, row, 1, 1)

            col += 1

            if item["sku"] != "":
                print_label_button = Gtk.Button()
                print_label_button.set_label("Print")
                print_label_button.connect(
                    "clicked",
                    print_label_on_BP730,
                    item["sku"],
                    item["quantity"],
                    country_lang[order["shipping"]["country"]]
                )
                grid.attach(print_label_button, col, row, 1, 1)

            col -= 1
            row += 1

            if len(item["meta_data"]) > 0:
                    for m in range(len(item["meta_data"])):
                        if item["meta_data"][m]["key"] in [
                            "_reduced_stock", 
                            "_delivery_time", 
                            "_item_desc",
                            "_units",
                            "_unit_price"]:
                            continue
                        else: 
                            print(item["meta_data"][m]["key"])
                        meta_label = Gtk.Label()
                        meta_label.set_halign(1)
                        meta_label.set_markup("    <b>{0}:</b> {1}".format(
                            item["meta_data"][m]["key"], 
                            item["meta_data"][m]["value"]
                            ))
                        grid.attach(meta_label, col, row, 1, 1)
                        
                        row += 1
        
        # FEES
        
        grid.attach(spacer, col, row, 1, 1)
        row += 1
        for fee in (order["fee_lines"]):
            fee_label = Gtk.Label()
            fee_label.set_text(fee["name"])
            fee_label.set_halign(1)
            fee_label.set_name("produkt")
            grid.attach(fee_label, col, row, 1, 1)
            
            row += 1

        # NOTES
        if len(order["customer_note"]) > 0:
            text = "<b>Kundennotiz:</b> " + order["customer_note"]
            label = Gtk.Label()
            label.set_selectable(True)
            label.set_markup(text)
            label.set_line_wrap(True)
            label.set_size_request(250, -1)
            grid.attach(label, col, row, 2, 1)
            row += 1


        ### Paket Zeug ###
        ### Paket Optionen Post ###
        parcel_types = {
            10: "Paket Österreich",
            69: "Paket Light Outbound"
            }
        parcel = True
        tracking_val = ""
        for item in reversed(order["meta_data"]):
            if item["key"] == "_tracking_code":
                tracking_val = item["value"]
                break
        

        leg_post = Gtk.Label()
        leg_post.set_text("Postlabel")
        leg_post.set_name("CategoryName")
        grid.attach(leg_post, col, row, 2, 1)
        row +=1

        post_box = Gtk.Grid()
        post_box.set_name("post_box")
        post_box.set_column_spacing(10)
        grid.attach(post_box, col, row, 2, 1)

        if order["shipping"]["country"] == "AT":
            self.parcel_type = 10
        else:
            self.parcel_type = 69

        weight = helper_funcs.calculate_total_weight_of_order(order)
        weight += 250
        
        instructions = order["customer_note"]

        parcel_label = Gtk.Label()
        parcel_label.set_text(parcel_types[self.parcel_type])
        post_box.add(parcel_label)

        self.weight_input = Gtk.Entry()
        self.weight_input.set_tooltip_text("In kg")
        self.weight_input.set_text(str(weight/1000))
        post_box.add(self.weight_input)
        
        self.xs = Gtk.CheckButton()
        self.xs.set_label("XS")
        post_box.add(self.xs)

        self.breakable = Gtk.CheckButton()
        self.breakable.set_label("Breakable")
        post_box.add(self.breakable)
        
        self.instructions_input = Gtk.Entry()
        self.instructions_input.set_text(instructions)
        self.instructions_input.set_placeholder_text("Anweisung")
        post_box.add(self.instructions_input)


        get_and_print_label = Gtk.Button()
        get_and_print_label.set_label("Paketlabel anfordern und drucken")
        get_and_print_label.connect(
            "clicked",
            self.get_post_label
            )
        post_box.add(get_and_print_label)

        if len(tracking_val) > 0:
            row += 1
            print_post_label_button = Gtk.Button()
            print_post_label_button.set_label("Postlabel noch mal drucken")
            print_post_label_button.connect(
                "clicked",
                print_a4,
                f"/tmp/post_labels/{tracking_val}.pdf"
                )
            grid.attach(print_post_label_button, col, row, 1, 1)

            row += 1

        grid.attach(spacer, row, col, 1, 1)
        
        row += 1

        # Completed - Versandt Buttons
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation(1))
        spacer = Gtk.Label()
        spacer.set_text(" ")
        spacer.set_vexpand(1)
        box.add(spacer)

        buttonbar = Gtk.Box()

        completed_button = Gtk.Button()
        completed_button.set_label("<u>C</u>ompleted")
        completed_button.get_child().set_use_markup(True)
        completed_button.set_name("order_sendbutton")
        completed_button.connect(
            "clicked",
            mainwindow.change_order_status,
            order,
            "completed"
            )
        completed_button.connect(
            "clicked",
            self.close_window,
            None)

        sent_button = Gtk.Button()
        sent_button.set_label("<u>V</u>ersandt")
        sent_button.get_child().set_use_markup(True)
        sent_button.set_name("order_sendbutton")
        sent_button.connect(
            "clicked",
            mainwindow.change_order_status,
            order,
            "shipped"
            )
        sent_button.connect(
            "clicked",
            self.close_window,
            None
        )

        processing_button = Gtk.Button()
        processing_button.set_label("<u>P</u>rocessing")
        processing_button.get_child().set_use_markup(True)
        processing_button.set_name("order_sendbutton")
        processing_button.connect(
            "clicked",
            mainwindow.change_order_status,
            order,
            "processing"
            )
        processing_button.connect(
            "clicked",
            self.close_window,
            None
        )
        
        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancel")
        cancel_button.set_name("order_sendbutton")
        cancel_button.connect(
            "clicked",
            mainwindow.change_order_status,
            order,
            "cancelled"
            )
        cancel_button.connect(
            "clicked",
            self.close_window,
            None
        )

        if order["status"] == "completed":
            buttonbar.pack_start(processing_button, 0, 1, 1)
            buttonbar.pack_start(sent_button, 0, 1, 1)
        elif order["status"] == "processing":
            buttonbar.pack_start(sent_button, 0, 1, 1)
            buttonbar.pack_end(completed_button, 0, 1, 1)
        elif order["status"] == "on-hold":
            buttonbar.pack_start(processing_button, 0, 1, 1)
            buttonbar.pack_start(sent_button, 0, 1, 1)
            buttonbar.pack_start(cancel_button, 0, 1, 1)
            buttonbar.pack_end(completed_button, 0, 1, 1)
        elif order["status"] == "pending":
            buttonbar.pack_start(processing_button, 0, 1, 1)
            buttonbar.pack_start(sent_button, 0, 1, 1)
            buttonbar.pack_start(cancel_button, 0, 1, 1)
            buttonbar.pack_end(completed_button, 0, 1, 1)
        elif order["status"] == "shipped":
            buttonbar.pack_start(processing_button, 0, 1, 1)
            buttonbar.pack_end(completed_button, 0, 1, 1)

        box.add(buttonbar)

        grid.attach(box, col, row, 2, 1)


        self.add(grid)

        self.show_all()

        if create_single_json is True:
            with open("temp/single_order.json", "w") as file:
                file.write(json.dumps(order))

    def get_post_label(self, widget):
        ConfirmWindow(
            None,
            "Paketmarke bestellen?",
            post.post_shipment,
            "widget",
            self.order,
            self.parcel_type,
            self.instructions_input.get_text(),
            self.weight_input.get_text(),
            self.xs.get_active(),
            self.breakable.get_active()
        )

    def on_key_press_event(self, widget, event, order):
        if event.keyval == Gdk.KEY_Escape:
            self.close_window("", "")
        elif event.keyval == Gdk.KEY_a:
            print_addresslabels(None, order)
        elif event.keyval == Gdk.KEY_b:
            letter_insert.generate(None, order)
        elif event.keyval == Gdk.KEY_2:
            cn22.generate(None, order)
        elif event.keyval == Gdk.KEY_3:
            CN23.generate(None, order)
        elif event.keyval == Gdk.KEY_r:
            print_invoice(None, order, True)
        elif event.keyval == Gdk.KEY_0:
            print_sender()
        elif event.keyval == Gdk.KEY_c:
            mainwindow.change_order_status(
                None, order, "completed")
            self.destroy()

    def close_window(self, widget, whatever):
        self.close()


class NewOrderFromExistingPopup(Gtk.Dialog):
    def __init__(self, widget, order):
        Gtk.Dialog.__init__(self, 0)
    
        self.set_position(Gtk.WindowPosition(3))
        self.set_title("New order from existing one")
        self.set_default_size(600,300)

        containerbox = self.get_children()[0]

        question = Gtk.Label()
        question.set_markup("Neuen Order mit den selben Adressen anlegen?")
        question.set_name("dialogtext")

        yes_button = Gtk.Button()
        yes_button.set_label("Ja")
        yes_button.set_name("big_button")
        yes_button.connect("clicked", self.create_order, order)

        no_button = Gtk.Button()
        no_button.set_label("Nein")
        no_button.set_name("big_button")
        no_button.connect("clicked", self.close_window)

        buttonbox = Gtk.Box()
        
        buttonbox.pack_end(yes_button, 0, 1, 1)
        buttonbox.pack_start(no_button, 0, 1, 1)

        containerbox.set_orientation(Gtk.Orientation.VERTICAL)
        containerbox.pack_start(question, 1, 1, 1)
        containerbox.pack_end(buttonbox, 0, 0, 0)

        self.show_all()

    def create_order(self, widget, order):

        _billing_eu_vat = ""
        _billing_business_consumer_selector = "consumer"
        is_vat_exempt = "no"
        meta = 0

        for item in reversed(order["meta_data"]):
            if item["key"] == "_billing_eu_vat":
                _billing_eu_vat = item["value"]
                meta += 1
            if item["key"] == "_billing_business_consumer_selector":
                _billing_business_consumer_selector = item["value"]
                meta += 1
            if item["key"] == "is_vat_exempt":
                is_vat_exempt = item["value"]
                meta += 1
        
        new_order = {
            "billing": order["billing"],
            "shipping": order["shipping"],
            "meta_data": [
                {   
                    "key": "_billing_eu_vat",
                    "value": _billing_eu_vat
                },
                {
                    "key": "_billing_business_consumer_selector",
                    "value": _billing_business_consumer_selector
                },
                {
                    "key": "is_vat_exempt",
                    "value": is_vat_exempt
                }
            ]
        }
        
        if new_order["billing"]["email"] in ["", None]:
            new_order["billing"]["email"] = "none@none.ad"

        new_order_obj = shops[order["website"]].post("orders", new_order).json()
        print(new_order_obj)

        webbrowser.open_new_tab(
            order["website"] 
            + "/wp-admin/post.php?post=" 
            + str(new_order_obj["id"])
            + "&action=edit"
            )

        self.close_window("?")

    def close_window(self, widget):
        self.close()


class ProductsWindow(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self, title="Produkte")
        self.set_default_size(900, 900)
        self.connect("delete_event", self.close)

        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        

        headerbar = Gtk.HeaderBar()

        self.lang_selection_combobox = Gtk.ComboBoxText()

        edit_css_button = Gtk.Button()
        edit_css_button.set_label("Edit CSS")
        edit_css_button.connect(
            "clicked",
            FileEditor,
            "??", 
            "data/products/label.css", 
            "css", 
            ProductsWindow)

        refresh_products_button = Gtk.Button()
        refresh_products_button.set_label("Refresh Products")
        refresh_products_button.connect(
            "clicked",
            self.on_refresh_products_button_clicked
        )
       
        
        headerbar.pack_start(edit_css_button)
        headerbar.pack_start(refresh_products_button)
        headerbar.pack_start(self.lang_selection_combobox)
        

        self.window_scrolled = Gtk.ScrolledWindow()

        box.pack_start(headerbar, 0, 1, 1)
        box.pack_start(self.window_scrolled, 1, 1, 1)
        
        with open("data/products/products.json") as f:
            self.allproducts = json.load(f)

        self.renderproducts()
        
        self.lang_selection_combobox.append("de", "Österreich/GER")
        for key in settings.langs:
            self.lang_selection_combobox.append(key, settings.langs[key])
        self.lang_selection_combobox.set_active(0)


        self.add(box)
        self.show_all()
    
    def renderproducts(self):
        self.grid = Gtk.Grid()
        
        self.grid.set_column_spacing(10)
        self.grid.set_row_spacing(10)

        self.i = 2
        c = 1

        p_sku_leg = Gtk.Label()
        p_sku_leg.set_text("Product")
        p_sku_leg.set_name("legende")
        self.grid.attach(p_sku_leg, c, 1, 1, 1)
        c += 1

        p_html_leg = Gtk.Label()
        p_html_leg.set_text("HTML")
        p_html_leg.set_name("legende")
        self.grid.attach(p_html_leg, c, 1, 1, 1)
        c += 1

        p_generate_leg = Gtk.Label()
        p_generate_leg.set_text("Generate PDFs")
        p_generate_leg.set_name("legende")
        self.grid.attach(p_generate_leg, c, 1, 2, 1)
        c += 2

        p_show_pdf_leg = Gtk.Label()
        p_show_pdf_leg.set_text("Show PDFs")
        p_show_pdf_leg.set_name("legende")
        self.grid.attach(p_show_pdf_leg, c, 1, 2, 1)
        c += 2

        for key in self.allproducts["sku"]:
            p = self.allproducts["sku"][key]
            
            if p["sku"] == "":
                pass
            else:
                c = 1

                # Article
                p_sku = Gtk.Label()
                p_sku.set_text(p["name"])
                p_sku.set_xalign(0)
                self.grid.attach(p_sku, c, self.i, 1, 1)
                
                c += 1
                
                # HTML Edit button

                file = "data/products/{}.html".format(p["sku"])
                if os.path.exists(file):
                    p_html_edit_button = Gtk.Button.new_with_label("Edit")
                    
                else:
                    p_html_edit_button = Gtk.Button.new_with_label("Create")

                self.grid.attach(p_html_edit_button, c, self.i, 1, 1)
                
                p_html_edit_button.connect("clicked",
                    FileEditor,
                    None,
                    file,
                    "html",
                    self)

                c += 1

                # Generate PDF Buttons
                p_make_label_en_button = Gtk.Button()
                p_make_label_en_button.set_label("DE")
                p_make_label_en_button.connect(
                    "clicked", 
                    self.generate_pdf,
                    file, 
                    p["sku"], 
                    False)
                self.grid.attach(p_make_label_en_button, c, self.i, 1, 1)
                c += 1 

                p_make_all_labels_button = Gtk.Button()
                p_make_all_labels_button.set_label("All")
                p_make_all_labels_button.connect(
                    "clicked",
                    self.generate_pdf,
                    file,
                    p["sku"],
                    True
                )
                self.grid.attach(p_make_all_labels_button, c, self.i, 1, 1)
                c += 1

                # Show PDF Buttons
                p_show_pdf_en_button = Gtk.Button()
                p_show_pdf_en_button.set_label("Show")
                p_show_pdf_en_button.connect(
                    "clicked",
                    self.preview_label,
                    p["sku"]
                    )
                self.grid.attach(p_show_pdf_en_button, c, self.i, 1, 1)
                c += 1

                # Print PDF Button
                p_print_pdf_button = Gtk.Button()
                p_print_pdf_button.set_label("Print")
                p_print_pdf_button.connect(
                    "clicked",
                    print_label_on_BP730,
                    p["sku"],
                    1,
                    False,
                    )
                self.grid.attach(p_print_pdf_button, c, self.i, 1, 1)

                
                self.i += 1

        self.window_scrolled.add_with_viewport(self.grid)

    def preview_label(self, widget, sku):
        lang = self.lang_selection_combobox.get_active_id()
        webbrowser.open_new_tab(
            "data/products/labels/{0}/{1}.pdf".format(
                sku,
                lang
            ))

    def generate_pdf(self, widget, file, sku, translate):
        with open("data/products/label.css") as css_file:
            sourceCSS = CSS(string=css_file.read(), font_config=font_config)
        
        with open(file) as html_file:
            sourceHtml = html_file.read()

        if not os.path.exists("data/products/labels/{}".format(sku)):
            os.makedirs("data/products/labels/{}".format(sku))

        # German Label
        doc = HTML(string=sourceHtml, base_url=".")
        doc.write_pdf(
            'data/products/labels/%s/de.pdf' % sku, 
            stylesheets=[sourceCSS], 
            font_config=font_config, 
            presentational_hints=True
            )
        
        if translate is True:
            soup = BeautifulSoup(sourceHtml)
            try:
                soup.find("img", {"class": "barcode"}).decompose()
            except:
                print("No barcode to be removed")
            for div in soup.find_all(None, {"class": "ignore"}):
                div.decompose()

            for lang in settings.langs:
                print(lang)
                sourceHtmltrans = translator.translate_text(
                    parent=parent,
                    contents=[str(soup)],
                    model='projects/shaped-entropy-248808/locations/global/models/general/nmt',
                    mime_type='text/html',  # mime types: text/plain, text/html
                    source_language_code='de',
                    target_language_code=lang)

                for translation in sourceHtmltrans.translations:
                    doc = HTML(
                        string=translation.translated_text, 
                        base_url="."
                        )
                    doc.write_pdf(
                        'data/products/labels/%s/%s.pdf' % (sku, lang), 
                        stylesheets=[self.sourceCSS], 
                        font_config=font_config,
                        presentational_hints=True
                        )

    def on_refresh_products_button_clicked(self, widget):
        os.remove("data/products/products.json")
        retrieve_products()
        self.destroy()
        self.__init__()

    def close(self, *args):
        self.destroy()
        self


class FileEditor(Gtk.Window):
    def __init__(self, widget, event, file, filetype, parentwindow, *args):
        # Main Window
        Gtk.Window.__init__(self, title="Editor")
        self.set_default_size(800, 700)
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation(1))
        self.add(box)

        # Scrolled container for SourceView
        textedit_scrolled = Gtk.ScrolledWindow()
        textedit_scrolled.set_vexpand(1)
        textedit_scrolled.set_hexpand(1)

        # SourceView
        textedit_sourceview = GtkSource.View()

        self.buffer = GtkSource.Buffer()
        if os.path.exists(file):
            with open(file, "r+") as f:
                self.buffer.set_text(f.read())
        else:
            with open(file, "w") as f:
                pass
        self.buffer.set_language(gtk_lang_manager.get_language(filetype))

        textedit_sourceview.set_buffer(self.buffer)
        textedit_scrolled.add_with_viewport(textedit_sourceview)
        box.add(textedit_scrolled)
        
        # Button box
        buttonbar = Gtk.ButtonBox()
        buttonbar.set_orientation(Gtk.Orientation(0))
        buttonbar.set_layout(Gtk.ButtonBoxStyle(4))

        # Buttons
        close_without_save_button = Gtk.Button()
        close_without_save_button.set_label("Close without saving")
        close_without_save_button.connect(
            "clicked",
            self.close,
            0,
            parentwindow)
        buttonbar.add(close_without_save_button)

        close_with_save_button = Gtk.Button()
        close_with_save_button.set_label("Save and Close")
        close_with_save_button.connect(
            "clicked",
            self.close,
            1,
            parentwindow)
        buttonbar.add(close_with_save_button)

        box.add(buttonbar)

        self.show_all()

        self.file = file
        

    def close(self, widget, save, parentwindow):

        if save == 0:
            self.destroy()
        else:
            with open(self.file, "w") as file:
                self.text = self.buffer.get_text(self.buffer.get_start_iter(),
                                self.buffer.get_end_iter(),
                                True)
                file.write(self.text)
            self.destroy()
        parentwindow.present()


class ReminderEmailWindow(Gtk.Window):
    def __init__(self, widget, order, emailtype, parentwindow):
        self.order = order
        self.emailtype = emailtype



        # Main Window
        Gtk.Window.__init__(
            self, 
            title=order["billing"]["last_name"] + " " + order["billing"]["first_name"] + " Erinnerungsmail")
        self.set_default_size(1280, 800)
        box = Gtk.Box()
        box.set_orientation(Gtk.Orientation(1))
        self.add(box)

        # Scrolled container for SourceView
        textedit_scrolled = Gtk.ScrolledWindow()
        textedit_scrolled.set_vexpand(1)
        textedit_scrolled.set_hexpand(1)
        textedit_scrolled.set_policy(1, 0)

        # SourceView
        textedit_sourceview = GtkSource.View()
        textedit_sourceview.set_wrap_mode(0)

        self.buffer = GtkSource.Buffer()

        self.buffer.set_language(gtk_lang_manager.get_language("html"))

        textedit_sourceview.set_buffer(self.buffer)
        textedit_scrolled.add_with_viewport(textedit_sourceview)
        box.add(textedit_scrolled)
        
        # Button box
        buttonbar = Gtk.ButtonBox()
        buttonbar.set_orientation(Gtk.Orientation(0))
        buttonbar.set_layout(Gtk.ButtonBoxStyle(4))

        # Buttons
        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancel")
        cancel_button.connect("clicked",
                                    self.close,
                                    parentwindow)
        buttonbar.add(cancel_button)

        send_button = Gtk.Button()
        send_button.set_label("Send")
        send_button.connect("clicked",
                                self.send,
                                order,
                                parentwindow)
        buttonbar.add(send_button)

        box.add(buttonbar)

        self.show_all()

        self.populate(order, emailtype)
    
    def populate(self, order, emailtype):
        date_ = datetime.datetime.fromisoformat(order["date_created"])

        if emailtype == "reminder":
            
            ordered_items = ""
            for item in order["line_items"]:
                ordered_items += f'\n<li>{item["quantity"]}x {item["name"]}</li>'

            if order["website"] == "https://www.fermentationculture.eu":
                text = (
                    f'<p>Hi {order["billing"]["first_name"]},</p>\n\n'
                    f'<p>On the {date_.day}.{date_.month}.{date_.year} you submitted an order in our shop \nat fermentationculture.eu, and selected up-front payment.<p>\n\n'
                    f'''<p>Here's what you ordered for your review:<p><ul>{ordered_items}</ul></p>\n\n'''
                    f'''We haven't received your money yet. If you are still interesed, please pay <strong>{order["total"]}€</strong> to:\n'''
                    f'<p><strong>IBAN:</strong> FI06 7997 7995 3104 84 <br><strong>BIC:</strong> HOLVFIHH </p>\n'
                    f'<p>Please put "FC-{order["number"]}" into the payment text.</p>\n\n'
                    f'''<p>If you prefer to pay with credit card, let us know and we'll send you a payment link.\n\n'''
                    f'''<p>Looking forward to hearing from you,<br>\nViktor<br>\nfermentationculture.eu\n'''
                )
            elif order["website"] == "https://www.luvifermente.eu":
                text = (
                    f'<p>Hallo {order["billing"]["first_name"]},</p>\n\n'
                    f'<p>Du hast am {date_.day}.{date_.month}.{date_.year} bei uns auf luvifermente.eu \neine Bestellung aufgegeben und ausgewählt per Vorkasse zu zahlen.</p>\n\n'
                    f'''<p>Du hast dir folgendes bestellt:<p><ul>{ordered_items}</ul></p>\n\n'''
                    f'''<p>Leider haben wir deine Zahlung noch nicht empfangen. \nWenn du an deiner Bestellung noch interessiert bist, zahle bitte <strong>{order["total"]}€</strong> an:\n'''
                    f'<p><strong>IBAN:</strong> FI06 7997 7995 3104 84 <br><strong>BIC:</strong> HOLVFIHH </p>\n'
                    f'<p>Gib bitte "LF-{order["number"]}" in den Überweisungstext.</p>\n\n'
                    f'''<p>Falls du lieber mit Kreditkarte oder Sofortüberweisung zahlen möchtest, lass es uns wissen, und wir schicken dir einen Zahlungslink.\n\n'''
                    f'''<p>Viele Grüße,<br>\nViktor, Christine und Lukas<br>LUVI Fermente\n'''
                )
            
            self.buffer.set_text(text)

    def send(self, widget, order, parentwindow):
        if order["website"] == "https://www.fermentationculture.eu":
            from_ = "fermentationculture.eu <office@fermentationculture.eu>"
            settings.send_email(
                from_, 
                order["billing"]["email"], 
                "Your order at fermentationculture.eu", 
                self.buffer.get_text(
                    self.buffer.get_start_iter(),
                    self.buffer.get_end_iter(),
                    True))
        elif order["website"] == "https://www.luvifermente.eu":
            from_ = "LUVI Fermente <office@luvifermente.eu>"
            settings.send_email(
                from_, 
                order["billing"]["email"], 
                "Deine Bestellung bei LUVI Fermente", 
                self.buffer.get_text(
                    self.buffer.get_start_iter(),
                    self.buffer.get_end_iter(),
                    True))
        
        self.close(None, parentwindow)


    def close(self, widget, parentwindow):
        self.destroy()
        parentwindow.present()
    

class ProductsSummaryPopup(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self, 0)
        self.set_position(Gtk.WindowPosition(3))
        self.set_title("Benötigte Artikel")
        
        box = self.get_children()[0]
        
        global filtered_orders
        
        self.to_get = Counter()

        for i in range(len(filtered_orders)):
            for item in filtered_orders[i]["line_items"]:
                if len(item["sku"]) == 0:
                    self.to_get[item["name"]] += item["quantity"]
                else:
                    self.to_get[item["sku"]] += item["quantity"]

        text = ""
        for name in self.to_get:
            text += str(self.to_get[name]) + "x " + name + "\n"


        buffer = Gtk.TextBuffer()
        buffer.set_text(text)

        text_view = Gtk.TextView()
        text_view.set_editable(0)
        text_view.set_buffer(buffer)
        text_view.set_name("ProductsSummary")

        box.add(text_view)

        print_button = Gtk.Button()
        print_button.set_label("Drucken")
        print_button.connect(
            "clicked",
            self.print_list
        )
        box.add(print_button)

        self.show_all()

    def print_list(self, *args):
        to_get = Counter()
        for i in range(len(filtered_orders)):
            for item in filtered_orders[i]["line_items"]:
                if len(item["sku"]) > 0:
                    to_get[item["sku"]] += item["quantity"]
        html = "<html><head>"
        for item in to_get:
            html += str(to_get[item]) + "x " + item + "<br>"
        html += "</head></html>"

        sourceCSS = CSS(string="""
                                @page { size: 62mm 50mm; margin: 1mm 1mm 1mm 1mm; } 
                                body {
                                    font-family: Verdana;
                                    font-size: 10px;
                                    }
                                """, font_config=font_config)

        doc = HTML(string=html, base_url=".")

        file = "temp/einkaufsliste.pdf"
        
        doc.write_pdf(
            file,
            stylesheets=[sourceCSS], 
            font_config=font_config
            )

        pdf = os.path.abspath(file)
        #webbrowser.open_new_tab(file)
        conn.printFile(settings.printers["labels_klein"], pdf, "Einkaufsliste", {"media": "62mmx50mm"})


class ConfirmWindow(Gtk.Dialog):
    def __init__(self, widget, question_str=str, function=object, *args, **kwargs):
        Gtk.Dialog.__init__(self, 0)
        self.connect(
            "key-press-event", 
            self.on_key_press_event,
            )

        self.args = args
        self.kwargs = kwargs

        self.set_position(Gtk.WindowPosition(3))
        self.set_title("")
        self.set_default_size(600,300)

        self.function = function

        self.question_str = question_str

        containerbox = self.get_children()[0]

        question = Gtk.Label()
        question.set_markup(self.question_str)
        question.set_name("dialogtext")

        yes_button = Gtk.Button()
        yes_button.set_label("<u>J</u>a")
        yes_button.get_child().set_use_markup(True)
        yes_button.set_name("big_button")
        yes_button.connect(
            "clicked", 
            self.do_the_thing)

        no_button = Gtk.Button()
        no_button.set_label("<u>N</u>ein")
        no_button.get_child().set_use_markup(True)
        no_button.set_name("big_button")
        no_button.connect(
            "clicked", 
            self.close_window)

        buttonbox = Gtk.Box()
        
        buttonbox.pack_end(yes_button, 0, 1, 1)
        buttonbox.pack_start(no_button, 0, 1, 1)

        containerbox.set_orientation(Gtk.Orientation.VERTICAL)
        containerbox.pack_start(question, 1, 1, 1)
        containerbox.pack_end(buttonbox, 0, 0, 0)

        self.show_all()

    def do_the_thing(self, widget):
        self.close_window(None)
        self.function(*self.args, **self.kwargs)
        

    def on_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_Return:
            self.do_the_thing(None)
        elif event.keyval == Gdk.KEY_Escape:
            self.close_window(None)
        elif event.keyval == Gdk.KEY_j:
            self.do_the_thing(None)
        elif event.keyval == Gdk.KEY_n:
            self.close_window(None)

    def close_window(self, widget):
        self.destroy()


class Handler:
    # Main Window:
    def onDestroy(self, *args):
        with open("data/orders.json", "w") as file:
            file.write(json.dumps(mainwindow.all_orders))
        
        files = glob("temp/*")
        for f in files:
            os.remove(f)

        Gtk.main_quit()
        exit()
    
    def einkaufsliste_clicked(self, button):
        #Einkaufsliste()
        ProductsSummaryPopup()

    def adresslabels_clicked(self, button):
        print_addresslabels("??", mainwindow.toggled_orders)

    def on_searchentry_changed(self, widget):
        mainwindow.search_orders()

    def on_end_of_day_button_clicked(self, widget):
        ConfirmWindow(
            None, 
            "Tagesabschluss durchführen?",
            post.end_of_day
            )

    def on_products_window_button_clicked(self, button):
        products_window = ProductsWindow()

    # Product Pop Up windows
    def productpopup_focus_out(self):
        pass
        
    # Textedit window:
    def textedit_close_wo_saving_clicked(self, button):
        textedit.hide()

    def textedit_close_w_saving_clicked(self, button):
        textedit_save()
        textedit.hide()

    def textedit_delete_event(self, button, window):
        textedit.hide()
        return True


builder.connect_signals(Handler())

retrieve_products()

gtk_style()

window.set_title("OrderApp")
window.set_wmclass("OrderApp", "OrderApp")


mainwindow = MainWindow()


window.maximize()

window.show_all()
Gtk.main()

