import json
import logging
import sys
import time
import os
import requests

import config
import currencies
from nostr_bot import ConnectToNostrToPublish

logging.basicConfig(filename='debug.log',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info('Bot Starting...')


def create_order(book_order):
    # TODO: FIX amount could have decimals
    if book_order['has_range']:
        amount = f"{int(float(book_order['min_amount'])):,}-{int(float(book_order['max_amount'])):,}"
    else:
        amount = f"{int(float(book_order['amount'])):,}"

    currency = currencies.CURRENCIES[str(book_order['currency'])]
    flag = currencies.get_flag(currency)

    order = f"""
Order on Robosats
Type: {config.ROBOSATS_ORDER_TYPE[book_order['type']]}
Amount: {amount}
Currency: {currency} {flag}
Payment method: {book_order['payment_method']} 
Premium: {book_order['premium']}%
Price: {int(float(book_order['price'])):,}
LINK (TOR): http://robosats6tkf3eva7x2voqso3a5wcorsnw34jveyxfqi2fu7oyheasid.onion/robot/ZlijUfOjQYs
    """
    return order



def load_persistence_file():
    # Load persistence file. It includes already posted order ids
    try:
        if os.path.isfile("config.PERSISTENCE_FILE"):
            with open(config.PERSISTENCE_FILE, 'r') as f:
                published_orders = json.load(f)
        else:
            with open(config.PERSISTENCE_FILE, 'w') as f:
                json.dump([], f)
                published_orders = []
    except FileNotFoundError:
        logger.info("Persistence file not found")
        published_orders = []

    return published_orders

def main():
    list_of_relays_to_add = [
            "wss://nostr-pub.wellorder.net",
            "wss://relay.damus.io",
            "wss://relay.snort.social",
            "wss://nostr.mom",
            "wss://nostr.wine",
        ]
    published_orders = load_persistence_file()

    # Main loop where we will poll Robosats for the orderbook and order new orders
    while True:
        logger.info('Fetching Robosats order book')
        order_book = None
        while not order_book:
            try:
                order_book = requests.get(config.ROBOSATS_API_ORDERBOOK, proxies=config.PROXIES).json()
            except requests.RequestException:
                logger.exception("Error retrieving orderbook. Waiting 10 secs to retry")
                time.sleep(2)

        for order in order_book:
            if order['id'] not in published_orders: 
                if order["currency"] != 1000:
                    message = create_order(order)
                    publisher = ConnectToNostrToPublish(list_of_relays_to_add, message)
                    publisher.run()
                    published_orders.append(order['id'])
                    time.sleep(10)
                else:
                    continue
            else:
                continue

        with open(config.PERSISTENCE_FILE, 'w') as f:
            json.dump(published_orders, f)

        logger.info(f'Job done. Sleeping for {config.POLL_INTERVAL} seconds')
        time.sleep(config.POLL_INTERVAL)


if __name__ == '__main__':
    while True:
        try:
            # main only returns in case of an unhandled exception
            main()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt. Quitting")
            sys.exit(0)
        except:
            logger.exception('Catched unexpected exception. Waiting 30 seconds to retry')
            time.sleep(30)
