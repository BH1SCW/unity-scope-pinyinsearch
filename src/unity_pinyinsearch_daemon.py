#! /usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mark Tully <markjtully@gmail.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GLib, Gio
from gi.repository import Unity
import gettext
import os
import webbrowser
import sqlite3
import hashlib

APP_NAME = 'unity-scope-pinyinsearch'
LOCAL_PATH = '/usr/share/locale/'
gettext.bindtextdomain(APP_NAME, LOCAL_PATH)
gettext.textdomain(APP_NAME)
_ = gettext.gettext

GROUP_NAME = 'com.canonical.Unity.Scope.Webhistory.Pinyinsearch'
UNIQUE_PATH = '/com/canonical/unity/scope/webhistory/pinyinsearch'

SEARCH_HINT = _('Search Bookmarks')
NO_RESULTS_HINT = _('Sorry, there are no Bookmarks that match your search.')
PROVIDER_CREDITS = _('')
SVG_DIR = '/usr/share/icons/unity-icon-theme/places/svg/'
PROVIDER_ICON = SVG_DIR + 'group-browserbookmarks.svg'
DEFAULT_RESULT_ICON = SVG_DIR + 'group-browserbookmarks.svg'
DEFAULT_RESULT_MIMETYPE = 'text/html'
DEFAULT_RESULT_TYPE = Unity.ResultType.DEFAULT
FIREFOX_EXECUTABLE = '/usr/bin/firefox'
BOOKMARKS_PATH = os.getenv("HOME") + "/.mozilla/firefox/"
BOOKMARKS_QUERY = '''SELECT moz_bookmarks.title, moz_places.url, moz_favicons.url, '%s', '%s'
                     FROM moz_bookmarks, moz_places, moz_favicons
                     WHERE moz_places.id = moz_bookmarks.fk
                         AND moz_places.favicon_id = moz_favicons.id
                         AND moz_bookmarks.title is not null
                         AND moz_places.favicon_id is not null
                         AND moz_bookmarks.type = 1
                         AND (moz_bookmarks.title LIKE '%%%s%%' OR moz_places.url LIKE '%%%s%%')
                     ORDER BY moz_bookmarks.lastModified;'''

c1 = {'id': 'bookmarks',
      'name': _('Bookmarks'),
      'icon': SVG_DIR + 'group-installed.svg',
      'renderer': Unity.CategoryRenderer.VERTICAL_TILE}
CATEGORIES = [c1]

FILTERS = []

EXTRA_METADATA = []


def get_bookmarks_from_firefox(path, search):
    '''
     Gets a list of bookmarks from the user's firefox profiles
    '''
    # Build Firefox's profile paths
    firefox_dbfiles = []
    bookmarks = []
    for folder in os.listdir(path):
        if '.' in folder:
            firefox_dbfiles.append(path + folder + "/places.sqlite")

    for dbfile in firefox_dbfiles:
        if os.path.exists(dbfile):
            try:
                filename = dbfile.replace('/places.sqlite', '')
                file_name, profile_name = os.path.splitext(filename)
                profile_name = profile_name[1:]
                sqlite_query = BOOKMARKS_QUERY % (profile_name, dbfile, search, search)

                conn = sqlite3.connect(dbfile)
                connection = conn.cursor()
                connection.execute(sqlite_query)
                profile_bookmarks = connection.fetchall()
                for bookmark in profile_bookmarks:
                    bookmarks.append(bookmark)
                connection.close()
            except sqlite3.DatabaseError:
                pass
    return bookmarks


def search(search, filters):
    '''
    Search for help documents matching the search string
    '''
    results = []
    bookmarks = get_bookmarks_from_firefox(BOOKMARKS_PATH, search)

    for bookmark in bookmarks:
        # Stop Firefox's smart bookmark folders from showing up
        if not bookmark[1].find("place:") == -1:
            continue
        path = bookmark[4].replace('places.sqlite', 'thumbnails/')
        path = path.replace('.mozilla/', '.cache/mozilla/') 
        icon = '%s%s.png' % (path, hashlib.md5(bookmark[1].encode()).hexdigest())
        if not os.path.exists(icon):
            icon = None
        results.append({'uri': bookmark[1],
                        'icon': icon,
                        'category': 0,
                        'title': bookmark[0],
                        'user': GLib.Variant('s', bookmark[3])})
    return results


def activate(result, metadata, id):
    '''
    Open the url in the default webbrowser
    Args:
      uri: The url to be opened
    '''
    parameters = [FIREFOX_EXECUTABLE, result.uri]
    GLib.spawn_async(parameters)
    return Unity.ActivationResponse(handled=Unity.HandledType.HIDE_DASH, goto_uri=None)


class Preview(Unity.ResultPreviewer):
    '''
    Creates the preview for the result
    '''
    def do_run(self):
        '''
        Create a preview and return it
        '''
        preview = Unity.GenericPreview.new(self.result.title, '', None)
        preview.props.subtitle = self.result.uri
        
        if os.path.exists(self.result.icon_hint):
            preview.props.image_source_uri = 'file://' + self.result.icon_hint
        else:
            preview.props.image = Gio.ThemedIcon.new('gtk-about')
        show_action = Unity.PreviewAction.new("show", _("Open"), None)
        preview.add_action(show_action)
        return preview

# Classes below this point establish communication
# with Unity, you probably shouldn't modify them.


class MySearch(Unity.ScopeSearchBase):
    def __init__(self, search_context):
        super(MySearch, self).__init__()
        self.set_search_context(search_context)

    def do_run(self):
        '''
        Adds results to the model
        '''
        try:
            result_set = self.search_context.result_set
            for i in search(self.search_context.search_query,
                            self.search_context.filter_state):
                if not 'uri' in i or not i['uri'] or i['uri'] == '':
                    continue
                if not 'icon' in i or not i['icon'] or i['icon'] == '':
                    i['icon'] = DEFAULT_RESULT_ICON
                if not 'mimetype' in i or not i['mimetype'] or i['mimetype'] == '':
                    i['mimetype'] = DEFAULT_RESULT_MIMETYPE
                if not 'result_type' in i or not i['result_type'] or i['result_type'] == '':
                    i['result_type'] = DEFAULT_RESULT_TYPE
                if not 'category' in i or not i['category'] or i['category'] == '':
                    i['category'] = 0
                if not 'title' in i or not i['title']:
                    i['title'] = ''
                if not 'comment' in i or not i['comment']:
                    i['comment'] = ''
                if not 'dnd_uri' in i or not i['dnd_uri'] or i['dnd_uri'] == '':
                    i['dnd_uri'] = i['uri']
                i['provider_credits'] = GLib.Variant('s', PROVIDER_CREDITS)
                result_set.add_result(**i)
        except Exception as error:
            print(error)


class Scope(Unity.AbstractScope):
    def __init__(self):
        Unity.AbstractScope.__init__(self)

    def do_get_search_hint(self):
        return SEARCH_HINT

    def do_get_schema(self):
        '''
        Adds specific metadata fields
        '''
        schema = Unity.Schema.new()
        if EXTRA_METADATA:
            for m in EXTRA_METADATA:
                schema.add_field(m['id'], m['type'], m['field'])
        #FIXME should be REQUIRED for credits
        schema.add_field('provider_credits', 's', Unity.SchemaFieldType.OPTIONAL)
        return schema

    def do_get_categories(self):
        '''
        Adds categories
        '''
        cs = Unity.CategorySet.new()
        if CATEGORIES:
            for c in CATEGORIES:
                cat = Unity.Category.new(c['id'], c['name'],
                                         Gio.ThemedIcon.new(c['icon']),
                                         c['renderer'])
                cs.add(cat)
        return cs

    def do_get_filters(self):
        '''
        Adds filters
        '''
        fs = Unity.FilterSet.new()
        #if FILTERS:
        #
        return fs

    def do_get_group_name(self):
        return GROUP_NAME

    def do_get_unique_name(self):
        return UNIQUE_PATH

    def do_create_search_for_query(self, search_context):
        se = MySearch(search_context)
        return se

    def do_activate(self, result, metadata, id):
        return activate(result, metadata, id)

    def do_create_previewer(self, result, metadata):
        '''
        Creates a preview when a resut is right-clicked
        '''
        result_preview = Preview()
        result_preview.set_scope_result(result)
        result_preview.set_search_metadata(metadata)
        return result_preview


def load_scope():
    return Scope()
