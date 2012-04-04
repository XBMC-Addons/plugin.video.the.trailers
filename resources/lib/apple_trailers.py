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

import re
from BeautifulSoup import BeautifulSoup
from urllib import unquote, urlencode
from urllib2 import urlopen, Request, HTTPError, URLError

UA = 'QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)'

MAIN_URL = 'http://trailers.apple.com/trailers/home/xml/current.xml'
MOVIE_URL = 'http://trailers.apple.com/moviesxml/s/%s/index.xml'

FILTER_CRITERIA = ('year', 'studio', 'cast', 'genre')

QUALITIES = ('480p', '720p', )

DEBUG = False


def get_filter_criteria():
    __log('get_filter_criteria')
    return FILTER_CRITERIA


def get_movies(filters={}):
    __log('get_movies started with filters: %s' % filters)
    url = MAIN_URL
    r_movie_string = re.compile('/movies/(.+)/')
    tree = __get_tree(url)
    movies = []
    for m in tree.findAll('movieinfo'):
        movie = {'movie_id': m.get('id'),
                 'source_id': 'apple',
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
            movie['genre'] = [g.string.strip() for g in m.genre.contents]
        if m.cast:
            movie['cast'] = [c.string.strip() for c in m.cast.contents]
        movie['trailer_url'] = ('%s?|User-Agent=%s'
                                  % (m.preview.large.string, UA))
        movie['movie_string'] = re.search(r_movie_string,
                                          m.preview.large.string).group(1)
        movie['size'] = m.preview.large['filesize']
        if filters:
            match = True
            for field, content in filters.items():
                match = match and content in movie.get(field)
            if not match:
                continue
        movies.append(movie)
    if DEBUG:
        for m in movies:
            print m
    __log('get_movies finished with %d elements' % len(movies))
    return movies


def get_trailer(movie_id, quality):
    __log('get_trailer started with movie_id: %s quality: %s'
          % (movie_id, quality))
    f = {'movie_id': movie_id}
    movies = get_movies(filters=f, quality=quality)
    if movies:
        return movies[0]['trailer_url']


def get_trailers(movie_id):
    __log('get_trailers started with movie_id: %s' % movie_id)
    f = {'movie_id': movie_id}
    movies = get_movies(filters=f)
    if not movies:
        raise Exception
    movie_string = movies[0]['movie_string']
    url = MOVIE_URL % movie_string
    html = __get_url(url)
    r_section = re.compile('<array>(.*?)</array>', re.DOTALL)
    section = re.search(r_section, html).group(1)
    tree = BeautifulSoup(section, convertEntities=BeautifulSoup.HTML_ENTITIES)
    trailers = []
    for s in tree.findAll('dict'):
        title = url = None
        for k in s.findAll('key'):
            if k.string == 'songName':
                title = k.nextSibling.string
            elif k.string == 'previewURL':
                url = k.nextSibling.string
            if title and url:
                trailers.append({'title': title,
                                 'url': ('%s?|User-Agent=%s' % (url, UA)), })
                break
    return trailers


def get_filter_content(criteria):
    __log('get_filter_content started with criteria: %s' % criteria)
    assert criteria in FILTER_CRITERIA
    movies = get_movies()
    return __filter(movies, criteria)


def __format_date(date_str):
    y, m, d = date_str.split('-')
    return '.'.join((d, m, y, ))


def __format_year(date_str):
    return date_str.split('-', 1)[0]


def __filter(ld, f):
    ll = [d[f] for d in ld if d.get(f)]
    if isinstance(ll[0], list):
        s = set([i for ll in ll for i in ll])
    else:
        s = set(ll)
    return sorted(s)


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
