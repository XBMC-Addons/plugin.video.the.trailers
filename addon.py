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
           'year': 30001,
           'studio': 30002,
           'cast': 30003,
           'genre': 30004,
           'open_settings': 30005}


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
                             trailer_type='default')
        return plugin.redirect(url)
    else:
        source = __get_source(source_id)
        is_folder = plugin.get_setting('ask_quality') == 'true'
        items = [{'label': i['title'],
                  'is_folder': is_folder,
                  'is_playable': not is_folder,
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
    if not plugin.get_setting('ask_quality') == 'true':
        __log('show_trailer_qualities redirecting to play_trailer')
        q_id = int(plugin.get_setting('trailer_quality'))
        trailer_quality = source.get_trailer_qualities()[q_id]['title']
        url = plugin.url_for('play_trailer',
                             source_id=source_id,
                             movie_title=movie_title,
                             trailer_type=trailer_type,
                             trailer_quality=trailer_quality)
        return plugin.redirect(url)
    else:
        source = __get_source(source_id)
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


@plugin.route('/<source_id>/trailer/<movie_title>/<trailer_type>/<trailer_quality>')
def play_trailer(source_id, movie_title, trailer_type, trailer_quality):
    __log(('play_trailer started with source_id=%s movie_title=%s '
           'trailer_type=%s trailer_quality=%s')
           % (source_id, movie_title, trailer_type, trailer_quality))
    source = __get_source(source_id)
    trailer_url = source.get_trailer(movie_title, trailer_quality,
                                     trailer_type)
    return plugin.set_resolved_url(trailer_url)


@plugin.route('/settings/')
def open_settings():
    __log('open_settings started')
    plugin.open_settings()


def __add_movies(source_id, entries):
    __log('__add_movies start')
    items = []
    context_menu = [(_('show_movie_info'), 'XBMC.Action(Info)'),
                    (_('open_settings'), 'XBMC.Container.Update(%s)'
                                         % plugin.url_for('open_settings'))]
    for fc in __get_source(source_id).get_filter_criteria():
        context_menu.append((_(fc['title']),
                             'XBMC.Container.Update(%s)'
                             % plugin.url_for('show_filter_content',
                                              source_id=source_id,
                                              filter_criteria=fc['id'])))
    is_playable = (plugin.get_setting('ask_quality') == 'false' and
                   plugin.get_setting('ask_trailer') == 'false')
    for e in entries:
        movie = __format_movie(e)
        movie['context_menu'] = context_menu
        movie['is_folder'] = not is_playable
        movie['is_playable'] = is_playable
        movie['url'] = plugin.url_for('show_trailer_types',
                                      source_id=source_id,
                                      movie_title=movie['label'])
        items.append(movie)
    sort_methods = [xbmcplugin.SORT_METHOD_UNSORTED,
                    xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
                    xbmcplugin.SORT_METHOD_DATE,
                    xbmcplugin.SORT_METHOD_VIDEO_RUNTIME, ]
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
    if source_id == 'apple':
        __log('__get_source using: %s' % source_id)
        source = apple_trailers.AppleTrailers()
        return source
    else:
        raise Exception('UNKNOWN SOURCE: %s' % source_id)


def _(s):
    s_id = STRINGS.get(s)
    if s_id:
        return plugin.get_string(s_id)
    else:
        return s


def __log(text):
    xbmc.log('%s addon: %s' % (__addon_name__, text))


if __name__ == '__main__':
    plugin.run()
