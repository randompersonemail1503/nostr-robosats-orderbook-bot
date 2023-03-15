import math
import ssl
import pickle
import os
import time
import logging
from nostr.event import Event
from nostr.relay_manager import RelayManager
from nostr.key import PrivateKey


class ConnectToNostrToPublish:
    def __init__(self, list_of_relays_to_add: list, order_text_to_publish: str):
        """
        Initializes ConnectToNostrToPublish class with provided private key,
        list of relays to connect to, and the order text to publish.

        Args:
            list_of_relays_to_add (list): A list of relay nodes to connect to.
            order_text_to_publish (str): A string representing the text of the order to
                publish.
        """
        self.list_of_relays_to_add = list_of_relays_to_add
        self.order_text_to_publish = order_text_to_publish

    def get_private_key(self):
        if os.path.isfile("./config/sec.pickle"):
            with open("./config/sec.pickle", "rb") as f:
                # deserialize the object and load it into memory
                self.private_key = pickle.load(f)
        else:
            self.private_key = PrivateKey()
            # open a file in binary mode
            with open("./config/sec.pickle", "wb") as f:
                # serialize the object and write it to the file
                pickle.dump(self.private_key, f)
            with open("./config/pv_key.txt", "w") as fp:
                # serialize the object and write it to the file
                fp.write(f"{self.private_key.bech32()}\n")
                fp.write(f"{self.private_key.public_key.bech32()}\n")

    def relay_manager_for_connection(self):
        """
        Establishes connections with the relays specified in the
        list_of_relays_to_add.
        """

        logging.info("Trying to establish connections with relay")
        self.relay_manager = RelayManager()
        # adding relays to the manager
        for relay in self.list_of_relays_to_add:
            self.relay_manager.add_relay(relay)
        self.relay_manager.open_connections(
            {"cert_reqs": ssl.CERT_NONE}
        )  # NOTE: This disables ssl certificate verification
        time.sleep(1.25)  # allow the connections to open

        # while self.relay_manager.message_pool.has_notices():
        #     notice_msg = self.relay_manager.message_pool.get_notice()
        #     print(notice_msg.content)

    def add_order_with_private_key(self):
        """
        Signs and publishes the order with the provided private key.
        """
        logging.info("Starting the relay manager")
        self.relay_manager_for_connection()
        logging.info("Finshed connecting to relays")

        event = Event(self.private_key.public_key.hex(), self.order_text_to_publish)
        self.private_key.sign_event(event)

        max_tries = 5
        for try_num in range(1, max_tries + 1):
            try:
                self.relay_manager.publish_event(event)
                time.sleep(1)  # allow the messages to send
                self.relay_manager.close_connections()
                logging.info("Finished publishing the order.")
                break
            except:
                logging.info(
                    "Publish attempt failed, retrying in %d seconds..."
                    % self._get_retry_delay(try_num)
                )
                self.relay_manager.close_connections()
                time.sleep(self._get_retry_delay(try_num))

    def _get_retry_delay(self, try_num):
        base_delay = 30  # start with a 30-second delay
        return math.ceil(base_delay * (2 ** (try_num - 1)))

    def run(self):
        """
        Establishes connections with the specified relays and
        publishes the order
        with the provided private key.
        """
        self.get_private_key()
        logging.info("Now trying to publish the event")
        self.add_order_with_private_key()
