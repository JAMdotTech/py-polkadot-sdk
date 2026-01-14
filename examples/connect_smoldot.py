from time import sleep

from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(chainspec="polkadot_asset_hub", relay_chainspecs=["polkadot"])
# substrate = SubstrateInterface(chainspec="ksmcc3_asset_hub", relay_chainspecs=["ksmcc3"])

def on_new_head(message, update_nr, subscription_id):
    print(f"New head [{subscription_id} #{update_nr}]: {message}")


print(f"Connected to chain {substrate.chain}")
substrate.rpc_request("chain_subscribeNewHeads", [], result_handler=on_new_head)

while True:
    sleep(0.5)
