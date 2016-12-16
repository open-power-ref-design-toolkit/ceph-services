#!/usr/bin/python

# Copyright 2016, IBM US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import copy
import math
import os.path
import sys
import yaml


JOURNAL_DEVICE_KEY = 'journal-devices'
OSD_DEVICE_KEY = 'osd-devices'
CEPH_STANDALONE = 'ceph-standalone'

openstack_keys = [
    {'name': 'client.glance',
     'value': "mon 'allow r' osd 'allow class-read object_prefix rbd_children,"
              " allow rwx pool={{ openstack_glance_pool.name }}'"},
    {'name': 'client.cinder',
     'value': "mon 'allow r' osd 'allow class-read object_prefix rbd_children,"
              " allow rwx pool={{ openstack_cinder_pool.name }},"
              " allow rwx pool={{ openstack_nova_pool.name }},"
              " allow rwx pool={{ openstack_glance_pool.name }}'"}]

openstack_pools = [
    "{{ openstack_glance_pool }}",
    "{{ openstack_cinder_pool }}",
    "{{ openstack_nova_pool }}"]


hard_coded_vars = {
    'ceph_stable_uca': True,
    'ceph_stable_openstack_release_uca': 'newton',
    'ceph_stable_repo_uca': 'http://ubuntu-cloud.archive.canonical.com/ubuntu',
    'ceph_stable_release_uca': '{{ ansible_lsb.codename }}-updates/'
                               '{{ ceph_stable_openstack_release_uca }}',
    'debian_ceph_packages': ['ceph', 'ceph-common'],
    'generate_fsid': True,
    'journal_size': 10240,
    'nfs_file_gw': False}


def _load_yml(name):
    with open(name, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as ex:
            print(ex)
            sys.exit(1)


def _write_yml(filename, contents):
    stream = file(filename, 'w')
    yaml.dump(contents, stream, default_flow_style=False, width=1000)


def _write_string(filename, contents):
    hosts_file = open(filename, "w")
    hosts_file.write(contents)
    hosts_file.close()


def _get_storage_network(inventory):
    if 'reference-architecture' in inventory.keys():
        if CEPH_STANDALONE in inventory['reference-architecture']:
            return 'ceph-public-storage'
    return 'openstack-stg'


def _init_default_values(inventory):
    config_vars = copy.deepcopy(hard_coded_vars)
    storage_net_name = _get_storage_network(inventory)
    storage_net = inventory['networks'][storage_net_name]
    mon_interface = storage_net.get('bridge')
    if not mon_interface:
        mon_interface = storage_net.get('eth-port')
    config_vars['monitor_interface'] = mon_interface
    if 'reference-architecture' in inventory.keys():
        if CEPH_STANDALONE in inventory['reference-architecture']:
            config_vars['delete_default_pool'] = False
            return config_vars
    config_vars['delete_default_pool'] = True
    config_vars['openstack_config'] = True
    config_vars['openstack_keys'] = openstack_keys
    config_vars['openstack_pools'] = openstack_pools
    return config_vars


def _get_osd_ips(inventory):
    osd_network = '%s-addr' % _get_storage_network(inventory)
    return [host[osd_network]
            for host in inventory['nodes']['ceph-osd']]


def _get_mon_ips(inventory):
    osd_network = '%s-addr' % _get_storage_network(inventory)
    return [host[osd_network]
            for host in inventory['nodes']['controllers']]


def generate_files(root_dir, inventory_file, growth_factor, vms_data_percent,
                   images_data_percent, volumes_data_percent):
    inventory = _load_yml(inventory_file)
    all_vars = _generate_all_vars(inventory, growth_factor, vms_data_percent,
                                  images_data_percent, volumes_data_percent)
    _write_yml(os.path.join(root_dir, 'group_vars', 'all'), all_vars)
    osd_vars = _generate_osds_vars(inventory)
    _write_yml(os.path.join(root_dir, 'group_vars', 'osds'), osd_vars)
    hosts_contents = _generate_hosts_file(inventory)
    _write_string(os.path.join(root_dir, 'ceph-hosts'), hosts_contents)


def _generate_all_vars(inventory, growth_factor, vms_data_percent,
                       images_data_percent, volumes_data_percent):
    all_vars = _init_default_values(inventory)
    pub_storage = _get_storage_network(inventory)
    storage_net = inventory['networks'][pub_storage]['addr']
    cluster_net = '{{ public_network }}'

    if 'ceph-replication' in inventory['networks']:
        cluster_net = inventory['networks']['ceph-replication']['addr']

    if 'reference-architecture' in inventory.keys():
        if CEPH_STANDALONE not in inventory['reference-architecture']:
            openstack_pools = _get_openstack_pools(inventory, growth_factor,
                                                   vms_data_percent,
                                                   images_data_percent,
                                                   volumes_data_percent)
            all_vars.update(openstack_pools)
    all_vars['public_network'] = storage_net
    all_vars['cluster_network'] = cluster_net
    return all_vars


def _generate_osds_vars(inventory):
    osd_vars = {}
    template = inventory['node-templates']['ceph-osd']
    osd_vars['devices'] = template['domain-settings'][OSD_DEVICE_KEY]

    if JOURNAL_DEVICE_KEY in template['domain-settings']:
        osd_vars['raw_multi_journal'] = True
        osd_vars['raw_journal_devices'] = _generate_journal_device_list(
            template['domain-settings'][JOURNAL_DEVICE_KEY],
            len(osd_vars['devices']))
    else:
        osd_vars['journal_collocation'] = True
    return osd_vars


def _generate_journal_device_list(journal_devices, osd_device_count):
    # Generate the journal device list, ensuring every OSD has a journal
    # and we account for the remainder OSDs when the number of OSDs is not
    # evenly divisible by the number of journals.
    osds_per_journal = int(math.floor(osd_device_count /
                                      (len(journal_devices) * 1.0)))
    remainder = osd_device_count % len(journal_devices)
    osd_journal_list = []
    for x in range(len(journal_devices)):
        journal_device = journal_devices[x]
        for y in range(osds_per_journal):
            osd_journal_list.append(journal_device)
        # Add the journal again if we have remainder OSDs
        if x < remainder:
            osd_journal_list.append(journal_device)

    return osd_journal_list


def _validate_devices_lists(osd_templates, device_key):
    """
    Validates the device lists on the OSD templates.
    The journal device lists must match across the templates.
    The osd device lists must match across the templates.
    This method is currently unused since we have moved the device lists from
    nodes to templates and only support one template.
    """

    def checkEqual(iterator):
        try:
            iterator = iter(iterator)
            first = next(iterator)
            return all(first == rest for rest in iterator)
        except StopIteration:
            return True

    are_equal = checkEqual(iter([tmpl[device_key] for tmpl in osd_templates]))
    if not are_equal:
        msg = ('The device list %(list_name)s does not contain the same '
               'set of devices across all of '
               'the OSD nodes.') % {'list_name': device_key}
        raise InvalidDeviceList(msg)


def _generate_hosts_file(inventory):
    # Get monitor IPs
    mon_ips = _get_mon_ips(inventory)
    # Get OSD IPs
    osd_ips = _get_osd_ips(inventory)
    file_contents_list = ['[mons]'] + mon_ips + ['\n[osds]'] + osd_ips
    return '\n'.join(file_contents_list)


def _get_openstack_pools(inventory, growth_factor, vms_percent,
                         images_percent, volumes_percent):
    pools = {'openstack_glance_pool': {'name': 'images',
                                       'percent_data':
                                       (images_percent / 100.0)},
             'openstack_nova_pool': {'name': 'vms',
                                     'percent_data': (vms_percent / 100.0)},
             'openstack_cinder_pool': {'name': 'volumes',
                                       'percent_data':
                                       (volumes_percent / 100.0)
                                       },
             }

    osd_count = _get_osd_count(inventory)
    for pool in pools.values():
        percent_data = pool.pop('percent_data')
        pgs = _calculate_pg_count(osd_count, percent_data, growth_factor)
        pool['pg_num'] = pgs
    return pools


def _calculate_pg_count(osd_count, percent_data, growth_factor):
    # PG calc formula from http://ceph.com/pgcalc/

    # This is the 'size' value in the calcs.
    replication_count = 3

    def nearest_power_of_2(value):
        # If the nearest power of 2 is more than 25% below the
        # original value, the next higher power of 2 is used.
        threshold = .25
        nearest = math.pow(2, round(math.log(value) / math.log(2)))
        if nearest < (value * (1 - threshold)):
            nearest = nearest * 2
        return nearest

    numerator = growth_factor * osd_count * percent_data
    pg_before_pow2 = math.floor(numerator / replication_count)
    if pg_before_pow2 == 0:
        pg_before_pow2 = 1
    pg_count = nearest_power_of_2(pg_before_pow2)
    # If the value of the above calculation is less than the value of
    # (OSD#) / (Size), then the value is updated to the value of
    # ((OSD#) / (Size)). This is to ensure even load / data distribution
    # by allocating at least one Primary or Secondary PG to every OSD for
    # every Pool.
    min_calc = nearest_power_of_2(
        math.floor(osd_count / replication_count) + 1)
    if pg_count < min_calc:
        pg_count = min_calc
    return int(pg_count)


def _get_osd_count(inventory):
    ceph_osd_tmpl = inventory['node-templates']['ceph-osd']
    domain_settings = ceph_osd_tmpl['domain-settings']
    num_osd_nodes = len(inventory['nodes']['ceph-osd'])
    count = len(domain_settings[OSD_DEVICE_KEY]) * num_osd_nodes
    return count


def main():

    parser = argparse.ArgumentParser(
        description=('Generate ceph-ansible input files using an'
                     ' inventory file.'),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--inventory',
                        dest='inventory_file',
                        required=True,
                        help='The path to the inventory file.')

    parser.add_argument('--output_directory',
                        dest='output_root',
                        required=True,
                        help=('The root path of the output directory.'
                              ' This is typically the root of ceph-ansible.'))

    growth_factor_help = (
        'A integer factor of how much the Ceph cluster is  expected to grow '
        'in the foreseeable future.\n'
        'Example values:\n'
        '100 - if number of disks in the cluster is not expected to increase\n'
        '200 - if the number of disks in the cluster is expected to double\n'
        '300 - if the number of disks in the cluster is expected to grow '
        'between 2X and 3X\n')

    parser.add_argument('--growth_factor',
                        dest='growth_factor',
                        type=int,
                        required=False,
                        default=100,
                        help=growth_factor_help)

    parser.add_argument('--vms_pool_percent',
                        dest='vms_pool_percent',
                        required=False,
                        type=int,
                        default=25,
                        help=('The percentage of the cluster data which will'
                              'be contained in the virtual machines pool,'
                              'specified as an integer. Example: 25 for 25%%'))
    parser.add_argument('--images_pool_percent',
                        dest='images_pool_percent',
                        required=False,
                        type=int,
                        default=15,
                        help=('The percentage of the cluster data which will'
                              'be contained in the images pool,'
                              'specified as an integer. Example: 25 for 25%%'))
    parser.add_argument('--volumes_pool_percent',
                        dest='volumes_pool_percent',
                        required=False,
                        type=int,
                        default=60,
                        help=('The percentage of the cluster data which will'
                              'be contained in the volumes pool,'
                              'specified as an integer. Example: 25 for 25%%'))

    # Handle error cases before attempting to parse
    # a command off the command line
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    generate_files(args.output_root, args.inventory_file, args.growth_factor,
                   args.vms_pool_percent, args.images_pool_percent,
                   args.volumes_pool_percent)

if __name__ == "__main__":
    main()


class InvalidDeviceList(Exception):
    pass
