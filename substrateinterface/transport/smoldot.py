import json
import os
import pkgutil
import time

try:
    from py_smoldot_light import SmoldotClient
except ImportError as exc:
    SmoldotClient = None
    _smoldot_import_error = exc

from .base import TransportBase, list_remove_iter
from ..exceptions import SubstrateRequestException, ConfigurationError


class SmoldotTransport(TransportBase):
    def __init__(self, chainspec, debug_fn=None):
        super().__init__(debug_fn=debug_fn)
        if SmoldotClient is None:
            raise ConfigurationError(
                "py_smoldot_light is required for Smoldot transport"
            ) from _smoldot_import_error
        self.chainspec = chainspec
        self.client = SmoldotClient()
        self.chain_id = self.client.add_chain(self._load_chainspec(chainspec))
        self.__rpc_message_queue = []

    @staticmethod
    def _load_chainspec(path):
        if not isinstance(path, str):
            raise ConfigurationError("chainspec must be a path or preset name string")

        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as chainspec_file:
                return chainspec_file.read()

        name = os.path.basename(path)
        if name.lower().endswith(".json"):
            name = name[:-5]

        preset_name = name.lower()
        if preset_name in ("polkadot", "kusama"):
            resource_path = f"data/chainspecs/{preset_name}.json"
            data = pkgutil.get_data("substrateinterface", resource_path)
            if data is None:
                raise ConfigurationError(
                    f"Unable to load packaged chainspec '{preset_name}'"
                )
            return data.decode("utf-8")

        raise ConfigurationError(
            f"Unable to resolve chainspec '{path}' (file not found or unknown preset)"
        )

    def _drain_messages(self, max_messages=10):
        responses = self.client.drain_responses(self.chain_id, max=max_messages)
        for message in responses:
            self.__rpc_message_queue.append(json.loads(message))
        return len(responses)

    def rpc_request(self, payload, result_handler=None):
        request_id = payload['id']
        self.client.json_rpc_request(self.chain_id, json.dumps(payload))

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
                        self.debug_message(f"Smoldot subscription [{subscription_id}] created")
                    else:
                        json_body = message

            for message, remove_message in list_remove_iter(self.__rpc_message_queue):
                if 'params' in message and message['params']['subscription'] == subscription_id:
                    remove_message()

                    self.debug_message(f"Smoldot result [{subscription_id} #{update_nr}]: {message}")

                    callback_result = result_handler(message, update_nr, subscription_id)
                    if callback_result is not None:
                        json_body = callback_result

                    update_nr += 1

            if json_body is None:
                drained = self._drain_messages()
                if drained == 0:
                    time.sleep(0.01)

        return json_body
