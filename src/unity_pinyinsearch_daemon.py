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

GROUP_NAME = 'com.canonical.Unity.Scope.Pinyinsearch'
UNIQUE_PATH = '/com/canonical/unity/scope/pinyinsearch'

SEARCH_HINT = _('Pinyin Search For Dash')
NO_RESULTS_HINT = _('Sorry, there are no Result that match your search.')
PROVIDER_CREDITS = _('')
SVG_DIR = '/usr/share/icons/unity-icon-theme/places/svg/'
PROVIDER_ICON = SVG_DIR + 'group-files.svg'
DEFAULT_RESULT_ICON = SVG_DIR + 'service-askubuntu.svg'
DEFAULT_RESULT_MIMETYPE = 'text/html'
DEFAULT_RESULT_TYPE = Unity.ResultType.DEFAULT
FIREFOX_EXECUTABLE = 'gvfs-open '
#FIREFOX_EXECUTABLE = 'mimeopen -n '
BOOKMARKS_PATH = os.getenv("HOME") + "/.pinyinsearch/"
BOOKMARKS_QUERY = '''select * from dashpinyin where pinyin LIKE '%%%s%%' '''
#/home/kroody/test/pipe/chongceshi.txt
c1 = {'id': 'records',
      'name': _('Results'),
      'icon': SVG_DIR + 'group-installed.svg',
      'renderer': Unity.CategoryRenderer.VERTICAL_TILE}
CATEGORIES = [c1]

FILTERS = []

EXTRA_METADATA = []


def get_records_from_db(path, search):
    # Build Firefox's profile paths
    pinyinsearch_db = path + ".pinyinsearch.sqlite"
    results = []
    search_test = 'chongceshi'
    print('=================================================================================')
    if os.path.exists(pinyinsearch_db):
        try:
            sqlite_query = BOOKMARKS_QUERY % (search)
            print(sqlite_query)
            conn = sqlite3.connect(pinyinsearch_db)
            connection = conn.cursor()
            connection.execute(sqlite_query)
            records = connection.fetchall()
            for record in records:
                print(record[1])
                results.append(record[1])
            connection.close()
        except sqlite3.DatabaseError:
            print('something err')
            pass
    else:
        print('database file not exists')

    print('===================OVER =========================================================')
    return results


def search(search, filters):
    results = []
    records = get_records_from_db(BOOKMARKS_PATH, search)
    if records == None:
        return None
    for record in records:
        print (record)
        icon = '/usr/share/icons/gnome/scalable/places/ubuntu-logo.png'
        if not os.path.exists(icon):
            icon = None
        results.append({'uri': "file://" + record,
            'icon': icon,
            'category': 0,
            'title': record,
            'user': GLib.Variant('s', record)})
        
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
