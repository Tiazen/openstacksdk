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

import mock
import munch
import testtools

import openstack
from openstack.cloud import exc
from openstack.cloud import meta
from openstack.config import cloud_config
from openstack.tests import fakes
from openstack.tests.unit import base


class TestOperatorCloud(base.RequestsMockTestCase):

    def setUp(self):
        super(TestOperatorCloud, self).setUp()

    def test_operator_cloud(self):
        self.assertIsInstance(self.op_cloud, openstack.OperatorCloud)

    @mock.patch.object(openstack.OperatorCloud, 'ironic_client')
    def test_list_nics(self, mock_client):
        port1 = fakes.FakeMachinePort(1, "aa:bb:cc:dd", "node1")
        port2 = fakes.FakeMachinePort(2, "dd:cc:bb:aa", "node2")
        port_list = [port1, port2]
        port_dict_list = meta.obj_list_to_munch(port_list)

        mock_client.port.list.return_value = port_list
        nics = self.op_cloud.list_nics()

        self.assertTrue(mock_client.port.list.called)
        self.assertEqual(port_dict_list, nics)

    @mock.patch.object(openstack.OperatorCloud, 'ironic_client')
    def test_list_nics_failure(self, mock_client):
        mock_client.port.list.side_effect = Exception()
        self.assertRaises(exc.OpenStackCloudException,
                          self.op_cloud.list_nics)

    @mock.patch.object(openstack.OperatorCloud, 'ironic_client')
    def test_list_nics_for_machine(self, mock_client):
        mock_client.node.list_ports.return_value = []
        self.op_cloud.list_nics_for_machine("123")
        mock_client.node.list_ports.assert_called_with(node_id="123")

    @mock.patch.object(openstack.OperatorCloud, 'ironic_client')
    def test_list_nics_for_machine_failure(self, mock_client):
        mock_client.node.list_ports.side_effect = Exception()
        self.assertRaises(exc.OpenStackCloudException,
                          self.op_cloud.list_nics_for_machine, None)

    @mock.patch.object(openstack.OpenStackCloud, '_image_client')
    def test_get_image_name(self, mock_client):

        fake_image = munch.Munch(
            id='22',
            name='22 name',
            status='success')
        mock_client.get.return_value = [fake_image]
        self.assertEqual('22 name', self.op_cloud.get_image_name('22'))
        self.assertEqual('22 name', self.op_cloud.get_image_name('22 name'))

    @mock.patch.object(openstack.OpenStackCloud, '_image_client')
    def test_get_image_id(self, mock_client):

        fake_image = munch.Munch(
            id='22',
            name='22 name',
            status='success')
        mock_client.get.return_value = [fake_image]
        self.assertEqual('22', self.op_cloud.get_image_id('22'))
        self.assertEqual('22', self.op_cloud.get_image_id('22 name'))

    @mock.patch.object(cloud_config.CloudConfig, 'get_endpoint')
    def test_get_session_endpoint_provided(self, fake_get_endpoint):
        fake_get_endpoint.return_value = 'http://fake.url'
        self.assertEqual(
            'http://fake.url', self.op_cloud.get_session_endpoint('image'))

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_get_session_endpoint_session(self, get_session_mock):
        session_mock = mock.Mock()
        session_mock.get_endpoint.return_value = 'http://fake.url'
        get_session_mock.return_value = session_mock
        self.assertEqual(
            'http://fake.url', self.op_cloud.get_session_endpoint('image'))

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_get_session_endpoint_exception(self, get_session_mock):
        class FakeException(Exception):
            pass

        def side_effect(*args, **kwargs):
            raise FakeException("No service")
        session_mock = mock.Mock()
        session_mock.get_endpoint.side_effect = side_effect
        get_session_mock.return_value = session_mock
        self.op_cloud.name = 'testcloud'
        self.op_cloud.region_name = 'testregion'
        with testtools.ExpectedException(
                exc.OpenStackCloudException,
                "Error getting image endpoint on testcloud:testregion:"
                " No service"):
            self.op_cloud.get_session_endpoint("image")

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_get_session_endpoint_unavailable(self, get_session_mock):
        session_mock = mock.Mock()
        session_mock.get_endpoint.return_value = None
        get_session_mock.return_value = session_mock
        image_endpoint = self.op_cloud.get_session_endpoint("image")
        self.assertIsNone(image_endpoint)

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_get_session_endpoint_identity(self, get_session_mock):
        session_mock = mock.Mock()
        get_session_mock.return_value = session_mock
        self.op_cloud.get_session_endpoint('identity')
        kwargs = dict(
            interface='public', region_name='RegionOne',
            service_name=None, service_type='identity')

        session_mock.get_endpoint.assert_called_with(**kwargs)

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_has_service_no(self, get_session_mock):
        session_mock = mock.Mock()
        session_mock.get_endpoint.return_value = None
        get_session_mock.return_value = session_mock
        self.assertFalse(self.op_cloud.has_service("image"))

    @mock.patch.object(cloud_config.CloudConfig, 'get_session')
    def test_has_service_yes(self, get_session_mock):
        session_mock = mock.Mock()
        session_mock.get_endpoint.return_value = 'http://fake.url'
        get_session_mock.return_value = session_mock
        self.assertTrue(self.op_cloud.has_service("image"))

    def test_list_hypervisors(self):
        '''This test verifies that calling list_hypervisors results in a call
        to nova client.'''
        self.register_uris([
            dict(method='GET',
                 uri=self.get_mock_url(
                     'compute', 'public', append=['os-hypervisors', 'detail']),
                 json={'hypervisors': [
                     fakes.make_fake_hypervisor('1', 'testserver1'),
                     fakes.make_fake_hypervisor('2', 'testserver2'),
                 ]}),
        ])

        r = self.op_cloud.list_hypervisors()

        self.assertEqual(2, len(r))
        self.assertEqual('testserver1', r[0]['hypervisor_hostname'])
        self.assertEqual('testserver2', r[1]['hypervisor_hostname'])

        self.assert_calls()
