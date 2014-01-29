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
        os.environ["REDIS_IMAGE"] = "redisapi"
        self.addCleanup(self.remove_env, "REDIS_IMAGE")
        from redisapi.managers import DockerManager
        self.manager = DockerManager()
        self.manager.client = mock.Mock()
        self.manager.health_checker = mock.Mock()

    def tearDown(self):
        self.manager.instances.remove()

    def test_hc(self):
        from redisapi.hc import FakeHealthCheck
        from redisapi.managers import DockerManager
        manager = DockerManager()
        self.assertIsInstance(manager.health_checker(), FakeHealthCheck)

    @mock.patch("pyzabbix.ZabbixAPI")
    def test_hc_zabbix(self, zabix_mock):
        os.environ["ZABBIX_URL"] = "url"
        os.environ["ZABBIX_USER"] = "url"
        os.environ["HEALTH_CHECKER"] = "zabbix"
        from redisapi.hc import ZabbixHealthCheck
        from redisapi.managers import DockerManager
        manager = DockerManager()
        self.assertIsInstance(manager.health_checker(), ZabbixHealthCheck)

    def test_add_instance(self):
        add_mock = mock.Mock()
        self.manager.health_checker.return_value = add_mock
        self.manager.client.create_container.return_value = {"Id": "12"}
        self.manager.client.inspect_container.return_value = {
            'NetworkSettings': {
                u'Ports': {u'6379/tcp': [{u'HostPort': u'49154'}]}}}

        self.manager.add_instance("name")

        self.manager.client.create_container.assert_called_with(
            self.manager.image_name,
            command="",
        )
        self.manager.client.start.assert_called_with(
            "12",
            port_bindings={6379: ('0.0.0.0',)}
        )
        add_mock.add.assert_called_with("localhost", u"49154")
        instance = self.manager.instances.find_one({"name": "name"})
        self.assertEqual(instance["name"], "name")
        self.assertEqual(instance["container_id"], "12")
        self.assertEqual(instance["host"], "localhost")
        self.assertEqual(instance["port"], u"49154")

    def test_remove_instance(self):
        remove_mock = mock.Mock()
        self.manager.health_checker.return_value = remove_mock
        instance = {
            'name': "name",
            'container_id': "12",
            'port': 123,
        }
        self.manager.instances.insert(instance)

        self.manager.remove_instance("name")

        remove_mock.remove.assert_called_with("localhost", 123)
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
            from redisapi.managers import DockerManager
            DockerManager()
        exc = cm.exception
        self.assertEqual(
            (u"You must define the REDIS_SERVER_HOST environment variable.",),
            exc.args,
        )

    def test_running_without_the_REDIS_IMAGE_variable(self):
        del os.environ["REDIS_IMAGE"]
        with self.assertRaises(Exception) as cm:
            from redisapi.managers import DockerManager
            DockerManager()
        exc = cm.exception
        self.assertEqual(
            (u"You must define the REDIS_IMAGE environment variable.",),
            exc.args,
        )

    @mock.patch("pymongo.MongoClient")
    def test_mongodb_host_environ(self, mongo_mock):
        from redisapi.managers import DockerManager
        DockerManager()
        mongo_mock.assert_called_with(host="localhost", port=27017)

        os.environ["MONGODB_HOST"] = "0.0.0.0"
        self.addCleanup(self.remove_env, "MONGODB_HOST")
        from redisapi.managers import DockerManager
        DockerManager()
        mongo_mock.assert_called_with(host="0.0.0.0", port=27017)

    @mock.patch("pymongo.MongoClient")
    def test_mongodb_port_environ(self, mongo_mock):
        from redisapi.managers import DockerManager
        DockerManager()
        mongo_mock.assert_called_with(host='localhost', port=27017)

        os.environ["MONGODB_PORT"] = "3333"
        self.addCleanup(self.remove_env, "MONGODB_PORT")
        from redisapi.managers import DockerManager
        DockerManager()
        mongo_mock.assert_called_with(host='localhost', port=3333)
