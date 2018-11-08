# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import rohberg.migratezhkathch4to5


class RohbergMigratezhkathch4To5Layer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=rohberg.migratezhkathch4to5)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'rohberg.migratezhkathch4to5:default')


ROHBERG_MIGRATEZHKATHCH4TO5_FIXTURE = RohbergMigratezhkathch4To5Layer()


ROHBERG_MIGRATEZHKATHCH4TO5_INTEGRATION_TESTING = IntegrationTesting(
    bases=(ROHBERG_MIGRATEZHKATHCH4TO5_FIXTURE,),
    name='RohbergMigratezhkathch4To5Layer:IntegrationTesting',
)


ROHBERG_MIGRATEZHKATHCH4TO5_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(ROHBERG_MIGRATEZHKATHCH4TO5_FIXTURE,),
    name='RohbergMigratezhkathch4To5Layer:FunctionalTesting',
)


ROHBERG_MIGRATEZHKATHCH4TO5_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        ROHBERG_MIGRATEZHKATHCH4TO5_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='RohbergMigratezhkathch4To5Layer:AcceptanceTesting',
)
