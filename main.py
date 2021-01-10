from bs4 import BeautifulSoup as Soup
import pandas as pd
import requests
import re
import time
import random
import locale
import pprint
import os
import sys
import datetime
import webbrowser
from tqdm.auto import tqdm
from pathlib import Path

locale.setlocale(locale.LC_ALL, '')


def get_data(ids, large_only=True, include_fleet_carrier=False, max_quantity=25000, max_request_wait=3, near_sol=True, **kwargs):
    commodity_data = []
    # sellmax, buymin
    pbar = tqdm(ids)
    commodity_map = get_commodity_map()
    for commodity_id in pbar:
        pbar.set_description(
            f"Downloading and formatting data for {commodity_map[int(commodity_id)]}")
        # https://inara.cz/ajaxaction.php?act=goodsdata&refname=sell&refid=10269&refid2=0
        buy_url = f'https://inara.cz/ajaxaction.php?act=goodsdata&refname=buymin&refid={commodity_id}&refid2=0'
        sell_url = f'https://inara.cz/ajaxaction.php?act=goodsdata&refname=sellmax&refid={commodity_id}&refid2=0'

        buy_r = requests.get(buy_url)
        # this parses all the tables in webpages to a list
        try:
            buy_df_list = pd.read_html(buy_r.text)
        except ValueError:
            continue
        buy_df = buy_df_list[0]
        buy_df.head()

        sell_r = requests.get(sell_url)
        # this parses all the tables in webpages to a list
        try:
            sell_df_list = pd.read_html(sell_r.text)
        except ValueError:
            continue
        sell_df = sell_df_list[0]
        sell_df.head()

        buyers = []
        sellers = []

        for index, row in buy_df.iterrows():
            price = row['Buy price']
            price = price[:-3]
            row_data = {
                'price': price.replace(',', ''),
                'quantity': row['QTY'],
                'updated': row['Updated'],
                'range': row['OPR'],
            }
            if (large_only and row['Pad'] != 'L'):
                continue
            if (not include_fleet_carrier) and is_fleet_carrier(row['Location']):
                continue
            if near_sol:
                # Get the distance from Sol
                dist = row['Distance']
                split = dist.split(' ')
                dist = split[0]
                dist = dist.translate({ord(i): None for i in ','})
                if float(dist) > 500:
                    continue
            location = row['Location']
            split_location = location.split('|')
            station = split_location[0]
            station = station[:-1]
            system = split_location[1]
            # Remove the snip icon at the end of the line
            system_split = system.split(u"\u2702")
            system = system_split[0]
            row_data['location'] = {
                'station': station,
                'system': system,
                'pad_size': row['Pad'],
                'carrier': is_fleet_carrier(location),
                'station distance': row['St dist'],
                'system distance': row['Distance']
            }
            buyers.append(row_data)
        for index, row in sell_df.iterrows():
            price = row['Sell price']
            price = price[:-3]
            row_data = {
                'price': price.replace(',', ''),
                'quantity': row['QTY'],
                'updated': row['Updated'],
                'range': row['OPR'],
            }
            if (large_only and row['Pad'] != 'L'):
                continue
            if (not include_fleet_carrier) and is_fleet_carrier(row['Location']):
                continue
            if near_sol:
                # Get the distance from Sol
                dist = row['Distance']
                split = dist.split(' ')
                dist = split[0]
                dist = dist.translate({ord(i): None for i in ','})
                if float(dist) > 500:
                    continue
            location = row['Location']
            # ✂︎
            # Ac/Dc Party Carrier (KHM-86M) | Robigo
            split_location = location.split('|')
            station = split_location[0]
            # Remove the snip icon at the end of the line
            station = station[:-1]
            system = split_location[1]
            system_split = system.split(u"\u2702")
            system = system_split[0]
            row_data['location'] = {
                'station': station,
                'system': system,
                'pad_size': row['Pad'],
                'carrier': is_fleet_carrier(location),
                'station distance': row['St dist'],
                'system distance': row['Distance']
            }
            sellers.append(row_data)

        commodity_data.append({
            'commodity_id': commodity_id,
            'buys': buyers,
            'sells': sellers
        })

        # wait before next iteration to avoid spamming webserver
        if max_request_wait != 0:
            time.sleep(random.random() * random.randint(1, max_request_wait))
    return commodity_data


def get_profit(commodity):
    return commodity['best_profit']


def process_data(data, max_quantity, **kwargs):
    processed = []
    pbar = tqdm(data)
    commodity_map = get_commodity_map()
    for commodity in pbar:
        pbar.set_description(
            f"Processing {commodity_map[int(commodity['commodity_id'])]}")
        max_profit = 0
        curr_best_sell = None
        curr_best_buy = None
        for sell_choice in commodity['sells']:
            for buy_choice in commodity['buys']:
                available_quantity = min(
                    buy_choice['quantity'], sell_choice['quantity'], max_quantity)
                available_profit = calc_possible_profit(
                    sell_choice, available_quantity) - calc_possible_profit(buy_choice, available_quantity)
                if (available_profit > max_profit):
                    max_profit = available_profit
                    curr_best_sell = sell_choice
                    curr_best_buy = buy_choice
        best_profit = max_profit
        commodity['best_sell'] = curr_best_sell
        commodity['best_buy'] = curr_best_buy
        commodity['best_profit'] = best_profit
        if not (commodity['best_sell'] == None or commodity['best_buy'] == None):
            processed.append(commodity)
    ordered_best = sorted(processed, key=get_profit)
    ordered_best.reverse()
    return ordered_best


def get_usable_quantity(max_quantity, quantity):
    if max_quantity < quantity:
        return max_quantity
    return quantity


def display_data(data, num, commodity_map):
    output = ""
    for index, commodity in enumerate(data):
        if index >= num:
            break
        output += print_commodity(commodity, commodity_map)
    return output


def format_buys(commodity):
    output = ""
    output += f"Best:\n\t\t\t{format_location(commodity['best_buy'])}"
    if len(commodity['buys']) > 0:
        output += "\tOther buy locations:\n"
        counter = 0
        while counter < len(commodity['buys']) and counter < 3:
            output += f"\t\t\t{format_location(commodity['buys'][counter])}"
            counter += 1
    return output


def format_sells(commodity):
    output = ""
    output += f"Best:\n\t\t\t{format_location(commodity['best_sell'])}"
    sells = commodity['sells']
    if len(sells) > 0:
        output += "\tOther sell locations:\n"
        counter = 0
        while counter < len(sells) and counter < 3:
            output += f"\t\t\t{format_location(commodity['sells'][counter])}"
            counter += 1
    return output


def format_location(data):
    station = f"{data['location']['station']} ({data['location']['station distance']})"
    system = f"{data['location']['system']} ({data['location']['system distance']})"
    pad = f"Pad: {data['location']['pad_size']}"
    carrier = f"Carrier: {data['location']['carrier']}"
    quantity = f"Qty: {data['quantity']}"
    price = f"Price: {data['price']}"
    cost = f"Max Cost: {(int(data['quantity']) * int(data['price'])):n}"
    updated = f"Updated: {data['updated']}"
    return f"{station} \t\t | \t {system} \t\t {pad} \t {carrier} \t\t\t {quantity} \t {price} \t {cost} \t {updated}\n"


def print_commodity(commodity, commodity_map):
    commodity_str = f"""
    =========================[ {commodity_map[int(commodity['commodity_id'])]} ]=========================
    Available Profit: \t{int(commodity['best_profit']):n} Cr
    Profit Per Ton: \t{int(commodity['best_sell']['price']) - int(commodity['best_buy']['price'])} Cr/T
    Buy:
        {format_buys(commodity)}
    Sell:
        {format_sells(commodity)}
    """
    print(commodity_str)
    return commodity_str


def calc_better_buy(data, data2, max_quantity):
    '''
        Is data a better commodity to buy than data2
    '''
    if data2['quantity'] == -1 or data2['price'] == -1:         # Anything is a better buy than the default of -1
        return True
    return data['quantity'] >= data2['quantity'] and calc_possible_profit(data, max_quantity) <= calc_possible_profit(data2, max_quantity)


def calc_better_sell(data, data2, max_quantity):
    '''
        Is data2 a better commodity to sell than data
    '''
    if data2['quantity'] == -1 or data2['price'] == -1:
        return True
    return calc_possible_profit(data, max_quantity) >= calc_possible_profit(data2, max_quantity)


def is_fleet_carrier(location):
    regex = r'([\d\w]{3}-[\d\w]{3})'
    return bool(re.search(regex, location))


def calc_possible_profit(data, max_quantity):
    return float(data['price']) * get_usable_quantity(max_quantity, int(data['quantity']))


def get_commodities():
    url = 'https://inara.cz/galaxy-commodities/'
    r = requests.get(url)
    text = r.text
    soup = Soup(text, 'html.parser')
    attrs = {
        'href': re.compile(r'/galaxy-commodity/')
    }
    links = soup.find_all('a', attrs=attrs)
    commodity_ids = []
    for link in links:
        href = link.get('href')
        split = href.split('/')
        commodity_ids.append(int(split[2]))
    return commodity_ids


def get_commodity_map():
    if getattr(sys, 'frozen', False):
        CurrentPath = sys._MEIPASS
    # If it's not use the path we're on now
    else:
        CurrentPath = os.path.dirname(__file__)
    filepath = os.path.join(CurrentPath, "format.html")
    second_soup = Soup(open(filepath), "html.parser")
    search_commodities = second_soup.find(
        'select', {'name': 'searchcommodity'})
    commodity_map = {}
    for option in search_commodities.find_all('option'):
        commodity_id = option['value']
        span = option.find('span')
        commodity_name = span.string
        commodity_map[int(commodity_id)] = commodity_name
    return commodity_map


def get_options():
    options = {
        'large_only': True,
        'include_fleet_carrier': False,
        'max_quantity': 25000,
        'max_request_wait': 3,
        'num_results_to_display': 5,
        'log_file': True,
        'near_sol': True,
    }
    large_input = input("Restrict landing pad size to large: [Y/n]\t")
    if (large_input.lower() == 'n'):
        options['large_only'] = False
    carrier_input = input("Include fleet carriers: [y/N]\t")
    if (carrier_input.lower() == 'y'):
        options['include_fleet_carrier']: True
    quantity_input = input(
        "What is the maximum amount of cargo units you can hold: ( > 0) [17800]\t")
    if len(quantity_input) > 0:
        try:
            num_quantity = int(quantity_input)
            if num_quantity <= 0:
                print("Input must be greater than zero. Using default value.")
            options['max_quantity'] = num_quantity
        except ValueError:
            print("Error parsing input. Using default value.")
    wait_input = input(
        "What is the maximum amount of seconds to wait per commodity: (0-10) [3]\t")
    if len(wait_input) > 0:
        try:
            wait_period = int(wait_input)
            if not 0 <= wait_period <= 10:
                print("Number outside of allowed range. Using default value.")
            else:
                options['max_request_wait'] = wait_period
        except ValueError:
            print("Error parsing input. Using default value.")
    results_input = input(
        "Maximum number of results to display: ( > 0) [5]\t ")
    if len(results_input) > 0:
        try:
            num_results = int(results_input)
            if (num_results < 0):
                print("Number outside of allowed range. Using default value.")
            else:
                options['num_results_to_display'] = num_results
        except ValueError:
            print("Error parsing input. Using default value.")
    sol_input = input("Restrict to systems within 500 Ly of Sol? [Y/n]\t")
    if (sol_input.lower() == 'n'):
        options['near_sol'] = False
    log_input = input(
        "Create log file? Directory will be created if it does not exist: [Y/n]\t")
    if log_input.lower() == 'n':
        options['log_file'] = False
    else:
        print(
            f"Saving log file to {os.path.join(os.path.expanduser('~'), 'Documents', 'ArrowTrader')}")
    return options


def run():
    options = get_options()
    get_commodity_map()
    ids = get_commodities()
    data = get_data(ids, **options)
    ordered = process_data(data, **options)
    commodity_map = get_commodity_map()
    output = display_data(
        ordered, options['num_results_to_display'], commodity_map)
    if options['log_file']:
        path = os.path.expanduser('~')
        path = os.path.join(path, 'Documents')
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except OSError:
                print(f"Unable to create directory {path}")
        path = os.path.join(path, 'ArrowTrader')
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except OSError:
                print(f"Unable to create directory {path}")
        latest_file = os.path.join(path, 'latest.log')
        file_path = Path(latest_file)
        if file_path.exists():
            # Rename the old log file
            modification_time = datetime.datetime.fromtimestamp(
                file_path.stat().st_mtime)
            new_name = f"ArrowTrader-{modification_time.isoformat(timespec='seconds')}.log"
            new_name = new_name.replace(':', '-')
            new_file_path = os.path.join(path, new_name)
            try:
                os.rename(latest_file, new_file_path)
            except OSError as error:
                print("Unable to rename previous log file")
                print(error)
        with open(file_path, 'w') as f:
            f.write(output)
        webbrowser.open(file_path)


if __name__ == '__main__':
    run()
