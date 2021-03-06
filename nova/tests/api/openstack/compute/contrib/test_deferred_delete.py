# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import webob

from nova.api.openstack.compute.contrib import deferred_delete
from nova.api.openstack.compute.plugins.v3 import deferred_delete as dd_v21
from nova.compute import api as compute_api
from nova import context
from nova import exception
from nova import test
from nova.tests.api.openstack import fakes


class FakeRequest(object):
    def __init__(self, context):
        self.environ = {'nova.context': context}


class DeferredDeleteExtensionTestV21(test.NoDBTestCase):
    ext_ver = dd_v21.DeferredDeleteController

    def setUp(self):
        super(DeferredDeleteExtensionTestV21, self).setUp()
        self.fake_input_dict = {}
        self.fake_uuid = 'fake_uuid'
        self.fake_context = context.RequestContext('fake', 'fake')
        self.fake_req = FakeRequest(self.fake_context)
        self.extension = self.ext_ver()

    def test_force_delete(self):
        self.mox.StubOutWithMock(compute_api.API, 'get')
        self.mox.StubOutWithMock(compute_api.API, 'force_delete')

        fake_instance = 'fake_instance'

        compute_api.API.get(self.fake_context, self.fake_uuid,
                            expected_attrs=None,
                            want_objects=True).AndReturn(fake_instance)
        compute_api.API.force_delete(self.fake_context, fake_instance)

        self.mox.ReplayAll()
        res = self.extension._force_delete(self.fake_req, self.fake_uuid,
                                           self.fake_input_dict)
        self.assertEqual(res.status_int, 202)

    def test_force_delete_instance_not_found(self):
        self.mox.StubOutWithMock(compute_api.API, 'get')

        compute_api.API.get(self.fake_context, self.fake_uuid,
                            expected_attrs=None,
                            want_objects=True).AndRaise(
            exception.InstanceNotFound(instance_id='instance-0000'))

        self.mox.ReplayAll()
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.extension._force_delete,
                          self.fake_req,
                          self.fake_uuid,
                          self.fake_input_dict)

    @mock.patch.object(compute_api.API, 'get')
    @mock.patch.object(compute_api.API, 'force_delete',
                side_effect=exception.InstanceIsLocked(
                    instance_uuid='fake_uuid'))
    def test_force_delete_instance_locked(self, mock_force_delete, mock_get):
        req = fakes.HTTPRequest.blank('/v2/fake/servers/fake_uuid/action')
        ex = self.assertRaises(webob.exc.HTTPConflict,
                            self.extension._force_delete,
                            req, 'fake_uuid', '')
        self.assertIn('Instance fake_uuid is locked', ex.explanation)

    def test_restore(self):
        self.mox.StubOutWithMock(compute_api.API, 'get')
        self.mox.StubOutWithMock(compute_api.API, 'restore')

        fake_instance = 'fake_instance'

        compute_api.API.get(self.fake_context, self.fake_uuid,
                            expected_attrs=None,
                            want_objects=True).AndReturn(fake_instance)
        compute_api.API.restore(self.fake_context, fake_instance)

        self.mox.ReplayAll()
        res = self.extension._restore(self.fake_req, self.fake_uuid,
                                      self.fake_input_dict)
        self.assertEqual(res.status_int, 202)

    def test_restore_instance_not_found(self):
        self.mox.StubOutWithMock(compute_api.API, 'get')

        compute_api.API.get(self.fake_context, self.fake_uuid,
                            expected_attrs=None, want_objects=True).AndRaise(
            exception.InstanceNotFound(instance_id='instance-0000'))

        self.mox.ReplayAll()
        self.assertRaises(webob.exc.HTTPNotFound, self.extension._restore,
                          self.fake_req, self.fake_uuid,
                          self.fake_input_dict)

    def test_restore_raises_conflict_on_invalid_state(self):
        self.mox.StubOutWithMock(compute_api.API, 'get')
        self.mox.StubOutWithMock(compute_api.API, 'restore')

        fake_instance = 'fake_instance'
        exc = exception.InstanceInvalidState(attr='fake_attr',
                state='fake_state', method='fake_method',
                instance_uuid='fake')

        compute_api.API.get(self.fake_context, self.fake_uuid,
                            expected_attrs=None,
                            want_objects=True).AndReturn(fake_instance)
        compute_api.API.restore(self.fake_context, fake_instance).AndRaise(
                exc)

        self.mox.ReplayAll()
        self.assertRaises(webob.exc.HTTPConflict, self.extension._restore,
                self.fake_req, self.fake_uuid, self.fake_input_dict)


class DeferredDeleteExtensionTestV2(DeferredDeleteExtensionTestV21):
    ext_ver = deferred_delete.DeferredDeleteController
