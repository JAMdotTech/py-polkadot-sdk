# Python Substrate Interface

[![Build Status](https://github.com/JAMdotTech/py-polkadot-sdk/actions/workflows/unittests.yml/badge.svg?branch=master)](https://github.com/JAMdotTech/py-polkadot-sdk/actions/workflows/unittests.yml)
[![Latest Version](https://img.shields.io/pypi/v/substrate-interface.svg)](https://pypi.org/project/substrate-interface/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/substrate-interface.svg)](https://pypi.org/project/substrate-interface/)
[![License](https://img.shields.io/pypi/l/substrate-interface.svg)](https://github.com/JAMdotTech/py-polkadot-sdk/blob/master/LICENSE)


## Description
This library specializes in interfacing with a [Substrate](https://substrate.io/) node; querying storage, composing extrinsics, 
SCALE encoding/decoding and providing additional convenience methods to deal with the features and metadata of 
the Substrate runtime.

## Documentation

* [Library documentation](https://jamdottech.github.io/py-polkadot-sdk/)
* [Metadata documentation for Polkadot and Kusama ecosystem runtimes](https://jamdottech.github.io/py-polkadot-metadata-docs/)

## Installation

Requires CPython 3.11 or newer. The test matrix covers 3.11 through 3.15.

```bash
python -m pip install substrate-interface
```

Python 3.15 may need to build native dependencies from source. Install the Rust toolchain and enable PyO3's stable ABI when no compatible wheels are available.

```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 python -m pip install substrate-interface
```

## Initialization

Using embedded light client

```python
substrate = SubstrateInterface(chainspec="polkadot_asset_hub", relay_chainspecs=["polkadot"])
```

Using node RPC endpoint 
```python
substrate = SubstrateInterface(url="ws://127.0.0.1:9944")
```

After connecting certain properties like `ss58_format` will be determined automatically by querying the RPC node. At 
the moment this will work for most `MetadataV14` and above runtimes like Polkadot, Kusama, Acala, Moonbeam. For 
older or runtimes under development the `ss58_format` (default 42) and other properties should be set manually. 

## Quick usage

### Balance information of an account
```python
result = substrate.query('System', 'Account', ['F4xQKRUagnSGjFqafyhajLs94e7Vvzvr8ebwYJceKpr8R7T'])
print(result.value['data']['free']) # 635278638077956496
```
### Create balance transfer extrinsic

```python
call = substrate.compose_call(
    call_module='Balances',
    call_function='transfer',
    call_params={
        'dest': '5E9oDs9PjpsBbxXxRE9uMaZZhnBAV38n2ouLB28oecBDdeQo',
        'value': 1 * 10**12
    }
)

keypair = Keypair.create_from_uri('//Alice')
extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)

receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)

print(f"Extrinsic '{receipt.extrinsic_hash}' sent and included in block '{receipt.block_hash}'")
```

## Running tests

Install the test dependencies with `python -m pip install -e '.[test]'` and run `python -m pytest`. To include tests that need live RPC endpoints, run `RUN_LIVE_TESTS=1 python -m pytest`. The endpoint overrides are listed in `test/settings.py`.

## Contact and Support 

For questions, please see the [Substrate StackExchange](https://substrate.stackexchange.com/questions/tagged/python) or [Github Discussions](https://github.com/JAMdotTech/py-polkadot-sdk/discussions).

## License
https://github.com/JAMdotTech/py-polkadot-sdk/blob/master/LICENSE
