"""
List of functions that return various numbers which are stored in the
admin database by the stats module.

All functions prefixed with `admin_range__` will be run for each day and the
result will be stored as the part after it. e.g. the result of
admin_range__foo will be stored under the key `foo`.

All functions prefixed with `admin_delta__` will be run for the current
day and the result will be stored as the part after it. e.g. the
result of `admin_delta__foo` will be stored under the key `foo`.

All functions prefixed with `admin_total__` will be run for the current
day and the result will be stored as `total_<key>`. e.g. the result of
`admin_total__foo` will be stored under the key `total__foo`.

Functions with names other than the these will not be called from the
main harness. They can be utility functions.

"""
import logging
import functools

import couchdb

class InvalidType(TypeError): pass

# Utility functions
def query_single_thing(db, typ, start, end):
    "Query the counts a single type from the things table"
    q1 = "SELECT id as id from thing where key='/type/%s'"% typ
    result = db.query(q1)
    try:
        kid = result[0].id 
    except IndexError:
        raise InvalidType("No id for type '/type/%s in the datbase"%typ)
    q2 = "select count(*) as count from thing where type=%d and created >= '%s' and created < '%s'"% (kid, start, end)
    result = db.query(q2)
    count = result[0].count
    return count


def single_thing_skeleton(**kargs):
    """Returns number of things of `type` added between `start` and `end`.

    `type` is partially applied for admin__[work, edition, user, author, list].
    """
    try:
        typ   = kargs['type']
        start = kargs['start'].strftime("%Y-%m-%d")
        end   = kargs['end'].strftime("%Y-%m-%d")
        db    = kargs['thingdb']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__%s"%(k, typ))
    return query_single_thing(db, typ, start, end)
    

# Public functions that are used by stats.py
def admin_range__human_edits(**kargs):
    """Calculates the number of edits between the `start` and `end`
    parameters done by humans. `thingdb` is the database.
    """
    try:
        start = kargs['start'].strftime("%Y-%m-%d")
        end   = kargs['end'].strftime("%Y-%m-%d")
        db    = kargs['thingdb']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__human_edits"%k)
    q1 = "SELECT count(*) AS count FROM transaction WHERE created >= '%s' and created < '%s'"% (start, end)
    result = db.query(q1)
    count = result[0].count
    return count


def admin_range__cover(**kargs):
    "Queries the number of covers added between `start` and `end`"
    try:
        start = kargs['start'].strftime("%Y-%m-%d")
        end   = kargs['end'].strftime("%Y-%m-%d")
        db    = kargs['coverdb']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__cover"%k)
    q1 = "SELECT count(*) as count from cover where created>= '%s' and created < '%s'"% (start, end)
    result = db.query(q1)
    count = result[0].count
    return count


admin_range__work    = functools.partial(single_thing_skeleton, type="work")
admin_range__edition = functools.partial(single_thing_skeleton, type="edition")
admin_range__user    = functools.partial(single_thing_skeleton, type="user")
admin_range__author  = functools.partial(single_thing_skeleton, type="author")
admin_range__list    = functools.partial(single_thing_skeleton, type="list")


def admin_total__author(**kargs):
    try:
        db    = kargs['seeds_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin_total__author"%k)    
    off1 = db.view("_all_docs", startkey="/authors",   limit=0, stale="ok").offset
    off2 = db.view("_all_docs", startkey="/authors/Z", limit=0, stale="ok").offset
    total_authors = off2 - off1
    return total_authors


def admin_total__subject(**kargs):
    try:
        db    = kargs['seeds_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin_total__subject"%k)
    rows = db.view("_all_docs", startkey="a", stale="ok", limit = 0)
    total_subjects = rows.total_rows - rows.offset
    return total_subjects


def admin_total__list(**kargs):
    try:
        db    = kargs['thingdb']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__total_list"%k)    
    # Computing total number of lists
    q1 = "SELECT id as id from thing where key='/type/list'"
    result = db.query(q1)
    try:
        kid = result[0].id 
    except IndexError:
        raise InvalidType("No id for type '/type/list' in the database")
    q2 = "select count(*) as count from thing where type=%d"% kid
    result = db.query(q2)
    total_lists = result[0].count
    return total_lists


def admin_total__cover(**kargs):
    try:
        db    = kargs['editions_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__total_cover"%k)    
    total_covers = db.view("admin/editions_with_covers", stale="ok").rows[0].value
    return total_covers


def admin_total__work(**kargs):
    try:
        db    = kargs['works_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__total_work"%k)    
    total_works = db.info()["doc_count"]
    return total_works


def admin_total__edition(**kargs):
    try:
        db    = kargs['editions_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__total_edition"%k)
    total_editions = db.info()["doc_count"]
    return total_editions


def admin_total__ebook(**kargs):
    try:
        db    = kargs['editions_db']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__total_ebook"%k)
    total_ebooks = db.view("admin/ebooks", stale="ok").rows[0].value
    return total_ebooks

def admin_delta__ebook(**kargs):
    try:
        editions_db = kargs['editions_db']
        admin_db    = kargs['admin_db']
        yesterday   = kargs['start']
        today       = kargs['end']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__delta_ebook"%k)
    current_total = editions_db.view("admin/ebooks", stale="ok").rows[0].value
    yesterdays_key = yesterday.strftime("counts-%Y-%m-%d")
    try:
        last_total = admin_db[yesterdays_key]["total_ebook"]
        logging.debug("Yesterdays count for total_ebook %s", last_total)
    except (couchdb.http.ResourceNotFound, KeyError):
        logging.warn("No total_ebook found for %s. Using 0", yesterdays_key)
        last_total = 0
    current_count = current_total - last_total
    return current_count

def admin_delta__subject(**kargs):
    try:
        editions_db = kargs['editions_db']
        admin_db    = kargs['admin_db']
        seeds_db    = kargs['seeds_db']
        yesterday   = kargs['start']
        today       = kargs['end']
    except KeyError, k:
        raise TypeError("%s is a required argument for admin__delta_ebook"%k)
    rows = seeds_db.view("_all_docs", startkey="a", stale="ok", limit=0)
    current_total = rows.total_rows - rows.offset
    yesterdays_key = yesterday.strftime("counts-%Y-%m-%d")
    try:
        last_total = admin_db[yesterdays_key]["total_subject"]
        logging.debug("Yesterdays count for total_subject %s", last_total)
    except (couchdb.http.ResourceNotFound, KeyError):
        logging.warn("No total_subject found for %s. Using 0", yesterdays_key)
        last_total = 0
    current_count = current_total - last_total
    return current_count