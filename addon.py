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

import os
from xbmcswift import Plugin, xbmc, xbmcplugin, xbmcgui, clean_dict
from resources.lib.exceptions import NetworkError
import resources.lib.apple_trailers as apple_trailers
import SimpleDownloader

__addon_name__ = 'The Trailers'
__id__ = 'plugin.video.the.trailers'

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
            'id': 'apple'}, ]

STRINGS = {'show_movie_info': 30000,
           'open_settings': 30001,
           'browse_by': 30002,
           'genre': 30003,
           'download_trailer': 30004,
           'download_play': 30005,
           'show_downloads': 30006,
           'add_to_cp': 30007,
           'neterror_title': 30100,
           'neterror_line1': 30101,
           'neterror_line2': 30102}


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
            li.addContextMenuItems(options['context_menu'], replaceItems=True)
        return options['url'], li, options.get('is_folder', True)

plugin = Plugin_mod(__addon_name__, __id__, __file__)


@plugin.route('/', default=True)
def show_sources():
    __log('show_sources')
    if len(SOURCES) == 1:
        __log('show_sources redirecting to show_all_movies')
        url = plugin.url_for('show_all_movies',
                             source_id=SOURCES[0]['id'])
        return plugin.redirect(url)
    else:
        items = [{'label': i['title'],
                  'url': plugin.url_for('show_all_movies',
                                        source_id=i['id'])}
                 for i in SOURCES]
        return plugin.add_items(items)


@plugin.route('/<source_id>/movies/')
def show_all_movies(source_id):
    __log('show_all_movies started with source_id=%s' % source_id)
    source = __get_source(source_id)
    items = source.get_movies()
    return __add_movies(source_id, items)


@plugin.route('/<source_id>/movies/<filter_criteria>/')
def show_filter_content(source_id, filter_criteria):
    __log('show_filter_content started with source_id=%s filter_criteria=%s'
          % (source_id, filter_criteria))
    source = __get_source(source_id)
    items = [{'label': i['title'],
              'url': plugin.url_for('show_filtered_movies',
                                    source_id=source_id,
                                    filter_criteria=filter_criteria,
                                    filter_content=i['id'])}
             for i in source.get_filter_content(filter_criteria)]
    return plugin.add_items(items)


@plugin.route('/<source_id>/movies/<filter_criteria>/<filter_content>/')
def show_filtered_movies(source_id, filter_criteria, filter_content):
    __log(('show_filtered_movies started with source_id=%s '
           'filter_criteria=%s filter_content=%s')
          % (source_id, filter_criteria, filter_content))
    source = __get_source(source_id)
    if filter_criteria != 'all' and filter_content != 'all':
        items = source.get_movies(filters={filter_criteria: filter_content})
    else:
        items = source.get_movies()
    return __add_movies(source_id, items)


@plugin.route('/<source_id>/trailer/<movie_title>/')
def show_trailer_types(source_id, movie_title):
    __log('show_trailer_types started with source_id=%s movie_title=%s'
          % (source_id, movie_title))
    if not plugin.get_setting('ask_trailer') == 'true':
        __log('show_trailer_types redirecting to show_trailer_qualities')
        url = plugin.url_for('show_trailer_qualities',
                             source_id=source_id,
                             movie_title=movie_title,
                             trailer_type='trailer')
        return plugin.redirect(url)
    else:
        source = __get_source(source_id)
        is_folder = plugin.get_setting('ask_quality') == 'true'
        items = [{'label': i['title'],
                  'is_folder': is_folder,
                  'is_playable': not is_folder,
                  'context_menu': __movie_cm_entries(source_id, movie_title,
                                                      trailer_type=i['id']),
                  'url': plugin.url_for('show_trailer_qualities',
                                        source_id=source_id,
                                        movie_title=movie_title,
                                        trailer_type=i['id'])}
                 for i in source.get_trailer_types(movie_title)]
        return plugin.add_items(items)


@plugin.route('/<source_id>/trailer/<movie_title>/<trailer_type>/')
def show_trailer_qualities(source_id, movie_title, trailer_type):
    __log(('show_trailer_qualities started with '
           'source_id=%s movie_title=%s trailer_type=%s')
          % (source_id, movie_title, trailer_type))
    source = __get_source(source_id)
    if not plugin.get_setting('ask_quality') == 'true':
        __log('show_trailer_qualities redirecting to play_trailer')
        q_id = int(plugin.get_setting('trailer_quality'))
        trailer_quality = source.get_trailer_qualities(movie_title)[q_id]['title']
        url = plugin.url_for('play_trailer',
                             source_id=source_id,
                             movie_title=movie_title,
                             trailer_type=trailer_type,
                             trailer_quality=trailer_quality)
        return plugin.redirect(url)
    else:
        items = [{'label': i['title'],
                  'is_playable': True,
                  'is_folder': False,
                  'url': plugin.url_for('play_trailer',
                                        source_id=source_id,
                                        movie_title=movie_title,
                                        trailer_type=trailer_type,
                                        trailer_quality=i['title'])}
                 for i in source.get_trailer_qualities(movie_title)]
        return plugin.add_items(items)


@plugin.route('/<source_id>/trailer/<movie_title>/<trailer_type>/<trailer_quality>/play')
def play_trailer(source_id, movie_title, trailer_type, trailer_quality):
    __log(('play_trailer started with source_id=%s movie_title=%s '
           'trailer_type=%s trailer_quality=%s')
           % (source_id, movie_title, trailer_type, trailer_quality))
    trailer_id = '|'.join((source_id, movie_title,
                           trailer_type, trailer_quality))
    downloaded_trailer = plugin.get_setting(trailer_id)
    if downloaded_trailer and os.path.isfile(downloaded_trailer):
        __log('trailer already downloaded, using downloaded version')
        return plugin.set_resolved_url(downloaded_trailer)
    source = __get_source(source_id)
    trailer_url = source.get_trailer(movie_title, trailer_quality,
                                     trailer_type)
    return plugin.set_resolved_url(trailer_url)


@plugin.route('/<source_id>/trailer/<movie_title>/<trailer_type>/download')
def download_trailer(source_id, movie_title, trailer_type):
    __log(('download_trailer started with source_id=%s movie_title=%s '
           'trailer_type=%s') % (source_id, movie_title, trailer_type))
    source = __get_source(source_id)
    q_id = int(plugin.get_setting('trailer_quality_download'))
    trailer_quality = source.get_trailer_qualities(movie_title)[q_id]['title']
    trailer_url = source.get_trailer(movie_title, trailer_quality,
                                     trailer_type)
    sd = SimpleDownloader.SimpleDownloader()
    if not plugin.get_setting('trailer_download_path'):
        plugin.open_settings()
    download_path = plugin.get_setting('trailer_download_path')
    if download_path:
        if '?|User-Agent=' in trailer_url:
            trailer_url, useragent = trailer_url.split('?|User-Agent=')
            # Override User-Agent because SimpleDownloader doesn't support that
            # native. Downloading from apple requires QT User-Agent
            sd.common.USERAGENT = useragent
        safe_chars = ('-_. abcdefghijklmnopqrstuvwxyz'
                      'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        safe_title = ''.join([c for c in movie_title if c in safe_chars])
        filename = '%s-%s-%s.%s' % (safe_title, trailer_type, trailer_quality,
                                    trailer_url.rsplit('.')[-1])
        params = {'url': trailer_url,
                  'download_path': download_path}
        sd.download(filename, params)
        full_path = os.path.join(download_path, filename)
        trailer_id = '|'.join((source_id, movie_title,
                               trailer_type, trailer_quality))
        plugin.set_setting(trailer_id, full_path)
        __log('start downloading: %s to path: %s' % (filename, download_path))


@plugin.route('/<source_id>/trailer/<movie_title>/<trailer_type>/download_play')
def download_play_trailer(source_id, movie_title, trailer_type):
    __log(('download_play_trailer started with source_id=%s movie_title=%s '
           'trailer_type=%s') % (source_id, movie_title, trailer_type))
    return


@plugin.route('/add_to_couchpotato/<movie_title>')
def add_to_couchpotato(movie_title):
    __log('add_to_couchpotato started with movie_title=%s' % movie_title)
    return


@plugin.route('/settings/')
def open_settings():
    __log('open_settings started')
    plugin.open_settings()


def __add_movies(source_id, entries):
    __log('__add_movies start')
    items = []
    context_menu = __global_cm_entries(source_id)
    is_playable = (plugin.get_setting('ask_quality') == 'false' and
                   plugin.get_setting('ask_trailer') == 'false')
    for e in entries:
        movie = __format_movie(e)
        movie['context_menu'] = context_menu[:]
        movie['context_menu'].extend(__movie_cm_entries(source_id,
                                                        e['title'],
                                                        'trailer'))
        movie['is_folder'] = not is_playable
        movie['is_playable'] = is_playable
        movie['url'] = plugin.url_for('show_trailer_types',
                                      source_id=source_id,
                                      movie_title=movie['label'])
        items.append(movie)
    sort_methods = [xbmcplugin.SORT_METHOD_DATE,
                    xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
    force_viewmode = plugin.get_setting('force_viewmode') == 'true'
    __log('__add_movies end')
    return plugin.add_items(items, sort_method_ids=sort_methods,
                            override_view_mode=force_viewmode)


def __format_movie(m):
    return {'label': m['title'],
            'iconImage': m.get('thumb', 'DefaultVideo.png'),
            'info': {'title': m.get('title'),
                     'duration': m.get('duration', '0:00'),
                     'size': int(m.get('size', 0)),
                     'mpaa': m.get('mpaa', ''),
                     'plot': m.get('plot', ''),
                     'cast': m.get('cast', []),
                     'genre': ', '.join(m.get('genre', [])),
                     'studio': m.get('studio', ''),
                     'date': m.get('post_date', ''),
                     'premiered': m.get('release_date', ''),
                     'year': int(m.get('year', 0)),
                     'rating': float(m.get('rating', 0.0)),
                     'director': m.get('director', ''),
                    },
           }


def __get_source(source_id):
    cache_path = xbmc.translatePath(plugin._plugin.getAddonInfo('profile'))
    if source_id == 'apple':
        __log('__get_source using: %s' % source_id)
        source = apple_trailers.AppleTrailers(cache_path)
        return source
    else:
        raise Exception('UNKNOWN SOURCE: %s' % source_id)


def __movie_cm_entries(source_id, movie_title, trailer_type):
    download_url = plugin.url_for('download_trailer',
                                  source_id=source_id,
                                  movie_title=movie_title,
                                  trailer_type=trailer_type)
    download_play_url = plugin.url_for('download_play_trailer',
                                       source_id=source_id,
                                       movie_title=movie_title,
                                       trailer_type=trailer_type)
    couchpotato_url = plugin.url_for('add_to_couchpotato',
                                       movie_title=movie_title)
    cm_entries =  [
        (_('download_trailer'), 'XBMC.RunPlugin(%s)' % download_url),
        (_('download_play'), 'XBMC.RunPlugin(%s)' % download_play_url),
        (_('add_to_cp'), 'XBMC.RunPlugin(%s)' % couchpotato_url),
    ]
    return cm_entries


def __global_cm_entries(source_id):
    show_settings_url =  plugin.url_for('open_settings')
    show_downloads_url = ''  # fixme
    cm_entries = [
        (_('show_movie_info'), 'XBMC.Action(Info)'),
        (_('open_settings'), 'XBMC.Container.Update(%s)' % show_settings_url),
        (_('show_downloads'), 'XBMC.Container.Update(%s)' % show_downloads_url),
    ]
    for fc in __get_source(source_id).get_filter_criteria():
        url = plugin.url_for('show_filter_content',
                             source_id=source_id,
                             filter_criteria=fc['id'])
        cm_entries.append(
            (_('browse_by') % fc['title'], 'XBMC.Container.Update(%s)' % url)
        )
    return cm_entries


def _(s):
    s_id = STRINGS.get(s)
    if s_id:
        return plugin.get_string(s_id)
    else:
        return s


def __log(text):
    xbmc.log('%s addon: %s' % (__addon_name__, text))


if __name__ == '__main__':
    try:
        plugin.set_content('movies')
        plugin.run()
    except NetworkError as e:
        __log('NetworkError: %s' % e)
        xbmcgui.Dialog().ok(_('neterror_title'),
                            _('neterror_line1'),
                            _('neterror_line2'))
