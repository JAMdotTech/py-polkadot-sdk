from abc import ABC, abstractmethod


def list_remove_iter(xs: list):
    removed = False

    def remove():
        nonlocal removed
        removed = True

    i = 0
    while i < len(xs):
        removed = False
        yield xs[i], remove
        if removed:
            xs.pop(i)
        else:
            i += 1


class TransportBase(ABC):
    def __init__(self, debug_fn=None):
        self._debug_fn = debug_fn

    def debug_message(self, message: str):
        if callable(self._debug_fn):
            self._debug_fn(message)

    @abstractmethod
    def rpc_request(self, payload, result_handler=None):
        raise NotImplementedError

    def close(self):
        return None
