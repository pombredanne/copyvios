# -*- coding: utf-8  -*-

from collections import OrderedDict

from .highlighter import highlight_delta
from .checker import do_check, T_POSSIBLE, T_SUSPECT
from .misc import Query, cache
from .sites import update_sites

__all__ = ["format_api_error", "handle_api_request"]

_CHECK_ERRORS = {
    "no search method": "Either 'use_engine' or 'use_links' must be true",
    "no URL": "The parameter 'url' is required for URL comparisons",
    "bad URI": "The given URI scheme is unsupported",
    "no data": "No text could be found in the given URL (note that only HTML "
               "and plain text pages are supported, and content generated by "
               "JavaScript or found inside iframes is ignored)",
    "timeout": "The given URL timed out before any data could be retrieved",
    "search error": "An error occurred while using the search engine; try "
                    "reloading or setting 'use_engine' to 0",
}

def _serialize_page(page):
    return OrderedDict((("title", page.title), ("url", page.url)))

def _serialize_source(source, show_skip=True):
    if not source:
        return OrderedDict((
            ("url", None), ("confidence", 0.0), ("violation", "none")))

    conf = source.confidence
    data = OrderedDict((
        ("url", source.url),
        ("confidence", conf),
        ("violation", "suspected" if conf >= T_SUSPECT else
                      "possible" if conf >= T_POSSIBLE else "none")
    ))
    if show_skip:
        data["skipped"] = source.skipped
        data["excluded"] = source.excluded
    return data

def _serialize_detail(result):
    source_chain, delta = result.best.chains
    article = highlight_delta(None, result.article_chain, delta)
    source = highlight_delta(None, source_chain, delta)
    return OrderedDict((("article", article), ("source", source)))

def format_api_error(code, info):
    if isinstance(info, BaseException):
        info = type(info).__name__ + ": " + str(info)
    elif isinstance(info, unicode):
        info = info.encode("utf8")
    error_inner = OrderedDict((("code", code), ("info", info)))
    return OrderedDict((("status", "error"), ("error", error_inner)))

def _hook_default(query):
    info = u"Unknown action: '{0}'".format(query.action.lower())
    return format_api_error("unknown_action", info)

def _hook_check(query):
    do_check(query)
    if not query.submitted:
        info = ("The query parameters 'project', 'lang', and either 'title' "
                "or 'oldid' are required for checks")
        return format_api_error("missing_params", info)
    if query.error:
        info = _CHECK_ERRORS.get(query.error, "An unknown error occurred")
        return format_api_error(query.error.replace(" ", "_"), info)
    elif not query.site:
        info = (u"The given site (project={0}, lang={1}) either doesn't exist,"
                u" is closed, or is private").format(query.project, query.lang)
        return format_api_error("bad_site", info)
    elif not query.result:
        if query.oldid:
            info = u"The given revision ID doesn't seem to exist: {0}"
            return format_api_error("bad_oldid", info.format(query.oldid))
        else:
            info = u"The given page doesn't seem to exist: {0}"
            return format_api_error("bad_title", info.format(query.page.title))

    result = query.result
    data = OrderedDict((
        ("status", "ok"),
        ("meta", OrderedDict((
            ("time", result.time),
            ("queries", result.queries),
            ("cached", result.cached),
            ("redirected", bool(query.redirected_from))
        ))),
        ("page", _serialize_page(query.page))
    ))
    if result.cached:
        data["meta"]["cache_time"] = result.cache_time
    if query.redirected_from:
        data["original_page"] = _serialize_page(query.redirected_from)
    data["best"] = _serialize_source(result.best, show_skip=False)
    data["sources"] = [_serialize_source(source) for source in result.sources]
    if query.detail in ("1", "true"):
        data["detail"] = _serialize_detail(result)
    return data

def _hook_sites(query):
    update_sites()
    return OrderedDict((
        ("status", "ok"), ("langs", cache.langs), ("projects", cache.projects)
    ))

_HOOKS = {
    "compare": _hook_check,
    "search": _hook_check,
    "sites": _hook_sites,
}

def handle_api_request():
    query = Query()
    if query.version:
        try:
            query.version = int(query.version)
        except ValueError:
            info = "The version string is invalid: {0}".format(query.version)
            return format_api_error("invalid_version", info)
    else:
        query.version = 1

    if query.version == 1:
        action = query.action.lower() if query.action else ""
        return _HOOKS.get(action, _hook_default)(query)

    info = "The API version is unsupported: {0}".format(query.version)
    return format_api_error("unsupported_version", info)
