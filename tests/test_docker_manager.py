# Copyright 2014 redis-api authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest
import mock
import os


class DockerManagerTest(unittest.TestCase):

    def remove_env(self, env):
        if env in os.environ:
            del os.environ[env]

    def setUp(self):
        os.environ["REDIS_SERVER_HOST"] = "localhost"
        self.addCleanup(self.remove_env, "REDIS_SERVER_HOST")
        from managers import DockerManager
        self.manager = DockerManager()
        self.manager.client = mock.Mock()

    def tearDown(self):
        self.manager.instances.remove()

    def test_add_instance(self):
        self.manager.client.build.return_value = "12", ""
        self.manager.client.inspect_container.return_value = {
            'NetworkSettings': {
                u'Ports': {u'6379/tcp': [{u'HostPort': u'49154'}]}}}
        self.manager.add_instance("name")
        self.manager.client.build.assert_called()
        instance = self.manager.instances.find_one({"name": "name"})
        self.assertEqual(instance["name"], "name")
        self.assertEqual(instance["container_id"], "12")
        self.assertEqual(instance["host"], "0.0.0.0")
        self.assertEqual(instance["port"], u"49154")

    def test_remove_instance(self):
        instance = {
            'name': "name",
            'container_id': "12",
        }
        self.manager.instances.insert(instance)
        self.manager.remove_instance("name")
        self.manager.client.stop.assert_called_with(instance["container_id"])
        self.manager.client.remove_container.assert_called(
            instance["container_id"])
        lenght = self.manager.instances.find({"name": "name"}).count()
        self.assertEqual(lenght, 0)

    def test_bind(self):
        instance = {
            'name': "name",
            'container_id': "12",
            'host': 'localhost',
            'port': '4242',
        }
        self.manager.instances.insert(instance)
        result = self.manager.bind(name="name")
        self.assertEqual(result['REDIS_HOST'], instance['host'])
        self.assertEqual(result['REDIS_PORT'], instance['port'])

    def test_running_without_the_REDIS_SERVER_HOST_variable(self):
        del os.environ["REDIS_SERVER_HOST"]
        with self.assertRaises(Exception) as cm:
            from managers import DockerManager
            DockerManager()
        exc = cm.exception
        self.assertEqual(
            (u"You must define the REDIS_SERVER_HOST environment variable.",),
            exc.args,
        )