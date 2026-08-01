from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from .settings_checks import validate_production_network_settings


class ProductionNetworkSettingsValidationTests(SimpleTestCase):
    def test_debug_true_never_raises_even_when_wildcarded(self):
        # Local development is allowed to be permissive.
        validate_production_network_settings(True, [], [])
        validate_production_network_settings(True, ['*'], [])

    def test_debug_false_with_wildcard_allowed_hosts_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_network_settings(False, ['*'], ['https://portal.example.com'])

    def test_debug_false_with_empty_allowed_hosts_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_network_settings(False, [], ['https://portal.example.com'])

    def test_debug_false_with_empty_cors_origins_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_network_settings(False, ['api.example.com'], [])

    def test_debug_false_with_explicit_non_wildcard_values_passes(self):
        # Should not raise.
        validate_production_network_settings(
            False,
            ['api.example.com'],
            ['https://portal.example.com'],
        )
