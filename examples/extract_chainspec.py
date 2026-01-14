import json
from pathlib import Path

from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(
    url="wss://kusama-asset-hub-rpc.polkadot.io"
)

response = substrate.rpc_request(method="sync_state_genSyncSpec", params=[False])

output_path = Path("../substrateinterface/data/chainspecs/kusama-assethub.json")
output_path.parent.mkdir(parents=True, exist_ok=True)

result = response.get("result", response)
if isinstance(result, str):
    output_path.write_text(result)
else:
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True))

print(f"Wrote chain spec to {output_path}")

