#!/usr/bin/python
# -*- coding: utf-8 -*-
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

from BeautifulSoup import BeautifulSoup
from urllib import unquote, urlencode
from urllib2 import urlopen, Request, HTTPError, URLError

UA = 'QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)'

MAIN_URL = 'http://trailers.apple.com/trailers/home/xml/'

CATEGORIES = [{'title': 'Current',
               'category_id': 'current'},
              {'title': 'Newest 720P',
               'category_id': 'newest_720p'}, ]

DEBUG = False


def get_categories():
    __log('get_categories')
    return CATEGORIES


def get_trailers(category_id):
    __log('get_trailers started with category_id: %s' % category_id)
    url = '%s%s.xml' % (MAIN_URL, category_id)
    tree = __get_tree(url)
    trailers = []
    for m in tree.findAll('movieinfo'):
        trailer = {'movie_id': m.get('id'),
                   'title': m.title.string,
                   'duration': m.runtime.string,
                   'mpaa': m.rating.string,
                   'studio': m.studio.string,
                   'post_date': __format_date(m.postdate.string),
                   'release_date': __format_date(m.releasedate.string),
                   'year': __format_year(m.releasedate.string),
                   'copyright': m.copyright.string,
                   'director': m.director.string,
                   'plot': m.description.string,
                   'thumb': m.poster.xlarge.string, }
        if m.genre:
            genres = [g.string for g in m.genre.findAll('name')]
            trailer['genre'] = __format_group(genres)
        if m.cast:
            trailer['cast'] = [c.string for c in m.cast.findAll('name')]
        trailer['url'] = '%s?|User-Agent=%s' % (m.preview.large.string, UA)
        trailer['size'] = m.preview.large['filesize']
        trailers.append(trailer)
    if DEBUG:
        for t in trailers:
            print t
    __log('get_trailers finished with %d elements' % len(trailers))
    return trailers


def __format_date(date_str):
    y, m, d = date_str.split('-')
    return '.'.join((d, m, y, ))


def __format_year(date_str):
    return date_str.split('-', 1)[0]


def __format_group(group):
    return ', '.join(group)


def __get_tree(url, referer=None):
    html = __get_url(url, referer)
    tree = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
    return tree


def __get_url(url, referer=None):
    __log('__get_url opening url: %s' % url)
    req = Request(url)
    if referer:
        req.add_header('Referer', referer)
    req.add_header('Accept', ('text/html,application/xhtml+xml,'
                              'application/xml;q=0.9,*/*;q=0.8'))
    req.add_header('User-Agent', UA)
    html = urlopen(req).read()
    __log('__get_url got %d bytes' % len(html))
    return html


def __log(msg):
    print('Apple scraper: %s' % msg)
