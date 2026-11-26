# Python Substrate Interface Library
#
# Copyright 2018-2020 Stichting Polkascan (Polkascan Foundation).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import unittest
from unittest.mock import patch

from scalecodec import ScaleBytes

from substrateinterface import SubstrateInterface, Keypair, KeypairType
from substrateinterface.constants import DEV_PHRASE
from substrateinterface.utils.ss58 import ss58_encode
from test import settings
from test.fixtures import RuntimeFixture


@settings.requires_live_node
class KusamaTypeRegistryTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.substrate = SubstrateInterface(
            url=settings.KUSAMA_NODE_URL,
            ss58_format=2,
            type_registry_preset='kusama'
        )

    def test_type_registry_compatibility(self):

        for scale_type in self.substrate.get_type_registry():
            obj = self.substrate.runtime_config.get_decoder_class(scale_type)

            self.assertIsNotNone(obj, '{} not supported'.format(scale_type))


@settings.requires_live_node
class PolkadotTypeRegistryTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.substrate = SubstrateInterface(
            url=settings.POLKADOT_NODE_URL,
            ss58_format=0,
            type_registry_preset='polkadot'
        )

    def test_type_registry_compatibility(self):

        for scale_type in self.substrate.get_type_registry():

            obj = self.substrate.runtime_config.get_decoder_class(scale_type)

            self.assertIsNotNone(obj, '{} not supported'.format(scale_type))


class ReloadTypeRegistryTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.substrate = SubstrateInterface(
            url='dummy',
            ss58_format=42,
            type_registry_preset='test'
        )

    def test_initial_correct_type_local(self):
        decoding_class = self.substrate.runtime_config.type_registry['types']['index']
        self.assertEqual(self.substrate.runtime_config.get_decoder_class('u32'), decoding_class)

    def test_reloading_use_remote_preset(self):
        u64_cls = self.substrate.runtime_config.get_decoder_class('u64')
        with patch('scalecodec.type_registry.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'types': {'Index': 'u64'}}
            self.substrate.reload_type_registry()

        mock_get.assert_called_once()
        self.assertEqual(u64_cls, self.substrate.runtime_config.get_decoder_class('Index'))

    def test_reloading_use_local_preset(self):

        # Intentionally overwrite type in local preset
        u32_cls = self.substrate.runtime_config.get_decoder_class('u32')
        u64_cls = self.substrate.runtime_config.get_decoder_class('u64')

        self.substrate.runtime_config.type_registry['types']['index'] = u64_cls

        self.assertEqual(u64_cls, self.substrate.runtime_config.get_decoder_class('Index'))

        # Reload type registry
        self.substrate.reload_type_registry(use_remote_preset=False)

        self.assertEqual(u32_cls, self.substrate.runtime_config.get_decoder_class('Index'))

    def test_account_decoders_keep_runtime_ss58_formats(self):
        public_key = Keypair.create_from_uri('//Alice').public_key
        default_decoder = self.substrate.runtime_config.get_decoder_class('AccountId')

        with RuntimeFixture(ss58_format=2, auto_discover=False) as kusama:
            kusama_decoder = kusama.runtime_config.get_decoder_class('AccountId')
            self.assertEqual(default_decoder(data=ScaleBytes(public_key)).decode(), ss58_encode(public_key, 42))
            self.assertEqual(kusama_decoder(data=ScaleBytes(public_key)).decode(), ss58_encode(public_key, 2))


class PortableRegistryTestCase(unittest.TestCase):
    def test_type_reg_preset_applied(self):
        substrate = RuntimeFixture(chain='test')
        substrate.init_runtime()
        self.assertTrue(substrate.implements_scaleinfo())
        self.assertIsNotNone(substrate.runtime_config.get_decoder_class('SpecificTestType'))

    def test_default_substrate_address(self):
        substrate = RuntimeFixture(auto_discover=False)

        keypair_alice = Keypair.create_from_uri('//Alice', ss58_format=substrate.ss58_format)

        call = substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': keypair_alice.ss58_address,
                'value': 2000
            }
        )

        extrinsic = substrate.create_signed_extrinsic(call, keypair_alice, nonce=0)

        self.assertEqual(extrinsic.value['address'], f'0x{keypair_alice.public_key.hex()}')

    def test_eth_address(self):
        substrate = RuntimeFixture(auto_discover=False)
        metadata = substrate.get_block_metadata()
        runtime = metadata.value[1]['V14']
        types = {entry['id']: entry['type'] for entry in runtime['types']['types']}

        def variant_fields(type_id, name):
            variants = types[type_id]['def']['variant']['variants']
            return next(variant['fields'] for variant in variants if variant['name'] == name)

        # Model Ethereum-compatible runtimes with the fixture's 20-byte address and raw ECDSA signature.
        extrinsic_type = types[runtime['extrinsic']['ty']]
        params = {param['name']: param for param in extrinsic_type['params']}
        address_type = variant_fields(params['Address']['type'], 'Address20')[0]['type']
        params['Address']['type'] = address_type
        params['Signature']['type'] = variant_fields(params['Signature']['type'], 'Ecdsa')[0]['type']

        balances = next(pallet for pallet in runtime['pallets'] if pallet['name'] == 'Balances')
        fields = variant_fields(balances['calls']['ty'], 'transfer_keep_alive')
        next(field for field in fields if field['name'] == 'dest')['type'] = address_type
        metadata_encoder = substrate.runtime_config.create_scale_object('MetadataVersioned')
        substrate.rpc_results['state_getMetadata'] = str(metadata_encoder.encode(metadata.value))

        keypair_alice = Keypair.create_from_mnemonic(DEV_PHRASE, crypto_type=KeypairType.ECDSA)

        call = substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': keypair_alice.ss58_address,
                'value': 2000
            }
        )

        extrinsic = substrate.create_signed_extrinsic(call, keypair_alice, nonce=0)
        decoded = substrate.create_scale_object('Extrinsic').decode(extrinsic.data)

        self.assertEqual(decoded['address'], f'0x{keypair_alice.public_key.hex()}')


if __name__ == '__main__':
    unittest.main()
