#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from xbmcswift import Plugin, xbmc, xbmcplugin, xbmcgui, clean_dict
import resources.lib.apple_trailers as apple_trailers

__addon_name__ = 'The Trailers'
__id__ = 'plugin.video.the.trailers'

DEBUG = False

THUMBNAIL_VIEW_IDS = {'skin.confluence': 500,
                      'skin.aeon.nox': 551,
                      'skin.confluence-vertical': 500,
                      'skin.jx720': 52,
                      'skin.pm3-hd': 53,
                      'skin.rapier': 50,
                      'skin.simplicity': 500,
                      'skin.slik': 53,
                      'skin.touched': 500,
                      'skin.transparency': 53,
                      'skin.xeebo': 55}


class Plugin_mod(Plugin):

    def add_items(self, iterable, is_update=False, sort_method_ids=[],
                  override_view_mode=False):
        items = []
        urls = []
        for i, li_info in enumerate(iterable):
            items.append(self._make_listitem(**li_info))
            if self._mode in ['crawl', 'interactive', 'test']:
                print '[%d] %s%s%s (%s)' % (i + 1, '', li_info.get('label'),
                                            '', li_info.get('url'))
                urls.append(li_info.get('url'))
        if self._mode is 'xbmc':
            if override_view_mode:
                skin = xbmc.getSkinDir()
                thumbnail_view = THUMBNAIL_VIEW_IDS.get(skin)
                if thumbnail_view:
                    cmd = 'Container.SetViewMode(%s)' % thumbnail_view
                    xbmc.executebuiltin(cmd)
            xbmcplugin.addDirectoryItems(self.handle, items, len(items))
            for id in sort_method_ids:
                xbmcplugin.addSortMethod(self.handle, id)
            xbmcplugin.endOfDirectory(self.handle, updateListing=is_update)
        return urls

    def _make_listitem(self, label, label2='', iconImage='', thumbnail='',
                       path='', **options):
        li = xbmcgui.ListItem(label, label2=label2, iconImage=iconImage,
                              thumbnailImage=thumbnail, path=path)
        cleaned_info = clean_dict(options.get('info'))
        if cleaned_info:
            li.setInfo('video', cleaned_info)
        if options.get('is_playable'):
            li.setProperty('IsPlayable', 'true')
        if options.get('context_menu'):
            li.addContextMenuItems(options['context_menu'])
        return options['url'], li, options.get('is_folder', True)

plugin = Plugin_mod(__addon_name__, __id__, __file__)


@plugin.route('/', default=True)
def show_sources():
    __log('show_sources start')
    entries = [{'title': 'Apple Movie Trailers',
                'source_id': 'apple'}, ]
    items = [{'label': e['title'],
              'url': plugin.url_for('show_categories',
                                    source_id=e['source_id'])}
             for e in entries]
    __log('show_sources end')
    return plugin.add_items(items)


@plugin.route('/source/<source_id>/')
def show_categories(source_id):
    __log('show_categories started with source_id=%s'
          % source_id)
    source = __get_source(source_id)
    entries = source.get_categories()
    items = [{'label': e['title'],
              'url': plugin.url_for('show_trailers',
                                    source_id=source_id,
                                    category_id=e['category_id'])}
             for e in entries]
    __log('show_categories end')
    return plugin.add_items(items)


@plugin.route('/source/<source_id>/<category_id>')
def show_trailers(source_id, category_id):
    __log('show_trailers started with source_id=%s, category_id=%s'
          % (source_id, category_id))
    source = __get_source(source_id)
    entries = source.get_trailers(category_id)
    __log('show_trailers end')
    return __add_items(entries)


def __add_items(entries):
    items = []
    force_viewmode = plugin.get_setting('force_viewmode') == 'true'
    update_on_pageswitch = plugin.get_setting('update_on_pageswitch') == 'true'
    has_icons = False
    is_update = False
    for e in entries:
        if force_viewmode and not has_icons and e.get('thumb', False):
            has_icons = True
        items.append({'label': e['title'],
                      'iconImage': e.get('thumb', 'DefaultVideo.png'),
                      'info': {'title': e.get('title'),
                               'duration': e.get('duration', '0:00'),
                               'size': int(e.get('size', 0)),
                               'mpaa': e.get('mpaa', ''),
                               'plot': e.get('plot', ''),
                               'cast': e.get('cast', []),
                               'genre': ', '.join(e.get('genre', [])),
                               'studio': e.get('studio', ''),
                               'date': e.get('post_date', ''),
                               'premiered': e.get('release_date', ''),
                               'year': int(e.get('year', 0)),
                               'rating': float(e.get('rating', 0.0)),
                               'director': e.get('director', '')},
                      'is_folder': False,
                      'is_playable': True,
                      'url': e['url']})
    sort_methods = [xbmcplugin.SORT_METHOD_UNSORTED,
                    xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
                    xbmcplugin.SORT_METHOD_DATE,
                    xbmcplugin.SORT_METHOD_VIDEO_RUNTIME, ]
    __log('__add_items end')
    return plugin.add_items(items, is_update=is_update,
                            sort_method_ids=sort_methods,
                            override_view_mode=has_icons)


def __get_source(source_id):
    if source_id == 'apple':
        __log('__get_source using: %s' % 'AMT')
        return apple_trailers
    else:
        raise Exception('UNKNOWN SOURCE: %s' % source_id)


def __log(text):
    xbmc.log('%s addon: %s' % (__addon_name__, text))


if __name__ == '__main__':
    plugin.run()
