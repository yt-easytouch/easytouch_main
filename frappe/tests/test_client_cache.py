import time

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.redis_wrapper import _ClientCache

TEST_KEY = "42"


class TestClientCache(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.client_cache.delete_value(TEST_KEY)
		return super().setUp()

	def test_client_cache_is_used(self):
		frappe.client_cache.set_value(TEST_KEY, 42)
		frappe.client_cache.get_value(TEST_KEY)
		with self.assertRedisCallCounts(0):
			frappe.client_cache.get_value(TEST_KEY)

	def test_client_cache_is_updated_instantly_noloop(self):
		val = frappe.generate_hash()
		frappe.client_cache.set_value(TEST_KEY, val)
		with self.assertRedisCallCounts(0):  # Locally set value should not be invalidated.
			self.assertEqual(frappe.client_cache.get_value(TEST_KEY), val)

	def test_invalidation_from_another_client_works(self):
		val = frappe.generate_hash()
		frappe.client_cache.set_value(TEST_KEY, val)
		self.assertEqual(frappe.client_cache.get_value(TEST_KEY), val)

		# frappe.cache is our "another client"
		val = frappe.generate_hash()
		frappe.cache.set_value(TEST_KEY, val)
		# This is almost instant, but obviously not as fast as running the next instruction in
		# current thread. So we wait.
		time.sleep(0.1)

		with self.assertRedisCallCounts(1, exact=True):
			self.assertEqual(frappe.client_cache.get_value(TEST_KEY), val)

	def test_client_local_cache_ttl(self):
		c = _ClientCache(ttl=1)
		c.set_value(TEST_KEY, 42)
		with self.assertRedisCallCounts(0):
			c.get_value(TEST_KEY)
		time.sleep(1)

		with self.assertRedisCallCounts(1, exact=True):
			c.get_value(TEST_KEY)

	def test_client_cache_maxsize(self):
		c = _ClientCache(maxsize=2)
		c.set_value(TEST_KEY, 42)
		c.set_value(frappe.generate_hash(), 42)
		c.set_value(frappe.generate_hash(), 42)

		self.assertEqual(len(c.local_cache), 2)
