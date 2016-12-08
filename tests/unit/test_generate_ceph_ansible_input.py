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

import copy
import os
import os.path
import mock
import sys
import unittest

TOP_DIR = os.path.join(os.getcwd(), os.path.dirname(__file__), '../..')
SCRIPT_DIR = 'scripts/ulysses_ceph'
sys.path.append(os.path.join(TOP_DIR, SCRIPT_DIR))

import generate_ceph_ansible_input as test_mod


class TestGenerateCephAnsibleInput(unittest.TestCase):
    TEST_MODULE_STRING = 'generate_ceph_ansible_input'

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch(TEST_MODULE_STRING + '._get_openstack_pools')
    def test_generate_all_vars(self, get_pools):
        # Test private cloud with bridge as monitor interface
        ref_arch = ['private-compute-cloud']
        get_pools.return_value = {'poolname': 'a pool'}
        inventory = {'networks': {'openstack-stg':
                                  {'addr': '172.29.244.0/22',
                                   'bridge': 'br-storage'}},
                     'reference-architecture': ref_arch}
        growth_factor = 200
        os_keys = copy.deepcopy(test_mod.openstack_keys)
        os_pools = copy.deepcopy(test_mod.openstack_pools)
        verify_vars = copy.deepcopy(test_mod.hard_coded_vars)
        verify_vars.update(get_pools.return_value)
        verify_vars['delete_default_pool'] = True
        verify_vars['public_network'] = '172.29.244.0/22'
        verify_vars['cluster_network'] = '{{ public_network }}'
        verify_vars['openstack_config'] = True
        verify_vars['ceph_stable_uca'] = True
        verify_vars['openstack_keys'] = os_keys
        verify_vars['openstack_pools'] = os_pools
        verify_vars['monitor_interface'] = 'br-storage'
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1)
        self._assert_invalid_config(ref_arch, verify_vars)
        self.assertDictEqual(verify_vars, all_vars)

        # Test again with cluster net set
        inventory['networks']['ceph-replication'] = {'addr': '172.29.100.0/22'}
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1)

        verify_vars['cluster_network'] = '172.29.100.0/22'
        self.assertDictEqual(verify_vars, all_vars)

        # Test ceph-standalone with eth-port as monitor interface
        ref_arch = ['ceph-standalone']
        inventory = {'networks': {'ceph-public-storage':
                                  {'addr': '172.26.244.0/22',
                                   'eth-port': 'eth11'}},
                     'reference-architecture': ref_arch,
                     'nodes': {'controllers': [{'hostname': ['sm15']}],
                               'ceph-osd': [{'hostname': 'osd1',
                                             'ceph-public-storage-addr':
                                             '172.26.244.0/22'}]}}
        growth_factor = 200
        verify_vars = test_mod._init_default_values(inventory)
        verify_vars['delete_default_pool'] = False
        verify_vars['public_network'] = '172.26.244.0/22'
        verify_vars['cluster_network'] = '{{ public_network }}'
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1)
        self._assert_invalid_config(ref_arch, verify_vars)
        self.assertDictEqual(verify_vars, all_vars)

        # Test again with cluster net set
        inventory['networks']['ceph-replication'] = {'addr': '172.29.100.0/22'}
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1)
        verify_vars['cluster_network'] = '172.29.100.0/22'
        self.assertDictEqual(verify_vars, all_vars)

    def _assert_invalid_config(self, ref_arch, ref_config_settings):
        if 'private-compute-cloud' in ref_arch:
            self.assertIn('openstack_keys', ref_config_settings)
            self.assertIn('openstack_pools', ref_config_settings)
            self.assertIn('openstack_config', ref_config_settings)
        elif 'ceph-standalone' in ref_arch:
            self.assertNotIn('openstack_config', ref_config_settings)
            self.assertNotIn('openstack_keys', ref_config_settings)
            self.assertNotIn('openstack_pools', ref_config_settings)

    def test_init_default_values(self):
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'networks': {'openstack-stg': {'bridge': 'br-storage',
                                                    'eth-port': 'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory)
        self.assertEquals(verify_vars['monitor_interface'], 'br-storage')
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue(verify_vars['openstack_config'])
        self.assertTrue(verify_vars['ceph_stable_uca'])
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'networks': {'ceph-public-storage': {'eth-port':
                                                          'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertEquals(verify_vars['monitor_interface'], 'eth11')

    def test_get_storage_network(self):
        inventory = {'reference-architecture': ['ceph-standalone']}
        self.assertEqual(test_mod._get_storage_network(inventory),
                         'ceph-public-storage')
        inventory = {'reference-architecture': ['private-compute-cloud']}
        self.assertEqual(test_mod._get_storage_network(inventory),
                         'openstack-stg')

    def test_get_osd_ips(self):
        ref_arch = ['ceph-standalone']
        inventory = {'reference-architecture': ref_arch,
                     'nodes': {'ceph-osd': [{'hostname': 'osd1',
                                             'ceph-public-storage-addr':
                                             '172.26.244.1'},
                                            {'hostname': 'osd2',
                                             'ceph-public-storage-addr':
                                             '172.26.244.2'}]}}
        self.assertEquals(test_mod._get_osd_ips(inventory),
                          ['172.26.244.1', '172.26.244.2'])
        ref_arch = ['private-compute-cloud']
        inventory = {'reference-architecture': ref_arch,
                     'nodes': {'ceph-osd': [{'openstack-stg-addr':
                                             '172.26.244.1'}]}}
        self.assertEqual(test_mod._get_osd_ips(inventory),
                         ['172.26.244.1'])

    def test_get_mon_ips(self):
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'nodes': {'controllers': [{'hostname': 'controller1',
                                                'ceph-public-storage-addr':
                                                '172.29.244.2'},
                                               {'hostname': 'controller2',
                                                'ceph-public-storage-addr':
                                                '172.29.244.3'},
                                               {'hostname': 'controller3',
                                                'ceph-public-storage-addr':
                                                '172.29.244.4'}]}}
        self.assertEqual(test_mod._get_mon_ips(inventory),
                         ['172.29.244.2', '172.29.244.3', '172.29.244.4'])
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'nodes': {'controllers': [{'hostname': 'controller1',
                                                'openstack-stg-addr':
                                                '172.29.244.2'},
                                               {'hostname': 'controller2',
                                                'openstack-stg-addr':
                                                '172.29.244.3'},
                                               {'hostname': 'controller3',
                                                'openstack-stg-addr':
                                                '172.29.244.4'}]}}
        self.assertEqual(test_mod._get_mon_ips(inventory),
                         ['172.29.244.2', '172.29.244.3', '172.29.244.4'])

    def test_get_osd_count(self):
        osd_devices = ['/dev/sde',
                       '/dev/sdf',
                       '/dev/sdg',
                       '/dev/sdh',
                       '/dev/sdi']
        osd_tmpl = {test_mod.OSD_DEVICE_KEY: osd_devices}
        domain_settings = {'domain-settings': osd_tmpl}
        inventory = {'node-templates': {'ceph-osd': domain_settings},
                     'nodes': {'ceph-osd': ['1', '2', '3', '4', '5', '6']}}

        # Test case when a each template has the same number of devices
        count = test_mod._get_osd_count(inventory)
        self.assertEqual(count, 30)

    def test_validate_devices_lists(self):
        devices = ['/dev/sde',
                   '/dev/sdf',
                   '/dev/sdg',
                   '/dev/sdh',
                   '/dev/sdi']
        # Test where the lists are equal
        osd_tmpls = [{test_mod.OSD_DEVICE_KEY: devices}]
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        test_mod._validate_devices_lists(osd_tmpls,
                                         test_mod.OSD_DEVICE_KEY)
        # Test where one list on one host is shorter
        osd_tmpls = [{test_mod.OSD_DEVICE_KEY: devices}]
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        devices2 = devices[:-2]
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices2)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls,
                          test_mod.OSD_DEVICE_KEY)

        # Test where one of the lists is longer
        osd_tmpls = [{test_mod.OSD_DEVICE_KEY: devices}]
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        devices2 = copy.deepcopy(devices).append('somethingMore')
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices2)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls,
                          test_mod.OSD_DEVICE_KEY)

        # Test where one of the lists has a different value
        osd_tmpls = [{test_mod.OSD_DEVICE_KEY: devices}]
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})
        devices2 = copy.deepcopy(devices)
        devices2[4] = '/different'
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices2)})
        osd_tmpls.append({test_mod.OSD_DEVICE_KEY: copy.deepcopy(devices)})

        self.assertRaises(test_mod.InvalidDeviceList,
                          test_mod._validate_devices_lists, osd_tmpls,
                          test_mod.OSD_DEVICE_KEY)

    def test_generate_journal_device_list(self):
        # Test one journal
        journal_d_list = ['a']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 10)
        self.assertEqual(['a'] * 10, ret_val)

        # Test equal division with 2 journals
        journal_d_list = ['a', 'b']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 10)
        self.assertEqual(['a'] * 5 + ['b'] * 5, ret_val)

        # Test equal division with 3 journals
        journal_d_list = ['a', 'b', 'c']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 12)
        self.assertEqual(['a'] * 4 + ['b'] * 4 + ['c'] * 4, ret_val)

        # Test unequal division with 3 journals
        journal_d_list = ['a', 'b', 'c']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 14)
        self.assertEqual(['a'] * 5 + ['b'] * 5 + ['c'] * 4, ret_val)

        # Test unequal division 5 journals with 3 remainder
        journal_d_list = ['a', 'b', 'c', 'd', 'e']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 18)
        self.assertEqual(['a'] * 4 + ['b'] * 4 + ['c'] * 4 + ['d'] * 3 +
                         ['e'] * 3, ret_val)

        # Test unequal division 5 journals with 4 remainder
        journal_d_list = ['a', 'b', 'c', 'd', 'e']
        ret_val = test_mod._generate_journal_device_list(journal_d_list, 19)
        self.assertEqual(['a'] * 4 + ['b'] * 4 + ['c'] * 4 + ['d'] * 4 +
                         ['e'] * 3, ret_val)

    def test_calculate_pg_count(self):
        # Input / output values verfied with pg calc web site
        self.assertEqual(256, test_mod._calculate_pg_count(36, .25, 100))
        self.assertEqual(512, test_mod._calculate_pg_count(36, .25, 200))
        self.assertEqual(1024, test_mod._calculate_pg_count(36, .25, 300))
        self.assertEqual(512, test_mod._calculate_pg_count(36, .40, 100))
        self.assertEqual(256, test_mod._calculate_pg_count(15, .40, 100))
        # Test a very small cluster with .001
        self.assertEqual(4, test_mod._calculate_pg_count(8, .001, 100))

    @mock.patch(TEST_MODULE_STRING + '._calculate_pg_count')
    @mock.patch(TEST_MODULE_STRING + '._get_osd_count')
    def test_get_openstack_pools(self, osd_count, pg_count):
        osd_count.return_value = 50
        pg_count.return_value = 512
        inventory = {}
        pools = test_mod._get_openstack_pools(inventory, 100, 15, 25, 60)

        pg_count.assert_has_calls([mock.call(50, .15, 100),
                                   mock.call(50, .25, 100),
                                   mock.call(50, .60, 100)],
                                  any_order=True)
        self.assertEqual(osd_count.call_count, 1)

        v_pools = {'openstack_glance_pool': {'name': 'images',
                                             'pg_num': 512},
                   'openstack_nova_pool': {'name': 'vms',
                                           'pg_num': 512},
                   'openstack_cinder_pool': {'name': 'volumes',
                                             'pg_num': 512},
                   }

        self.assertDictEqual(pools, v_pools)

    @mock.patch(TEST_MODULE_STRING + '._generate_journal_device_list')
    def test_generate_osds_vars(self, gen_journal_list):
        # Test with journal list:
        inventory = {'node-templates':
                     {'ceph-osd': {'domain-settings':
                                   {test_mod.OSD_DEVICE_KEY: ['a'],
                                    test_mod.JOURNAL_DEVICE_KEY: ['b', 'c']}}}}
        gen_journal_list.return_value = ['d']
        ret_vars = test_mod._generate_osds_vars(inventory)
        verify_vars = {'raw_multi_journal': True,
                       'raw_journal_devices': ['d'],
                       'devices': ['a']}
        self.assertDictEqual(ret_vars, verify_vars)

        # Test with co-located journals
        osd_template = {'ceph-osd': {'domain-settings':
                                     {test_mod.OSD_DEVICE_KEY: ['a', 'b']}}}
        inventory = {'node-templates': osd_template}
        gen_journal_list.return_value = ['d']
        ret_vars = test_mod._generate_osds_vars(inventory)
        verify_vars = {'journal_collocation': True,
                       'devices': ['a', 'b']}
        self.assertDictEqual(ret_vars, verify_vars)

    def test_generate_hosts_file(self):
        the_nodes = {'controllers': [{'hostname': 'controller1',
                                      'openstack-stg-addr': '172.29.244.2'},
                                     {'hostname': 'controller2',
                                      'openstack-stg-addr': '172.29.244.3'},
                                     {'hostname': 'controller3',
                                      'openstack-stg-addr': '172.29.244.4'}],
                     'ceph-osd': [{'hostname': 'ceph-osd1',
                                   'openstack-stg-addr': '172.29.244.5'},
                                  {'hostname': 'ceph-osd2',
                                   'openstack-stg-addr': '172.29.244.6'},
                                  {'hostname': 'ceph-osd3',
                                   'openstack-stg-addr':
                                   '172.29.244.7'}]}
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'nodes': the_nodes}
        hosts_file = test_mod._generate_hosts_file({'nodes': the_nodes})
        expected_file = ('[mons]\n'
                         '172.29.244.2\n'
                         '172.29.244.3\n'
                         '172.29.244.4\n'
                         '\n[osds]\n'
                         '172.29.244.5\n'
                         '172.29.244.6\n'
                         '172.29.244.7')
        self.assertEqual(hosts_file, expected_file)
        ref_arch = ['ceph-standalone']
        the_nodes = {'controllers': [{'hostname': 'controller1',
                                      'ceph-public-storage-addr':
                                      '172.29.244.2'},
                                     {'hostname': 'controller2',
                                      'ceph-public-storage-addr':
                                      '172.29.244.3'},
                                     {'hostname': 'controller3',
                                      'ceph-public-storage-addr':
                                      '172.29.244.4'}],
                     'ceph-osd': [{'hostname': 'ceph-osd1',
                                   'ceph-public-storage-addr':
                                   '172.29.244.5'},
                                  {'hostname': 'ceph-osd2',
                                   'ceph-public-storage-addr':
                                   '172.29.244.6'},
                                  {'hostname': 'ceph-osd3',
                                   'ceph-public-storage-addr':
                                   '172.29.244.7'}]}
        inventory = {'networks': {'ceph-public-storage':
                                  {'addr': '172.26.244.0/22',
                                   'eth-port': 'eth11'}},
                     'reference-architecture': ref_arch,
                     'nodes': the_nodes}
        hosts_file = test_mod._generate_hosts_file(inventory)
        expected_file = ('[mons]\n'
                         '172.29.244.2\n'
                         '172.29.244.3\n'
                         '172.29.244.4\n'
                         '\n[osds]\n'
                         '172.29.244.5\n'
                         '172.29.244.6\n'
                         '172.29.244.7')
        self.assertEqual(hosts_file, expected_file)

    @mock.patch(TEST_MODULE_STRING + '._write_string')
    @mock.patch(TEST_MODULE_STRING + '._write_yml')
    @mock.patch(TEST_MODULE_STRING + '._generate_hosts_file')
    @mock.patch(TEST_MODULE_STRING + '._generate_osds_vars')
    @mock.patch(TEST_MODULE_STRING + '._generate_all_vars')
    @mock.patch(TEST_MODULE_STRING + '._load_yml')
    def test_generate_files(self, load_yml, all_vars, osds, hosts,
                            write_yml, write_string):
        # Test successful path
        inventory_file = '/test/inventory_file'
        root_dir = '/root_dir'
        inventory_contents = {'node-templates': {'ceph-osd': 'osdhosts'}}
        load_yml.return_value = inventory_contents
        test_mod.generate_files(root_dir, inventory_file, 200, 1, 1, 1)
        load_yml.assert_called_once_with(inventory_file)
        all_vars.assert_called_once_with(inventory_contents, 200, 1, 1, 1)
        osds.assert_called_once_with(inventory_contents)
        write_yml.assert_has_calls(
            [mock.call(root_dir + os.path.sep + 'group_vars' +
                       os.path.sep + 'all', all_vars.return_value),
             mock.call(root_dir + os.path.sep + 'group_vars' +
                       os.path.sep + 'osds', osds.return_value)])
        write_string.assert_called_once_with(root_dir + os.path.sep +
                                             'ceph-hosts', hosts.return_value)

#     @mock.patch('generate_ceph_ansible_input._write_string')
#     @mock.patch('generate_ceph_ansible_input._write_yml')
#     def test_generate_files_real_inventory(self, write_yml, write_string):
#         # Test successful path
#         inventory_file = ''
#         root_dir = 'c:\\a_ulysses\\workspace\\ulysses\\tests\\output'
#         test_mod.generate_files(root_dir, inventory_file, 200)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
