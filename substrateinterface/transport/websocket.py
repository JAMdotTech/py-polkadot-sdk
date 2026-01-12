import json

from websocket import create_connection, WebSocketConnectionClosedException

from .base import TransportBase, list_remove_iter
from ..exceptions import SubstrateRequestException


class WebsocketTransport(TransportBase):
    def __init__(self, url=None, websocket=None, ws_options=None, auto_reconnect=True, debug_fn=None, on_connect=None):
        super().__init__(debug_fn=debug_fn)
        self.url = url
        self.websocket = websocket
        self.ws_options = ws_options or {}
        self.auto_reconnect = auto_reconnect
        self.on_connect = on_connect
        self.__rpc_message_queue = []

        if self.websocket and callable(self.on_connect):
            self.on_connect(self.websocket)

        if self.url and not self.websocket:
            self.connect()

    def connect(self):
        if self.url:
            self.debug_message("Connecting to {} ...".format(self.url))
            self.websocket = create_connection(
                self.url,
                **self.ws_options
            )
            if callable(self.on_connect):
                self.on_connect(self.websocket)

    def close(self):
        if self.websocket:
            self.debug_message("Closing websocket connection")
            self.websocket.close()

    def rpc_request(self, payload, result_handler=None):
        request_id = payload['id']

        try:
            self.websocket.send(json.dumps(payload))
        except WebSocketConnectionClosedException:
            if self.auto_reconnect and self.url:
                self.debug_message("Connection Closed; Trying to reconnecting...")
                self.connect()
                return self.rpc_request(payload=payload, result_handler=result_handler)
            raise

        update_nr = 0
        json_body = None
        subscription_id = None

        while json_body is None:
            for message, remove_message in list_remove_iter(self.__rpc_message_queue):
                if 'id' in message and message['id'] == request_id:
                    remove_message()

                    if 'error' in message:
                        raise SubstrateRequestException(message['error'])

                    if callable(result_handler):
                        subscription_id = message['result']
                        self.debug_message(f"Websocket subscription [{subscription_id}] created")
                    else:
                        json_body = message

            for message, remove_message in list_remove_iter(self.__rpc_message_queue):
                if 'params' in message and message['params']['subscription'] == subscription_id:
                    remove_message()

                    self.debug_message(f"Websocket result [{subscription_id} #{update_nr}]: {message}")

                    callback_result = result_handler(message, update_nr, subscription_id)
                    if callback_result is not None:
                        json_body = callback_result

                    update_nr += 1

            if json_body is None:
                self.__rpc_message_queue.append(json.loads(self.websocket.recv()))

        return json_body
