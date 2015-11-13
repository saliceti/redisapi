# Copyright 2015 redisapi authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest
import mock
import os
import json

from redisapi.storage import Instance, MongoStorage


class DockerManagerTest(unittest.TestCase):

    def remove_env(self, env):
        if env in os.environ:
            del os.environ[env]

    def setUp(self):
        os.environ["SENTINEL_HOSTS"] = '["http://host1.com:4243", \
            "http://localhost:4243", "http://host2.com:4243"]'
        self.addCleanup(self.remove_env, "SENTINEL_HOSTS")
        os.environ["REDIS_SERVER_HOST"] = "localhost"
        self.addCleanup(self.remove_env, "REDIS_SERVER_HOST")
        os.environ["REDIS_IMAGE"] = "redisapi"
        self.addCleanup(self.remove_env, "REDIS_IMAGE")
        os.environ["DOCKER_HOSTS"] = '["http://host1.com:4243", \
            "http://localhost:4243"]'
        self.addCleanup(self.remove_env, "DOCKER_HOSTS")
        from redisapi.managers import DockerManager
        self.manager = DockerManager()
        client_mock = mock.Mock()
        client_mock.return_value = mock.Mock()
        self.manager.client = client_mock
        self.manager.health_checker = mock.Mock()
        self.storage = MongoStorage()

    def tearDown(self):
        self.storage.db().instances.remove()

    def test_client(self):
        os.environ["DOCKER_HOSTS"] = '["http://host1.com:4243", \
            "http://localhost:4243"]'
        self.addCleanup(self.remove_env, "DOCKER_HOSTS")
        from redisapi.managers import DockerManager
        manager = DockerManager()
        client = manager.client()
        hosts = ["http://host1.com:4243", "http://localhost:4243"]
        self.assertIn(client.base_url, hosts)

    def test_extract_hostname(self):
        from redisapi.managers import DockerManager
        manager = DockerManager()
        url = manager.extract_hostname("http://host.com:4243")
        self.assertEqual(url, "host.com")

    def test_docker_host_from_hostname(self):
        from redisapi.managers import DockerManager
        manager = DockerManager()
        url = manager.docker_url_from_hostname("host.com")
        self.assertEqual(url, "http://host.com:4243")

    def test_client_with_value(self):
        from redisapi.managers import DockerManager
        manager = DockerManager()
        host = "http://myhost.com:4243"
        client = manager.client(host=host)
        self.assertEqual(client.base_url, host)

    def test_hc(self):
        from redisapi.hc import FakeHealthCheck
        from redisapi.managers import DockerManager
        manager = DockerManager()
        self.assertIsInstance(manager.health_checker(), FakeHealthCheck)

    def test_docker_hosts(self):
        hosts = ["http://host1.com:4243", "http://localhost:4243"]
        self.assertListEqual(self.manager.docker_hosts, hosts)

    @mock.patch("pyzabbix.ZabbixAPI")
    def test_hc_zabbix(self, zabix_mock):
        os.environ["ZABBIX_URL"] = "url"
        os.environ["ZABBIX_USER"] = "url"
        os.environ["ZABBIX_PASSWORD"] = "url"
        os.environ["HEALTH_CHECKER"] = "zabbix"
        self.addCleanup(self.remove_env, "HEALTH_CHECKER")
        os.environ["ZABBIX_HOST"] = "2"
        os.environ["ZABBIX_INTERFACE"] = "1"
        from redisapi.hc import ZabbixHealthCheck
        from redisapi.managers import DockerManager
        manager = DockerManager()
        self.assertIsInstance(manager.health_checker(), ZabbixHealthCheck)

    def test_add_instance(self):
        add_mock = mock.Mock()
        self.manager.config_sentinels = mock.Mock()
        self.manager.health_checker.return_value = add_mock
        client_mock = mock.Mock()
        client_mock.return_value = mock.Mock(base_url="http://localhost:4243")
        self.manager.client = client_mock

        self.manager.client().create_container.return_value = {"Id": "12"}
        self.manager.client().inspect_container.return_value = {
            'NetworkSettings': {
                u'Ports': {u'6379/tcp': [{u'HostPort': u'49154'}]}}}

        self.manager.client().images.return_value = [
            {u'Created': 1446330175, u'Labels': None, u'VirtualSize': 1108935,
                u'ParentId': u'039b63dd2cbaa10d6015ea574392530571ed8d7b174090f032211285a71881d0',
                u'RepoTags': [u'busybox:latest'], u'RepoDigests': [],
                u'Id': u'c51f86c283408d1749d066333f7acd5d33b053b003a61ff6a7b36819ddcbc7b7',
                u'Size': 0}]
        instance = self.manager.add_instance("name")

        self.manager.client().pull.assert_called_with(self.manager.image_name)
        self.manager.client().pull.reset_mock()

        self.manager.client().images.return_value = [
            {u'Created': 1447094544, u'Labels': None, u'VirtualSize': 144105595,
                u'ParentId': u'c82e8df8f302be4b88963855bf2ad684f24ce94a260f76ed5d631ca7a5883153',
                u'RepoTags': [u'tsuru/bs:v1'], u'RepoDigests': [],
                u'Id': u'76ed3ae479104e6c8105a2da9d83d41bbde5e04493cd38a24dad213e6fa6d8c6',
                u'Size': 0},
            {u'Created': 1446330175, u'Labels': None, u'VirtualSize': 1108935,
                u'ParentId': u'039b63dd2cbaa10d6015ea574392530571ed8d7b174090f032211285a71881d0',
                u'RepoTags': [self.manager.image_name + ':latest'], u'RepoDigests': [],
                u'Id': u'c51f86c283408d1749d066333f7acd5d33b053b003a61ff6a7b36819ddcbc7b7',
                u'Size': 0}]
        instance = self.manager.add_instance("name")

        assert not self.manager.client().pull.called
        self.manager.client().pull.reset_mock()

        self.manager.client().images.return_value = [
            {u'Created': 1446330175, u'Labels': None, u'VirtualSize': 1108935,
                u'ParentId': u'039b63dd2cbaa10d6015ea574392530571ed8d7b174090f032211285a71881d0',
                u'RepoTags': [self.manager.image_name + ':v123'], u'RepoDigests': [],
                u'Id': u'c51f86c283408d1749d066333f7acd5d33b053b003a61ff6a7b36819ddcbc7b7',
                u'Size': 0}]
        instance = self.manager.add_instance("name")

        assert not self.manager.client().pull.called

        self.manager.client().create_container.assert_called_with(
            self.manager.image_name,
            command="",
            environment={'REDIS_PORT': 49153},
            ports=[49153]
        )
        self.manager.client().start.assert_called_with(
            "12",
            port_bindings={49153: ('0.0.0.0', 49153)}
        )
        add_mock.add.assert_called_with("localhost", 49153)
        endpoint = instance.endpoints[0]
        self.assertEqual(instance.name, "name")
        self.assertEqual(endpoint["container_id"], "12")
        self.assertEqual(endpoint["host"], "localhost")
        self.assertEqual(endpoint["port"], 49153)
        self.assertEqual(instance.plan, "basic")

        self.manager.config_sentinels.assert_called_with(
            "name", endpoint)

    def test_remove_instance(self):
        remove_mock = mock.Mock()
        self.manager.remove_from_sentinel = mock.Mock()
        self.manager.health_checker.return_value = remove_mock
        instance = Instance(
            name="name",
            plan="basic",
            endpoints=[{"host": "host", "port": 123, "container_id": "12"}],
        )
        self.storage.add_instance(instance)

        self.manager.remove_instance(instance)
        remove_mock.remove.assert_called_with("host", 123)
        self.manager.client.assert_called_with("http://host:4243")
        self.manager.client().stop.assert_called_with(
            instance.endpoints[0]["container_id"])
        self.manager.client().remove_container.assert_called(
            instance.endpoints[0]["container_id"])
        self.storage.remove_instance(instance)
        self.manager.remove_from_sentinel.assert_called_with(
            instance.name)

    def test_bind(self):
        instance = Instance(
            name="name",
            plan='basic',
            endpoints=[{"host": "localhost", "port": 4242,
                        "container_id": "12"}],
        )

        result = self.manager.bind(instance)

        self.assertEqual(result['REDIS_HOST'], "localhost")
        self.assertEqual(result['REDIS_PORT'], "4242")
        expected_redis = json.dumps(['localhost:4242'])
        expected_sentinels = json.dumps([
            u'http://host1.com:4243',
            u'http://localhost:4243',
            u'http://host2.com:4243'
        ])
        self.assertEqual(result['REDIS_HOSTS'], expected_redis)
        self.assertEqual(result['SENTINEL_HOSTS'], expected_sentinels)
        self.assertEqual(result['REDIS_MASTER'], instance.name)

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

    @mock.patch("redis.StrictRedis")
    def test_config_sentinels(self, redis_mock):
        master = {"host": "localhost", "port": "3333"}
        self.manager.config_sentinels("master_name", master)

        calls = []
        sentinels = [
            {"host": u"host1.com", "port": u"4243"},
            {"host": u"localhost", "port": u"4243"},
            {"host": u"host2.com", "port": u"4243"},
        ]
        for sentinel in sentinels:
            host, port = sentinel["host"], sentinel["port"]
            sentinel_calls = [
                mock.call(host=host, port=port),
                mock.call().sentinel(
                    'monitor', 'master_name', 'localhost', '3333', '1'),
                mock.call().sentinel(
                    'set', 'master_name', 'down-after-milliseconds', '5000'),
                mock.call().sentinel(
                    'set', 'master_name', 'failover-timeout', '60000'),
                mock.call().sentinel(
                    'set', 'master_name', 'parallel-syncs', '1'),
            ]
            calls.extend(sentinel_calls)

        redis_mock.assert_has_calls(calls)

    @mock.patch("redis.StrictRedis")
    def test_remove_from_sentinel(self, redis_mock):
        self.manager.remove_from_sentinel("master_name")

        calls = []
        sentinels = [
            {"host": u"host1.com", "port": u"4243"},
            {"host": u"localhost", "port": u"4243"},
            {"host": u"host2.com", "port": u"4243"},
        ]
        for sentinel in sentinels:
            host, port = sentinel["host"], sentinel["port"]
            sentinel_calls = [
                mock.call(host=host, port=port),
                mock.call().sentinel(
                    'remove', 'master_name'),
            ]
            calls.extend(sentinel_calls)

        redis_mock.assert_has_calls(calls)

    def test_port_range_start(self):
        self.assertEqual(49153, self.manager.port_range_start)

    def test_get_port_new_host(self):
        self.assertEqual(49153, self.manager.get_port_by_host("newhost"))

    def test_get_port_host_with_containers(self):
        instance = Instance(
            name="name",
            plan="basic",
            endpoints=[{"host": "newhost", "port": 49153,
                        "container_id": "12"}],
        )
        self.storage.add_instance(instance)
        self.assertEqual(49154, self.manager.get_port_by_host("newhost"))
