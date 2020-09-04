# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os
import pytest

import openstack.config
from openstack import connection


TEST_CLOUD_NAME = os.getenv('OS_CLOUD', 'otc')
TEST_CLOUD_REGION = openstack.config.get_cloud_region(cloud=TEST_CLOUD_NAME)

KNOWN_SERVICES = [
    {
        'name': 'identity',
        'service_type': 'identity',
        'expected_suffix': '/v3'
    }
]


@pytest.fixture(scope='module')
def conn():
    return connection.Connection(config=TEST_CLOUD_REGION)
