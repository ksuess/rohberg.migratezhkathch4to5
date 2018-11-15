"""Define custom blueprints for zhkathch."""

from Acquisition import aq_inner
from Acquisition import aq_parent
from DateTime import DateTime
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Condition
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
from collective.transmogrifier.utils import traverse
from operator import itemgetter
from plone import api
from plone.api.exc import InvalidParameterError
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from zope.interface import classProvides

import pkg_resources


try:
    pkg_resources.get_distribution('plone.app.contenttypes')
except pkg_resources.DistributionNotFound:
    HAS_PAC = False
else:
    from plone.event.utils import pydt
    from pytz import timezone
    HAS_PAC = True


class SetAndFixKnownDates(object):
    """Set dates."""

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.condition = Condition(
            options.get('condition', 'python:True'),
            transmogrifier, name, options
            )
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')

    def __iter__(self):
        """Iterate over items."""
        default_timezone = self.options.get('default_timezone') or 'UTC'
        if HAS_PAC:
            try:
                tz = api.portal.get_registry_record('plone.portal_timezone')
            except InvalidParameterError:
                tz = None
            if tz is not None:
                tz = timezone(tz)
            else:
                tz = timezone(default_timezone)

        for item in self.previous:
            if self.condition(item):
                pathkey = self.pathkey(*item.keys())[0]
                if not pathkey:  # not enough info
                    yield item
                    continue
                path = item[pathkey]

                obj = traverse(self.context, str(path).lstrip('/'), None)
                if obj is None:
                    yield item
                    continue  # object not found

                if 'creation_date' in item:
                    # try:
                    #     obj.setCreationDate(item['creation_date'])
                    # except AttributeError:
                    #     # dexterity content does not have setCreationDate
                    #     obj.creation_date = item['creation_date']
                    obj.creation_date = item['creation_date']
                if 'modification_date' in item:
                    obj.setModificationDate(item['modification_date'])
                if 'effectiveDate' in item:
                    obj.setEffectiveDate(item['effectiveDate'])
                if 'expirationDate' in item:
                    obj.setExpirationDate(item['expirationDate'])

                # Fix issue where expiration date was before effective date
                effective = obj.effective()
                expires = obj.expires()
                if effective and expires and expires < effective:
                    obj.setExpirationDate(effective)

                if HAS_PAC and item.get('_type') == 'Event':
                    # obj = resolve_object(context, item)
                    obj.start = pydt(DateTime(obj.start)).astimezone(tz)
                    obj.end = pydt(DateTime(obj.end)).astimezone(tz)

            yield item


class LeftOvers(object):
    """Set some left overs."""

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        """Initialize class."""
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

        if 'properties-key' in options:
            propertieskeys = options['properties-key'].splitlines()
        else:
            propertieskeys = \
                defaultKeys(options['blueprint'], name, 'properties')
        self.propertieskey = Matcher(*propertieskeys)

    def __iter__(self):
        """Iter."""
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            if not pathkey:
                # not enough info
                yield item
                continue

            obj = \
                self.context.unrestrictedTraverse(
                    str(item[pathkey]).lstrip('/'), None)

            if obj is None:
                # path doesn't exist
                yield item
                continue

            # # Tags
            # if item.get('subject', False):
            #     obj.subject = item['subject']

            yield item


ANNOTATION_KEY = 'ftw.blueprints-position'

class PositionInParentUpdater(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.positionkey = defaultMatcher(options, 'position-key',
                                          name, 'gopip')

    def __iter__(self):
        for item in self.previous:
            keys = item.keys()
            pathkey = self.pathkey(*keys)[0]
            positionkey = self.positionkey(*keys)[0]
            path = item[pathkey]
            position = item.get(positionkey)

            obj = self.context.unrestrictedTraverse(
                str(path).lstrip('/'), None)
            if obj is not None:
                self.updateObjectPosition(obj, position)

            yield item

    def updateObjectPosition(self, obj, position):
        """Store the position we want on the object and order all children
        of the parent according to their stored positions.
        This allows to partially migrate different types in a folder in different
        steps and will reorder already migrated siblings correctly because we
        have stored the position from the source installation.
        """
        print(position)
        if position is not None:
            self.store_position_for_obj(obj, position)
        parent = aq_parent(aq_inner(obj))
        self.reorder_children(parent)

    def store_position_for_obj(self, obj, position):
        IAnnotations(obj)[ANNOTATION_KEY] = position

    def reorder_children(self, obj):
        ordered_sibling_ids = self.get_ordered_children_ids_from_annotations(obj)
        obj.moveObjectsByDelta(ordered_sibling_ids, - len(ordered_sibling_ids))

    def get_ordered_children_ids_from_annotations(self, container):
        def get_position_from_annotations(item):
            id_, obj = item
            try:
                return IAnnotations(obj)[ANNOTATION_KEY]
            except (TypeError, KeyError):
                return 10000

        ordered_children = sorted(container.objectItems(), key=get_position_from_annotations)
        return map(itemgetter(0), ordered_children)
