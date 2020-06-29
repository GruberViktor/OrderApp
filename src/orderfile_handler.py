__docformat__ = 'restructuredtext'
from concurrent import futures
import os
import json
import dateutil
from requests.exceptions import ReadTimeout
import time
import threading
from itertools import combinations
from collections import Counter
import datetime

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, GtkSource

from shops import shops
import settings
import __main__ as m


all_orders = []


class get_all_orders():
    def __init__(self, widget, shops: list, *args, **kwargs):
        """
        Gets all available orders from a shop and saves them in a json file. 
        Every order object gets a new field called "website", in which the URL
        to the shop is saved.

        Parameters:

        - `shops`: A list of woocommerce API objects is expected.
        """
        self.orders = []

        for shop in shops:
            self.shop = shop
            self.response = shops[self.shop].get("orders?per_page=100").headers
            self.pages = int(self.response["X-WP-TotalPages"])
            print(f"Retrieving {self.pages} pages from {shop}")

            self.request_all_orders()
        
        self.save()

    def get_page(self, page):
        while True:
            try:
                response = shops[self.shop].get(f"orders?per_page=100&page={page}")
                print(f"Page {page}: {response}, {len(response.json())} Orders")
                return response.json()

            except ReadTimeout:
                print(f"Page {page} timed out")

    def request_all_orders(self):
        with futures.ThreadPoolExecutor(max_workers=6) as executor:
            self.results = executor.map(self.get_page, range(1, self.pages + 1))

        requested_orders = []
        for result in self.results:
            for i in range(len(result)):
                result[i]["website"] = self.shop
            requested_orders.extend(result)
        #orders = list({v['id']: v for v in requested_orders}.values())

        self.orders.extend(requested_orders)

    def save(self):
        print(f"Retrieved {len(self.orders)} orders")

        with open("data/orders.json", "w") as jsonfile:
            jsonfile.write(json.dumps(self.orders))


def load_all_orders():
    global all_orders
    if os.path.exists("data/orders.json"):
        with open("data/orders.json", "r") as json_file:
            all_orders = json.load(json_file)
            if all_orders[0].get("nth_order") == False:
                count_orders_by_email()
            else:
                print("Orders already counted")

    else:
        get_all_orders(shops)
        with open("data/orders.json", "r") as json_file:
            all_orders = json.load(json_file)


def save_all_orders():
    global all_orders
    with open("data/orders.json", "w") as json_file:
        json_file.write(json.dumps(all_orders))


def count_orders_by_email():
    global all_orders

    number_of_order_by_email = Counter()
    for order in all_orders:
        email = order["billing"]["email"].lower()
        number_of_order_by_email[email] += 1
        order["nth_order"] = number_of_order_by_email[email]
    print(f"Counted {len(all_orders)} orders")


def sort_orders():
    def return_date(order):
        return datetime.datetime.fromisoformat(order["date_created"])
    global all_orders
    all_orders.sort(key=return_date)
    

class GetOrders():
    def __init__(self, event, pages_requested):
        """Retrieves orders from shops. pages_requested should be either int or "All".
        If int, it will download int*100 orders.
        """
        global all_orders
        self.dialog = Gtk.Dialog(
            "",
            m.window,
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
        self.orders_per_shop = {shop: 0 for shop in shops}
        self.orders_total = 0
        if pages_requested == "All":
            for shop in shops:
                response = shops[shop].get("orders?per_page=100").headers
                self.orders_per_shop[shop] = int(response["X-WP-Total"])
                self.orders_total += int(response["X-WP-TotalPages"])
        else:
            for shop in shops:
                self.orders_per_shop[shop] = pages_requested
                self.orders_total += self.orders_per_shop[shop]
        
        self.worker = threading.Thread(target=self.order_retriever)
        self.init_process()        
        self.progress = 0 
        
        
    def get_page(self, args):
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

    def order_retriever(self):
        global all_orders

        args = []
        
        for shop in shops:
            args.extend([(shop, page) for page in range(1, self.orders_per_shop[shop] + 1)])

               
        with futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = executor.map(self.get_page, args) 
        requested_orders = []

        for result in results:
            requested_orders.extend(result)

        orders_to_be_popped = []

        for i in range(len(all_orders)):
            ordernumber = all_orders[i]["number"]
            website = all_orders[i]["website"]

            if any(
                d["number"] == ordernumber 
                and d["website"] == website 
                for d in requested_orders
                ):
                orders_to_be_popped.append(i)

        orders_to_be_popped = sorted(orders_to_be_popped, reverse=True)

        for i in range(len(orders_to_be_popped)):
            all_orders.pop(orders_to_be_popped[i])

        all_orders.extend(requested_orders)
        
        GObject.idle_add(self.stop_process)

    def init_process(self):
        self.running = True
        GObject.timeout_add(200, self.update_progress)
        self.worker.start()

    def update_progress(self):
        if self.running:
            if self.progress + 1 <= self.pages_total:
                self.progresstext.set_text(
                    f"Downloading orders ({(self.progress + 1) * 100} of {self.pages_total * 100})")
            else:
                self.progresstext.set_text("Done")
            self.progressbar.set_fraction(self.progress / self.pages_total)
        return self.running

    def stop_process(self):
        self.running = False
        self.worker.join()
        self.dialog.destroy()
        #load_all_orders()

        sort_orders()
        count_orders_by_email()

        m.mainwindow.update_window()


def refresh_orders():

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
        data = {
            "last_smart_refresh": datetime.datetime.now().replace(microsecond=0).isoformat()
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

    for i in range(len(all_orders)):
        ordernumber = all_orders[i]["number"]
        website = all_orders[i]["website"]

        if any(order["number"] == ordernumber and 
            order["website"] == website for order in new_orders):
            orders_to_be_updated.append(i)

    orders_to_be_updated = sorted(orders_to_be_updated, reverse=True)
 
    for i in range(len(orders_to_be_updated)):
        all_orders.pop(orders_to_be_updated[i])

    all_orders.extend(new_orders)
    
    sort_orders()
    count_orders_by_email()

    m.mainwindow.update_window()


if __name__ == "__main__":
    # oldest_processing_order = shops["https://www.fermentationculture.eu"].get("orders?status=processing&per_page=1&order=asc").json()
    # target_date = oldest_processing_order[0]["date_created"][:-8] + "00:00:00"
    # pages_requested = shops["https://www.fermentationculture.eu"].get(f"orders?per_page=100&after={target_date}&order=asc").headers["X-WP-TotalPages"]
    # orders = shops["https://www.fermentationculture.eu"].get("orders?after=2020-06-24T00:00:00&per_page=100").json()
    # for order in orders:
    #     print(order["number"], order["billing"]["last_name"])
    load_all_orders()
    refresh_orders()