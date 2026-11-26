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
from unittest.mock import Mock

from scalecodec.types import GenericAccountId

from substrateinterface.exceptions import SubstrateRequestException

from substrateinterface import SubstrateInterface
from test import settings
from test.fixtures import RuntimeFixture


CLAIM_ADDRESSES = (
    '0x00000a9c44f24e314127af63ae55b864a28d7aee',
    '0x00002f21194993a750972574e2d82ce8c95078a6',
    '0x0000a940f973ccf435ae9c040c253e1c043c5fb2',
    '0x00010b75619f666c3f172f0d1c7fa86d02adcf9c',
    '0x0002000000000000000000000000000000000000',
)
STAKER_ADDRESSES = (
    'JCghFN7mD4ETKzMbvSVmMMPwWutJGk6Bm1yKWk8Z9KhPGeZ',
    'CmNv7yFV13CMM6r9dJYgdi4UTJK7tzFEF17gmK9c3mTc2PG',
    'DfishveZoxSRNRb8FtyS7ignbw6cr32eCY2w6ctLDRM1NQz',
    'HmsTAS1bCtZc9FSq9nqJzZCEkhhSygtXj9TDxNgEWTHnpyQ',
)


class QueryMapTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kusama_substrate = RuntimeFixture(metadata_version='kusama_test', ss58_format=2)
        substrate = cls.kusama_substrate

        def storage_key(pallet, name, *params):
            return substrate.create_storage_key(pallet, name, list(params)).to_hex()

        claims = {
            storage_key('Claims', 'Claims', address): '0x' + (45880000000000 + i).to_bytes(16, 'little').hex()
            for i, address in enumerate(CLAIM_ADDRESSES)
        }
        account_type = substrate.get_metadata_storage_function('System', 'Account').get_value_type_string()
        accounts = {
            storage_key('System', 'Account', '0x' + f'{i:02x}' * 32): str(substrate.encode_scale(account_type, {
                'nonce': i,
                'refcount': 0,
                'data': {'free': 100, 'reserved': 0, 'misc_frozen': 0, 'fee_frozen': 0},
            }))
            for i in (1, 2)
        }
        exposure_type = substrate.get_metadata_storage_function('Staking', 'ErasStakers').get_value_type_string()
        exposure = str(substrate.encode_scale(exposure_type, {'total': 1, 'own': 1, 'others': []}))
        stakers = {storage_key('Staking', 'ErasStakers', 2185, address): exposure for address in STAKER_ADDRESSES}
        cls.storage_at = {
            substrate.block_head: {**claims, **stakers},
            substrate.parent_hash: {**dict(list(claims.items())[:4]), **accounts},
        }

    def setUp(self):
        def get_keys_paged(params):
            prefix, page_size, start_key, block_hash = params
            if page_size > 1000:
                raise SubstrateRequestException('Maximum page size is 1000')

            keys = sorted(key for key in self.storage_at[block_hash] if key.startswith(prefix) and key > start_key)
            return keys[:page_size]

        def query_storage_at(params):
            keys, block_hash = params
            return [{'block': block_hash, 'changes': [[key, self.storage_at[block_hash][key]] for key in keys]}]

        self.get_keys_paged = Mock(side_effect=get_keys_paged)
        self.kusama_substrate.rpc_results.update({
            'state_getKeysPaged': self.get_keys_paged,
            'state_queryStorageAt': query_storage_at,
        })

    def test_claims_claim_map(self):

        result = self.kusama_substrate.query_map('Claims', 'Claims', max_results=3)

        records = [item for item in result]

        self.assertEqual(3, len(records))
        self.assertEqual(45880000000000, records[0][1].value)
        self.assertEqual(list(CLAIM_ADDRESSES[:3]), [key.value for key, _ in records])

    def test_system_account_map_block_hash(self):

        # Retrieve first two records from System.Account query map

        block_hash = self.kusama_substrate.parent_hash
        result = self.kusama_substrate.query_map('System', 'Account', page_size=1, block_hash=block_hash)

        record_1_1 = next(result)

        self.assertIsInstance(record_1_1[0], GenericAccountId)
        self.assertIn('data', record_1_1[1].value)
        self.assertIn('nonce', record_1_1[1].value)

        # Next record set must trigger RPC call

        self.assertEqual(1, self.get_keys_paged.call_count)
        record_1_2 = next(result)
        self.assertEqual(2, self.get_keys_paged.call_count)

        self.assertIsInstance(record_1_2[0], GenericAccountId)
        self.assertIn('data', record_1_2[1].value)
        self.assertIn('nonce', record_1_2[1].value)

        # Same query map with yield of 2 must result in same records

        result = self.kusama_substrate.query_map('System', 'Account', page_size=2, block_hash=block_hash)

        record_2_1 = next(result)
        record_2_2 = next(result)

        self.assertEqual(record_1_1[0].value, record_2_1[0].value)
        self.assertEqual(record_1_1[1].value, record_2_1[1].value)
        self.assertEqual(record_1_2[0].value, record_2_2[0].value)
        self.assertEqual(record_1_2[1].value, record_2_2[1].value)

    def test_max_results(self):
        for page_size, expected_requests in ((100, 1), (2, 2)):
            with self.subTest(page_size=page_size):
                self.get_keys_paged.reset_mock()
                result = self.kusama_substrate.query_map('Claims', 'Claims', max_results=3, page_size=page_size)
                self.assertEqual(list(CLAIM_ADDRESSES[:3]), [key.value for key, _ in result])
                self.assertEqual(expected_requests, self.get_keys_paged.call_count)

    def test_result_exhausted(self):
        result = self.kusama_substrate.query_map(
            module='Claims', storage_function='Claims',
            block_hash=self.kusama_substrate.parent_hash
        )
        self.assertEqual(list(CLAIM_ADDRESSES[:4]), [key.value for key, _ in result])
        self.assertEqual(2, self.get_keys_paged.call_count)

    def test_non_existing_query_map(self):
        with self.assertRaises(ValueError) as cm:
            self.kusama_substrate.query_map("Unknown", "StorageFunction")

        self.assertEqual('Pallet "Unknown" not found', str(cm.exception))

    def test_non_map_function_query_map(self):
        with self.assertRaises(ValueError) as cm:
            self.kusama_substrate.query_map("System", "Events")

        self.assertEqual('Given storage function is not a map', str(cm.exception))

    def test_exceed_maximum_page_size(self):
        with self.assertRaises(SubstrateRequestException):
            self.kusama_substrate.query_map(
                'System', 'Account', page_size=9999999
            )

    def test_double_map(self):
        era_stakers = self.kusama_substrate.query_map(
            module='Staking',
            storage_function='ErasStakers',
            params=[2185],
            max_results=4
        )

        records = list(era_stakers)

        self.assertEqual(list(STAKER_ADDRESSES), [key.ss58_address for key, _ in records])
        self.assertEqual({'total': 1, 'own': 1, 'others': []}, records[0][1].value)

    def test_double_map_page_size(self):
        era_stakers = self.kusama_substrate.query_map(
            module='Staking',
            storage_function='ErasStakers',
            params=[2185],
            max_results=4,
            page_size=1
        )

        self.assertEqual(list(STAKER_ADDRESSES), [key.ss58_address for key, _ in era_stakers])
        self.assertEqual(4, self.get_keys_paged.call_count)

    def test_double_map_no_result(self):
        era_stakers = self.kusama_substrate.query_map(
            module='Staking',
            storage_function='ErasStakers',
            params=[21000000]
        )
        self.assertEqual(era_stakers.records, [])

    def test_double_map_too_many_params(self):
        with self.assertRaises(ValueError) as cm:
            self.kusama_substrate.query_map(
                module='Staking',
                storage_function='ErasStakers',
                params=[21000000, 2]
            )
        self.assertEqual('Storage function map can accept max 1 parameters, 2 given', str(cm.exception))

    def test_map_with_param(self):
        with self.assertRaises(ValueError) as cm:
            self.kusama_substrate.query_map(
                module='System',
                storage_function='Account',
                params=[2]
            )
        self.assertEqual('Storage function map can accept max 0 parameters, 1 given', str(cm.exception))


@settings.requires_live_node
class HistoricalQueryMapTestCase(unittest.TestCase):
    def setUp(self):
        self.substrate = SubstrateInterface(url=settings.KUSAMA_NODE_URL, ss58_format=2, type_registry_preset='kusama')
        self.addCleanup(self.substrate.close)

    def test_claims_claim_map(self):
        result = self.substrate.query_map(
            'Claims', 'Claims', max_results=3,
            block_hash='0x4b313e72e3a524b98582c31cd3ff6f7f2ef5c38a3c899104a833e468bb1370a2'
        )
        records = list(result)

        self.assertEqual(list(CLAIM_ADDRESSES[:3]), [key.value for key, _ in records])
        self.assertEqual(45880000000000, records[0][1].value)

    def test_double_map(self):
        result = self.substrate.query_map(
            'Staking', 'ErasStakers', params=[2185], max_results=4,
            block_hash='0x61dd66907df3187fd1438463f2c87f0d596797936e0a292f6f98d12841da2325'
        )
        self.assertEqual(list(STAKER_ADDRESSES), [key.ss58_address for key, _ in result])


if __name__ == '__main__':
    unittest.main()
