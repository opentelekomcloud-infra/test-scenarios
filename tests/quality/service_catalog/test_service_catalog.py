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
import pytest
import os
#from tests.quality import base

from openstack import exceptions

import influxdb


testdata = [
    ('antiddos'),
    ('as'),
    ('asv1'),
    ('cce'),
    ('ccev2.0'),
    ('ces'),
    ('cesv1'),
    ('cesv1'),
    ('compute'),
    ('csbs'),
    ('css'),
    ('cts'),
    ('ctsv2'),
    ('data-protect'),
    ('database'),
    ('dcaas'),
    ('dcs'),
    ('dcsv1'),
    ('ddsv3'),
    ('deh'),
    ('dis'),
    ('disv2'),
    ('dms'),
    ('dmsv1'),
    ('dns'),
    ('dws'),
    ('dwsv1'),
    ('ecs'),
    ('elb'),
    ('elbv1'),
    ('evs'),
    ('identity'),
    ('image'),
    ('kms'),
    ('kmsv1'),
    ('lts'),
    ('mrs'),
    ('mrsv1'),
    ('nat'),
    ('network'),
    ('object-store'),
    ('orchestration'),
    ('plas'),
    ('rds'),
    ('rdsv3'),
    ('sdrs'),
    ('sharev2'),
    ('sfsturbo'),
    ('smn'),
    ('smnv2'),
    ('swr'),
    ('tms'),
    ('vbs'),
    ('vbsv2'),
    ('volume'),
    ('volumev2'),
    ('volumev3'),
    ('vpc'),
    ('vpc2.0'),
    ('vpcep'),
    ('waf'),
    ('wks'),
    ('workspace'),
]


class TestServiceCatalog:

    @pytest.fixture(scope='module')
    def influx_client(self):
        host = os.environ.get('INFLUXDB_HOST', 'localhost')
        port = int(os.environ.get('INFLUXDB_PORT', 8080))
        user = os.environ.get('INFLUXDB_USER')
        password = os.environ.get('INFLUXDB_PASSWORD')
        database = os.environ.get('INFLUXDB_DATABASE', 'default')
        influx = None
        if host and port and user and password:
            influx = influxdb.InfluxDBClient(
                host, port, user, password, database,
                ssl=True)
        return influx

    def get_catalog(self, conn):
       return conn.config.get_service_catalog().catalog

    def convert_catalog(self, catalog):
        cat = {}
        for rec in catalog:
            entry_type = rec.get('type')
            cat[entry_type] = rec
        return cat

    def test_validate_catalog_structure(self, conn, influx_client, token_catalog):
        """Verify catalog structure"""
        cat = {}
        for rec in token_catalog:
            entry_type = rec.get('type')
            if entry_type in cat:
                valid = False
            else:
                valid = True
            self.write_result(influx_client, entry_type,
                              'single_in_catalog', not valid)
            cat[entry_type] = rec
        self.write_result(influx_client, None,
                          'catalog_valid', not valid)
        assert valid, "Service catalog is valid"

    @pytest.fixture(scope='module')
    def token_catalog(self, conn):
        return self.get_catalog(conn)

    @pytest.fixture(scope='module')
    def normalized_catalog(self, conn, token_catalog):
        return self.convert_catalog(token_catalog)

    @pytest.mark.parametrize('service_type', testdata)
    def test_service_available_in_region(
            self, conn, influx_client, normalized_catalog,
            service_type):
        match = {}
        regions = [x.id for x in conn.identity.regions()]
        srv = normalized_catalog.get(service_type, {})
        if not srv:
            self.write_result(influx_client, service_type,
                              'service_in_catalog', True)
#        assert srv, "Service present in the catalog"
        if srv:
            for ep in srv['endpoints']:
                for reg in regions:
                   if ep['region_id'] == reg:
                        match[reg] = True
            failed = False
            if len(match.keys()) != len(regions):
                failed = True
            self.write_result(influx_client, service_type,
                              'endpoint_present_in_region', failed)
            assert not failed, \
                   "Service known in all regions"
        else:
            self.write_result(influx_client, service_type,
                              'endpoint_present_in_region', True)

    def write_result(self, influx_client, service, check, failed):
        if influx_client:
            fields = dict(
                service=service,
                failed=1 if failed else 0,
                succeeded=0 if failed else 1
            )
            influx_client.write_points([
                dict(
                    measurement='scmon',
                    fields=fields,
                    tags=dict(
                        service_type=service,
                        check=check,
                        status='failed' if failed else 'succeeded'
                    )
                )
            ])

