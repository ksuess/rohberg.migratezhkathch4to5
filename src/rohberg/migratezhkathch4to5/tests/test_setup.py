# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from rohberg.migratezhkathch4to5.testing import ROHBERG_MIGRATEZHKATHCH4TO5_INTEGRATION_TESTING  # noqa

import unittest


class TestSetup(unittest.TestCase):
    """Test that rohberg.migratezhkathch4to5 is properly installed."""

    layer = ROHBERG_MIGRATEZHKATHCH4TO5_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if rohberg.migratezhkathch4to5 is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'rohberg.migratezhkathch4to5'))

    def test_browserlayer(self):
        """Test that IRohbergMigratezhkathch4To5Layer is registered."""
        from rohberg.migratezhkathch4to5.interfaces import (
            IRohbergMigratezhkathch4To5Layer)
        from plone.browserlayer import utils
        self.assertIn(
            IRohbergMigratezhkathch4To5Layer,
            utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = ROHBERG_MIGRATEZHKATHCH4TO5_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.installer.uninstallProducts(['rohberg.migratezhkathch4to5'])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if rohberg.migratezhkathch4to5 is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'rohberg.migratezhkathch4to5'))

    def test_browserlayer_removed(self):
        """Test that IRohbergMigratezhkathch4To5Layer is removed."""
        from rohberg.migratezhkathch4to5.interfaces import \
            IRohbergMigratezhkathch4To5Layer
        from plone.browserlayer import utils
        self.assertNotIn(
            IRohbergMigratezhkathch4To5Layer,
            utils.registered_layers())
