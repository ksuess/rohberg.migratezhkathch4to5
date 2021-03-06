# -*- coding: utf-8 -*-
"""Define custom blueprints for zhkathch."""

from Acquisition import aq_inner
from Acquisition import aq_parent
from bs4 import BeautifulSoup
from DateTime import DateTime
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.utils import Condition
from collective.transmogrifier.utils import defaultMatcher
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import defaultKeys
from collective.transmogrifier.utils import traverse
from io import BytesIO
from io import StringIO
from os.path  import basename
from operator import itemgetter
from PIL import Image
from plone import api
from plone.api.exc import InvalidParameterError
from plone.namedfile.file import NamedBlobImage
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from zope.interface import classProvides

import pkg_resources
import requests
import logging
logger = logging.getLogger("zhkathch transmogrifier")

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
                print("SetAndFixKnownDates")
                if 'creation_date' in item:
                    # try:
                    #     obj.setCreationDate(item['creation_date'])
                    # except AttributeError:
                    #     # dexterity content does not have setCreationDate
                    #     obj.creation_date = item['creation_date']
                    obj.creation_date = item['creation_date']
                if 'modification_date' in item:
                    obj.setModificationDate(item['modification_date'])
                effectiveDate = item.get('effectiveDate', None)
                if effectiveDate and effectiveDate != u"None":
                    obj.setEffectiveDate(effectiveDate)
                else:
                    obj.setEffectiveDate(item.get('modification_date', None))
                # if item['_path']==u'/organisation/gv/arbeitshilfen/exuperantius/exuperantius-05-oeffentlichkeitsarbeit':
                #     import pdb; pdb.set_trace()
                print(item.get('effectiveDate', None) or item.get('modification_date', None))
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
    """Set some left overs for news."""

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
            # # siehe ftw.blueprints.typefieldmapper
            # if item.get('subject', False):
            #     obj.subjects = item['subject']

            # pagetype
            if '/news' in item[pathkey]:
                obj.pagetype = "Beitrag"

            # description
            if item.get('description', False):
                obj.description = item['description']
                obj.beschreibung_themenseite = item['description']

            # Teaserimage immer anzeigen
            obj.teaserimage_anzeigen = True

            yield item


class LeftOversProtokolle(object):
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

            logger.info("item[pathkey] {}".format(item[pathkey]))
            # # Tags
            # # siehe ftw.blueprints.typefieldmapper
            # if item.get('subject', False):
            #     obj.subjects = item['subject']

            # # pagetype
            # if '/news' in item[pathkey]:
            #     obj.pagetype = "Beitrag"

            # description
            if item.get('description', False):
                obj.description = item['description']
                obj.beschreibung_themenseite = item['description']

            # Teaserimage immer anzeigen
            obj.teaserimage_anzeigen = True

            yield item

class LeftOversWordpress(LeftOvers):
    """Set some left overs."""

    classProvides(ISectionBlueprint)
    implements(ISection)

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

            # Tags
            # logger.info(u"leftoverswordpress: subject {}".format(item.get('subject', False)))
            if item.get('subject', False):
                obj.setSubject(item['subject'])

            if 'modification_date' in item:
                obj.setModificationDate(item['modification_date'])
            if 'effectiveDate' in item:
                obj.setEffectiveDate(item['effectiveDate'])
            # if 'expirationDate' in item:
            #     obj.setExpirationDate(item['expirationDate'])

            if item.get('_type', item.get('portal_type', None)) == "zhkathpage":
                # pagetype
                obj.pagetype = "Meinung"

                # Teaserimage mitnehmen und anzeigen
                imgdata = getImageData(item['_orig_url'],
                    selector="img.wp-post-image")
                if imgdata:
                    # crop image
                    img = Image.open(BytesIO(imgdata))
                    x,y = img.size
                    width = 4*y/3 # Seitenformat 4:3
                    offset = (x-width)/2
                    coords = (offset,0,x-offset,y)
                    cropped_img = img.crop(coords)
                    try:
                        out = BytesIO()
                        cropped_img.save(out, format='JPEG')
                        out.seek(0)
                        namedblobimage = NamedBlobImage(data=out.getvalue(),
                            filename=u"teaserimage-blog.jpg")  #, title="Teaserimage Blog")
                        out.close()

                        print("*** teaserimage: item['_orig_url'] {}".format(item['_orig_url']))
                        obj.image = namedblobimage
                    except Exception as e:
                        pass

                    # img = NamedBlobImage(imgdata)  #, filename="")
                    # print(item['_orig_url'])
                    # print(img.getImageSize())
                    # obj.image = img
                else:
                    print("*** teaserimage not found: item['_orig_url'] {}".format(item['_orig_url']))


                obj.teaserimage_anzeigen = True


def getImageData(url=None, selector=".myimage"):
    """Get image content for given url and selector."""

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:63.0) Gecko/20100101 Firefox/63.0'
    headers = {'User-Agent': user_agent}
    resp = requests.get(url, headers=headers)
    print("getImageData status {}".format(resp.status_code))
    try:
        soup = BeautifulSoup(resp.content)
        for img in soup.select(selector):
            src = img["src"]
            response = requests.get(src, headers=headers)
            return response.content

            # img = Image.open(BytesIO(response.content))
            # img.save(basename(src))
            return img
    except Exception as e:
        print("ERROR getImageData {} {}".format(e, url))
        # import pdb; pdb.set_trace()

def getMetainfoAuthor(author_login):
    """Return dictionary with companyposition, bio."""

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:63.0) Gecko/20100101 Firefox/63.0'
    headers = {'User-Agent': user_agent}
    url = "https://blog.zhkath.ch/author/{}/".format(author_login)
    resp = requests.get(url, headers=headers)
    print("getMetainfoAuthor status {}".format(resp.status_code))
    try:
        soup = BeautifulSoup(resp.content)
        selector = "span.author-organisation"
        pick = soup.select(selector)
        companyposition = len(pick) > 0 and pick[0].contents[0].strip(", ") or u""

        selector = "#author-info p"
        pick = soup.select(selector)
        bio = len(pick)>1 and pick[1].contents[0] or u""

        print(companyposition)
        print(bio)
        return {'companyposition': companyposition,
            'bio': bio}
    except Exception as e:
        print("ERROR getMetainfoAuthor {} {}".format(e, author_login))
        # import pdb; pdb.set_trace()
        return None

class BlogauthorConstructor(object):
    """."""

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
            # import pdb; pdb.set_trace()
            if item.get('author_login', False):
                blogauthor = {}
                blogauthor['_type'] = 'blogauthor'
                blogauthor['portal_type'] = 'blogauthor'
                blogauthor['_path'] = item['author_login']
                blogauthor['title'] = item.get('author_display_name', u"Katholische Kirche im Kanton Zürich")
                # logger.info(u"BlogauthorConstructor yield blogauthor {}".format(blogauthor))
                # TODO blogauthor: get image
                imagedata = getImageData("https://blog.zhkath.ch/author/{}/".format(item['author_login']), selector="#author-info img")
                # TODO filename
                dct = {
                    'data': imagedata,
                    'filename': u'{}.jpg'.format(item['author_login'])}
                blogauthor['image'] = dct
                metainfo = getMetainfoAuthor(item['author_login'])
                if metainfo:
                    blogauthor['companyposition'] = u'' + metainfo.get('companyposition', u'')
                    blogauthor['description'] = u"" + metainfo.get('bio', u'')
                logger.info("*** blogauthor {}".format(blogauthor['_path']))
                yield blogauthor

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


class Typefieldmapperzhkathch(object):
    """Map types and their fields to new types and new fields.
    """

    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.typekey = defaultMatcher(options, 'type-key', name, 'type')

    def __iter__(self):
        # Folder mit nur Files: Folder to Folder, File to File
        # sonst: Folder to zhkathpage, File to zhkathpage
        filefolder = [
            u'/organisation/rechtsgrundlagen',
            u'/organisation/synodalrat/geschaefte',
            u'/organisation/synode',
            u'/organisation/rekurskommission',
            u'/service/publikationen/personalwesen/handbuch',
            u'/service/publikationen/jahresberichte/archiv',
            ]
        # mixedfolder = ['/ethikbeitraege/',]
        for item in self.previous:
            keys = item.keys()
            typekey = self.typekey(*keys)[0]

            if not typekey:
                yield item
                continue

            old_type = item[typekey]

            print("*** Typefieldmapperzhkathch old_type: {} _path: {}".format(old_type, item["_path"]))
            is_filefolder = False
            for filefolderpath in filefolder:
                # print(item['_path'].startswith(filefolderpath))
                if item['_path'].startswith(filefolderpath):
                    is_filefolder = True
                    break
            print("is_filefolder {}".format(is_filefolder))
            if not is_filefolder:
                if old_type == 'Folder':
                    item[typekey] = 'zhkathpage'
                    item['text'] = u''
                    # TODO: no yield wenn der Folder eine default page hat
                    if item.get('_defaultpage', False):
                        # continue
                        pass
                elif old_type == 'File':
                    item[typekey] = 'zhkathpage'
                    item['pagetype'] = 'Publikation'
                    item['text'] = u''
                elif old_type == 'Link':
                    item[typekey] = 'zhkathpage'
                    item['link_url'] = item['remoteUrl']
                    item['link_label'] = item['title']
                    item['text'] = u''
                # TODO: Wenn default page, dann _path auf den des Parents ändern
                elif old_type == 'zhkathpage' and item.get('_is_defaultpage', False):
                    _path = item['_path']
                    new_path = '/'.join(_path.split('/')[:-1])
                    new_id = _path.split('/')[-2]
                    print("new_path {} new_id {}".format(new_path, new_id))
                    item['_path'] = new_path
                    item['_id'] = new_id


            yield item
