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

from scalecodec import ScaleBytes
from scalecodec.exceptions import RemainingScaleBytesNotEmptyException
from substrateinterface import SubstrateInterface
from test import settings


class TestLightClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.polkadot_substrate = SubstrateInterface(chainspec='polkadot')
        cls.asset_hub_substrate = SubstrateInterface(chainspec="ksmcc3_asset_hub", relay_chainspecs=["ksmcc3"])

    def test_chain(self):
        self.assertEqual('Kusama Asset Hub', self.asset_hub_substrate.chain)
        self.assertEqual('Polkadot', self.polkadot_substrate.chain)

    def test_properties(self):
        self.assertDictEqual(
            {'ss58Format': 2, 'tokenDecimals': 12, 'tokenSymbol': 'KSM'}, self.asset_hub_substrate.properties
        )
        self.assertDictEqual(
            {'ss58Format': 0, 'tokenDecimals': 10, 'tokenSymbol': 'DOT'}, self.polkadot_substrate.properties
        )


if __name__ == '__main__':
    unittest.main()
