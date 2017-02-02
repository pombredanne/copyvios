# -*- coding: utf-8  -*-

import datetime
from os.path import expanduser

from flask import g, request
import oursql
from sqlalchemy.pool import manage

oursql = manage(oursql)

__all__ = ["Query", "cache", "get_db", "get_notice", "httpsfix", "urlstrip"]

class Query(object):
    def __init__(self, method="GET"):
        self.query = {}
        data = request.form if method == "POST" else request.args
        for key in data:
            self.query[key] = data.getlist(key)[-1]

    def __getattr__(self, key):
        return self.query.get(key)

    def __setattr__(self, key, value):
        if key == "query":
            super(Query, self).__setattr__(key, value)
        else:
            self.query[key] = value


class _AppCache(object):
    def __init__(self):
        super(_AppCache, self).__setattr__("_data", {})

    def __getattr__(self, key):
        return self._data[key]

    def __setattr__(self, key, value):
        self._data[key] = value


cache = _AppCache()

def get_db():
    if not g._db:
        args = cache.bot.config.wiki["_copyviosSQL"]
        args["read_default_file"] = expanduser("~/.my.cnf")
        args["autoping"] = True
        args["autoreconnect"] = True
        g._db = oursql.connect(**args)
    return g._db

def get_notice():
    try:
        with open(expanduser("~/copyvios_notice.html")) as fp:
            lines = fp.read().decode("utf8").strip().splitlines()
            if lines[0] == "<!-- active -->":
                return "\n".join(lines[1:])
            return None
    except IOError:
        return None

def httpsfix(context, url):
    if url.startswith("http://"):
        url = url[len("http:"):]
    return url

def parse_wiki_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y%m%d%H%M%S')

def urlstrip(context, url):
    if url.startswith("http://"):
        url = url[7:]
    if url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    if url.endswith("/"):
        url = url[:-1]
    return url
