# Copyright 2016,2017 IBM US, Inc.
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
        # verify_vars['ceph_stable_uca'] = True
        verify_vars['ceph_origin'] = 'distro'
        verify_vars['openstack_keys'] = os_keys
        verify_vars['openstack_pools'] = os_pools
        verify_vars['monitor_interface'] = 'br-storage'
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1, True)
        self._assert_invalid_config(ref_arch, verify_vars)
        self.assertDictEqual(verify_vars, all_vars)

        # Test again with cluster net set
        inventory['networks']['ceph-replication'] = {'addr': '172.29.100.0/22'}
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1, True)

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
        verify_vars = test_mod._init_default_values(inventory, False)
        verify_vars['delete_default_pool'] = False
        verify_vars['public_network'] = '172.26.244.0/22'
        verify_vars['cluster_network'] = '{{ public_network }}'
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1, False)
        self._assert_invalid_config(ref_arch, verify_vars)
        self.assertDictEqual(verify_vars, all_vars)

        # Test again with cluster net set
        inventory['networks']['ceph-replication'] = {'addr': '172.29.100.0/22'}
        all_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                               1, 1, 1, False)
        verify_vars['cluster_network'] = '172.29.100.0/22'
        self.assertDictEqual(verify_vars, all_vars)

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role',
                return_value=['ceph-osd'])
    def test_generate_priv_cloud_all_vars(self, template_names):
        os_config = False
        growth_factor = 200
        ref_arch = ['private-compute-cloud']
        inventory = {'networks': {'openstack-stg':
                                  {'addr': '172.29.244.0/22',
                                   'bridge': 'br-storage'}},
                     'reference-architecture': ref_arch}
        verify_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                                  1, 1, 1, os_config)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertNotIn('openstack_config', verify_vars)
        os_config = True
        inventory['node-templates'] = {'ceph-osd':
                                       {'domain-settings':
                                        {'osd-devices': {'/dev/sdb'}}}}
        inventory['nodes'] = {'controllers': [{'hostname': ['sm15']}],
                              'ceph-osd': [{'hostname': 'osd1',
                                            'ceph-public-storage-addr':
                                            '172.26.244.0/22'}]}
        verify_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                                  1, 1, 1, os_config)
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue('openstack_config', verify_vars)

    def test_generate_ceph_standalone_all_vars(self):
        os_config = False
        growth_factor = 200
        ref_arch = ['ceph-standalone']
        inventory = {'networks': {'ceph-public-storage':
                                  {'addr': '172.26.244.0/22',
                                   'eth-port': 'eth11'}},
                     'reference-architecture': ref_arch,
                     'nodes': {'controllers': [{'hostname': ['sm15']}],
                               'ceph-osd': [{'hostname': 'osd1',
                                             'ceph-public-storage-addr':
                                             '172.26.244.0/22'}]}}
        verify_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                                  1, 1, 1, os_config)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertNotIn('openstack_config', verify_vars)
        os_config = True
        inventory['node-templates'] = {'ceph-osd':
                                       {'domain-settings':
                                        {'osd-devices': {'/dev/sdb'}}}}
        verify_vars = test_mod._generate_all_vars(inventory, growth_factor,
                                                  1, 1, 1, os_config)
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue('openstack_config', verify_vars)

    def _assert_invalid_config(self, ref_arch, ref_config_settings):
        if 'private-compute-cloud' in ref_arch:
            self.assertIn('openstack_keys', ref_config_settings)
            self.assertIn('openstack_pools', ref_config_settings)
            self.assertIn('openstack_config', ref_config_settings)
        elif 'ceph-standalone' in ref_arch:
            self.assertNotIn('openstack_config', ref_config_settings)
            self.assertNotIn('openstack_keys', ref_config_settings)
            self.assertNotIn('openstack_pools', ref_config_settings)

    def test_init_ceph_standalone_os_config(self):
        os_config = True
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'networks': {'ceph-public-storage': {'eth-port':
                                                          'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory, os_config)
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue('openstack_config', verify_vars)

        os_config = False
        verify_vars = test_mod._init_default_values(inventory, os_config)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertNotIn('openstack_config', verify_vars)

    def test_init_ceph_priv_cloud_os_config(self):
        os_config = True
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'networks': {'openstack-stg': {'bridge': 'br-storage',
                                                    'eth-port': 'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory, os_config)
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue('openstack_config' in verify_vars)

        os_config = False
        verify_vars = test_mod._init_default_values(inventory, os_config)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertNotIn('openstack_config', verify_vars)

    def test_init_default_values(self):
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'networks': {'openstack-stg': {'bridge': 'br-storage',
                                                    'eth-port': 'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory, True)
        self.assertEquals(verify_vars['monitor_interface'], 'br-storage')
        self.assertTrue(verify_vars['delete_default_pool'])
        self.assertTrue(verify_vars['openstack_config'])
        # self.assertTrue(verify_vars['ceph_stable_uca'])
        self.assertEqual(verify_vars['ceph_origin'], 'distro')
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'networks': {'ceph-public-storage': {'eth-port':
                                                          'eth11'}}}
        verify_vars = test_mod._init_default_values(inventory, False)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertEquals(verify_vars['monitor_interface'], 'eth11')
        # Test bonded network
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'networks': {'ceph-public-storage': {'bond':
                                                          'jamesbond'}}}
        verify_vars = test_mod._init_default_values(inventory, False)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertEquals(verify_vars['monitor_interface'], 'jamesbond')

        # Test deployment environment
        test_env = {'a': 'b',
                    'c': 'd'}
        inventory = {'reference-architecture': ['ceph-standalone'],
                     'networks': {'ceph-public-storage': {'bond':
                                                          'jamesbond'}},
                     'deployment-environment': test_env}
        verify_vars = test_mod._init_default_values(inventory, False)
        self.assertFalse(verify_vars['delete_default_pool'])
        self.assertEquals(verify_vars['monitor_interface'], 'jamesbond')
        self.assertEqual(verify_vars['deployment_environment_variables'],
                         test_env)

    def test_get_storage_network(self):
        inventory = {'reference-architecture': ['ceph-standalone']}
        self.assertEqual(test_mod._get_storage_network(inventory),
                         'ceph-public-storage')
        inventory = {'reference-architecture': ['private-compute-cloud']}
        self.assertEqual(test_mod._get_storage_network(inventory),
                         'openstack-stg')

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role',
                return_value=['ceph-osd'])
    def test_get_osd_ips(self, template_names):
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

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role',
                return_value=['controllers'])
    def test_get_mon_ips(self, template_names):
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

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role',
                return_value=['ceph-osd'])
    def test_get_osd_count(self, template_names):
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

        # Test 3 ceph-osd templates
        template_names.return_value = ['ceph-osd', 'osd2', 'osd3']
        inventory = {'node-templates': {'ceph-osd': domain_settings,
                                        'osd2': domain_settings,
                                        'osd3': domain_settings},
                     'nodes': {'ceph-osd': ['1', '2', '3', '4', '5', '6'],
                               'osd2': ['a', 'b', 'c', 'd', 'e', 'f'],
                               'osd3': ['g', 'h', 'i', 'j', 'k', 'l']}}
        count = test_mod._get_osd_count(inventory)
        self.assertEqual(count, 90)

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

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role',
                return_value=['ceph-osd'])
    @mock.patch(TEST_MODULE_STRING + '._generate_journal_device_list')
    def test_generate_osds_vars(self, gen_journal_list, template_names):
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
        # Test private compute flavors with original template = role
        templates = {'controllers': {},
                     'ceph-osd': {}}
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
                     'nodes': the_nodes,
                     'node-templates': templates}
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
        # Test ceph standalone with original template = role
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
                     'nodes': the_nodes,
                     'node-templates': templates}
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

        # Test converged node
        templates = {'converged': {
                     test_mod.TEMPLATE_ROLES_KEY: ['ceph-monitor',
                                                   'ceph-osd']}}
        the_nodes = {'converged': [{'hostname': 'controller1',
                                    'openstack-stg-addr': '172.29.244.2'},
                                   {'hostname': 'controller2',
                                    'openstack-stg-addr': '172.29.244.3'},
                                   {'hostname': 'controller3',
                                    'openstack-stg-addr': '172.29.244.4'}]}
        inventory = {'reference-architecture': ['private-compute-cloud'],
                     'nodes': the_nodes,
                     'node-templates': templates}
        hosts_file = test_mod._generate_hosts_file(inventory)
        expected_file = ('[mons]\n'
                         '172.29.244.2\n'
                         '172.29.244.3\n'
                         '172.29.244.4\n'
                         '\n[osds]\n'
                         '172.29.244.2\n'
                         '172.29.244.3\n'
                         '172.29.244.4')
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
        test_mod.generate_files(root_dir, inventory_file, 200, 1, 1, 1, True)
        load_yml.assert_called_once_with(inventory_file)
        all_vars.assert_called_once_with(inventory_contents, 200, 1, 1, 1,
                                         True)
        osds.assert_called_once_with(inventory_contents)
        write_yml.assert_has_calls(
            [mock.call(root_dir + os.path.sep + 'group_vars' +
                       os.path.sep + 'all', all_vars.return_value),
             mock.call(root_dir + os.path.sep + 'group_vars' +
                       os.path.sep + 'osds', osds.return_value)])
        write_string.assert_called_once_with(root_dir + os.path.sep +
                                             'ceph-hosts', hosts.return_value)

    def test_get_node_template_names_for_role(self):
        # Test backward compatibility
        templates = {'controllers': {},
                     'ceph-osd': {},
                     'compute': {}}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-monitor')
        self.assertEqual(ret, ['controllers'])
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-osd')
        self.assertEqual(ret, ['ceph-osd'])

        # Test converged ceph monitor and osd
        templates = {'converged': {
            test_mod.TEMPLATE_ROLES_KEY: ['ceph-monitor',
                                          'ceph-osd']}}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-monitor')
        self.assertEqual(ret, ['converged'])
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-osd')
        self.assertEqual(ret, ['converged'])

        # Test separate monitor and OSD
        templates = {'mon': {test_mod.TEMPLATE_ROLES_KEY: ['ceph-monitor']},
                     'osd': {test_mod.TEMPLATE_ROLES_KEY: ['ceph-osd']}}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-monitor')
        self.assertEqual(ret, ['mon'])
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-osd')
        self.assertEqual(ret, ['osd'])

        # Test multiple mon templates (controller and other)
        mon_only = {test_mod.TEMPLATE_ROLES_KEY: ['ceph-monitor']}
        templates = {'controllers': mon_only,
                     'monType1': mon_only,
                     'monType2': mon_only}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-monitor')
        self.assertItemsEqual(ret, ['controllers', 'monType1', 'monType2'])

        # Test multiple mon templates without controllers in the picture
        mon_only = {test_mod.TEMPLATE_ROLES_KEY: ['ceph-monitor']}
        templates = {'monType1': mon_only,
                     'monType2': mon_only}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-monitor')
        self.assertItemsEqual(ret, ['monType1', 'monType2'])

        # Test multiple OSD templates without ceph-osd template in the picture
        osd_only = {test_mod.TEMPLATE_ROLES_KEY: ['ceph-osd']}
        templates = {'osdType1': osd_only,
                     'osdType2': osd_only}
        inv = {'node-templates': templates}
        ret = test_mod._get_node_template_names_for_role(inv,
                                                         'ceph-osd')
        self.assertItemsEqual(ret, ['osdType1', 'osdType2'])

    @mock.patch(TEST_MODULE_STRING + '._get_node_template_names_for_role')
    def test_get_nodes_for_role(self, templs_for_roles):

        nodes = {'noise': '',
                 'noise2': '',
                 'target1': ['n1', 'n2', 'n3'],
                 'target2': ['n4'],
                 'noise3': '',
                 'target3': ['n5', 'n6']}

        inventory = {'nodes': nodes}
        # Test that if templates is passed it's used and
        # _get_node_template_names_for_role is not called
        ret = test_mod._get_nodes_for_role(inventory, 'junk', ['target1',
                                                               'target2',
                                                               'target3'])

        self.assertEqual(templs_for_roles.call_count, 0)
        self.assertItemsEqual(['n1', 'n2', 'n3', 'n4', 'n5', 'n6'], ret)
        # Test getting only 2 targets
        templs_for_roles.return_value = ['target2', 'target3']
        ret = test_mod._get_nodes_for_role(inventory, 'junk')
        templs_for_roles.assert_called_with(inventory, 'junk')
        self.assertItemsEqual(['n4', 'n5', 'n6'], ret)

        # Test getting single target
        templs_for_roles.reset_mock()
        templs_for_roles.return_value = ['target1']
        ret = test_mod._get_nodes_for_role(inventory, 'junk')
        templs_for_roles.assert_called_with(inventory, 'junk')
        self.assertItemsEqual(['n1', 'n2', 'n3'], ret)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
