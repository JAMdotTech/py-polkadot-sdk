from time import sleep

from substrateinterface import SubstrateInterface

chainspec_path = "../substrateinterface/data/chainspecs/polkadot.json"

substrate = SubstrateInterface(chainspec=chainspec_path)


def on_new_head(message, update_nr, subscription_id):
    print(f"New head [{subscription_id} #{update_nr}]: {message}")


value = substrate.rpc_request("system_chain", [])
print(f"Connected to chain {value}")
substrate.rpc_request("chain_subscribeNewHeads", [], result_handler=on_new_head)

while True:
    sleep(0.5)
