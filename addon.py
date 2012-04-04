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

SOURCES = [{'title': 'Apple Movie Trailers',
            'source_id': 'apple'}, ]

STRINGS = {'all': 30000,
           'year': 30001,
           'studio': 30002,
           'cast': 30003,
           'genre': 30004}


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
    items = [{'label': s['title'],
              'url': plugin.url_for('show_filters',
                                    source_id=s['source_id'])}
             for s in SOURCES]
    __log('show_sources end')
    return plugin.add_items(items)


@plugin.route('/<source_id>/')
def show_filters(source_id):
    __log('show_filters started with source_id=%s'
          % source_id)
    source = __get_source(source_id)
    entries = source.get_filter_criteria()
    items = [{'label': _(e),
              'url': plugin.url_for('show_filter_content',
                                    source_id=source_id,
                                    filter_criteria=e)}
             for e in entries]
    items.insert(0, {'label': _('all'),
                     'url': plugin.url_for('show_movies',
                                            source_id=source_id)})
    __log('show_filters end')
    return plugin.add_items(items)


@plugin.route('/<source_id>/all/')
def show_movies(source_id):
    __log('show_movies started with source_id=%s ' % source_id)
    source = __get_source(source_id)
    entries = source.get_movies()
    __log('show_movies end')
    return __add_items(entries)


@plugin.route('/<source_id>/play/<movie_id>')
def play_trailer(source_id, movie_id):
    __log('play_trailer started with source_id=%s movie_id=%s'
          % (source_id, movie_id))
    source = __get_source(source_id)
    quality = '720p'
#    source.get_trailers(movie_id)  # fixme
    video_url = source.get_trailer(movie_id, quality)
    __log('play_trailer ended with video_url=%s' % video_url)
    return plugin.set_resolved_url(video_url)


@plugin.route('/<source_id>/<filter_criteria>/')
def show_filter_content(source_id, filter_criteria):
    __log('show_filter_content started with source_id=%s filter_criteria=%s'
          % (source_id, filter_criteria))
    source = __get_source(source_id)
    entries = source.get_filter_content(filter_criteria)
    items = [{'label': e,
              'url': plugin.url_for('show_movies_filtered',
                                    source_id=source_id,
                                    filter_criteria=filter_criteria,
                                    filter_content=e)}
             for e in entries]
    __log('show_filter_content end')
    return plugin.add_items(items)


@plugin.route('/<source_id>/<filter_criteria>/<filter_content>/')
def show_movies_filtered(source_id, filter_criteria, filter_content):
    __log(('show_movies_filtered started with source_id=%s '
           'filter_criteria=%s filter_content=%s')
          % (source_id, filter_criteria, filter_content))
    source = __get_source(source_id)
    entries = source.get_movies({filter_criteria: filter_content})
    __log('show_movies_filtered end')
    return __add_items(entries)


def __add_items(entries):
    items = []
    force_viewmode = plugin.get_setting('force_viewmode') == 'true'
    has_icons = False
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
                      'url': plugin.url_for('play_trailer',
                                            source_id=e['source_id'],
                                            movie_id=e['movie_id'])})
    sort_methods = [xbmcplugin.SORT_METHOD_UNSORTED,
                    xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
                    xbmcplugin.SORT_METHOD_DATE,
                    xbmcplugin.SORT_METHOD_VIDEO_RUNTIME, ]
    __log('__add_items end')
    return plugin.add_items(items, sort_method_ids=sort_methods,
                            override_view_mode=has_icons)


def __get_source(source_id):
    if source_id == 'apple':
        __log('__get_source using: %s' % source_id)
        return apple_trailers
    else:
        raise Exception('UNKNOWN SOURCE: %s' % source_id)


def _(s):
    s_id = STRINGS.get(s)
    if s_id:
        return plugin.get_string(s_id)
    else:
        __log('missing translation for s:"%s"' % s)
        return s


def __log(text):
    xbmc.log('%s addon: %s' % (__addon_name__, text))


if __name__ == '__main__':
    plugin.run()
