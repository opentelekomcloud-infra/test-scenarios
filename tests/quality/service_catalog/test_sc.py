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
import json
import yaml

#from urllib.parse import urlparse

import influxdb
import openstack

#from keystoneauth1 import discover


results = {}


def read_sc_config(conn, config_path='service_config.yaml'):
    data = {}
    with open(config_path) as fp:
        data = yaml.load(fp, Loader=yaml.FullLoader)
    return data


def _normalize_catalog(catalog):
    cat = {}
    for rec in catalog:
        entry_type = rec.get('type')
        cat[entry_type] = rec
    return cat


def _log(level, section, service, msg):
#     if not section in results:
#         results[section] = {}
#     if service not in results[section]:
#         results[section][service] = {}
#     if level not in results[section][service]:
#         results[section][service][level] = []
#     results[section][service][level].append(msg)
    if service not in results:
        results[service] = {}
    if level not in results[service]:
        results[service][level] = []
    results[service][level].append(msg)



def _error(section, service, msg):
    return _log('error', section, service, msg)


def _warn(section, service, msg):
    return _log('warn', section, service, msg)

def _success(section, service, msg=None):
    return _log('success', section, service, msg)


def validate_catalog_valid(catalog):
    cat = {}
    for rec in catalog:
        entry_type = rec.get('type')
        if entry_type in cat:
            _error(
                'catalog', 'general',
                'Service %s present multiple times' % entry_type)
        cat[entry_type] = rec


def _validate_service_known_in_regions(service_name, service, endpoints, regions,
                                       type='catalog'):
    match = {}
    for reg in regions:
        for cat_srv in endpoints:
            reg_id = cat_srv.get('region_id')
            if reg == reg_id:
                match[reg] = True
        if reg not in match:
            _error(
                type + '_catalog', service_name,
                'Service %s is not registered in region %s' %
                (service.get('type'), reg))


def validate_service_known_in_region(conn, catalog, config, regions):
    for srv in config['services']:
        service_name = list(srv.keys())[0]
        srv_data = srv[service_name]
        service_type = srv_data.get('service_type')
        service_in_catalog = catalog.get(service_type)
        if not service_in_catalog:
            _error(
                'token_catalog', service_name,
                'Service %s is not know in catalog' % service_type)
            continue
        _validate_service_known_in_regions(
            service_name,
            service_in_catalog,
            service_in_catalog.get('endpoints', []),
            regions,
            'token')

        # Validate standalone endpoints for the service are actually same
        _validate_service_known_in_regions(
            service_name,
            service_in_catalog,
            conn.identity.endpoints(service_id=service_in_catalog.get('id')),
            regions,
            'catalog'
        )


def validate_service_supports_version_discovery(conn, catalog, config,
                                                regions):
    for srv in config['services']:

        service_name = list(srv.keys())[0]
        srv_data = srv[service_name]
        service_type = srv_data.get('service_type')
        service_in_catalog = catalog.get(service_type)
        if not service_in_catalog:
            # bad service with no entries
            continue

        for ep in service_in_catalog.get('endpoints'):
            supports_vd = False
            client = conn.config.get_session_client(service_type)
            url = ep['url']
            try:
                data = client.get_endpoint_data()
                if data.service_url:
                    # If we got service_url - most likely we are good
                    supports_vd = True
                url = data.service_url or data.catalog_url
            except Exception as e:
                supports_vd = False
            if not supports_vd:
                _warn('service_version_discovery',
                      service_name,
                      'Service %s does not support version discovery properly'
                      % service_type)
            # Now verify that the URL we have points to a usable point
            expected_suffix = srv_data.get('expected_suffix').format(
                project_id=conn.current_project_id
            ).rstrip('/')
            if not url.rstrip('/').endswith(expected_suffix):
                _warn('service_version_discovery',
                      service_name,
                      'Service %s exposes wrong suffix'
                      % service_type)


def write_result(influx_client, config):
    data_points = []
    services = []
    for srv in config.get('services'):
        services.append(list(srv.keys())[0])
    services.append('general')
    for service_name in services:
        result = results.get(service_name, {})
        point = dict(
            measurement='scmon1',
            tags=dict(
                service_type=service_name,
            )
        )
        point['fields'] = dict(
            service=service_name,
            errors=len(result.get('error', [])) or 0,
            warn=len(result.get('warn', [])) or 0
        )
        data_points.append(point)
    if data_points and influx_client:
        influx_client.write_points(data_points)


def get_influx_client():
    host = os.environ.get('INFLUXDB_HOST', 'localhost')
    port = int(os.environ.get('INFLUXDB_PORT', 8086))
    user = os.environ.get('INFLUXDB_USER')
    password = os.environ.get('INFLUXDB_PASSWORD')
    database = os.environ.get('INFLUXDB_DATABASE', 'default')
    ssl = os.environ.get('INFLUXDB_SSL', False)
    influx = None
    if host and port and user and password:
        influx = influxdb.InfluxDBClient(
            host, port, user, password, database,
            ssl, timeout=5)
    return influx


def main():
    conn = openstack.connect()
    sc_config = read_sc_config('../../service_config.yaml')
    project_catalog = conn.config.get_service_catalog().catalog
    normalized_project_catalog = _normalize_catalog(project_catalog)

    regions = [x.id for x in conn.identity.regions()]

    validate_catalog_valid(project_catalog)

    validate_service_known_in_region(
        conn,
        normalized_project_catalog,
        sc_config,
        regions
    )

    validate_service_supports_version_discovery(
        conn,
        normalized_project_catalog,
        sc_config,
        regions
    )

    print(json.dumps(results, sort_keys=True, indent=True))

    influx_client = get_influx_client()
    if influx_client:
        write_result(influx_client, sc_config)


if __name__ == '__main__':
    main()
