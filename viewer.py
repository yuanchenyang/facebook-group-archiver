import argparse
import json
import sqlite3
import time
import sys
import os

try:
    import apsw
except: pass

import archiver

from collections import OrderedDict
from flask import Flask, request, render_template, flash, url_for, redirect
from werkzeug.serving import BaseRequestHandler

app = Flask(__name__)

MAX_LIMIT = 25
# Will be set once when program starts
GROUP_ID = None
PROD = False

# Used for caching queries, may not be threadsafe
# This probably isn't the right way to do it
db_modified_time = None
query_cache = {}

## HTML Pages
@app.route("/search")
def main_page():
    return render_template("search.html")

@app.route("/sql")
def sql_page():
    return render_template("sql.html")

@app.route("/")
def stats_page():

    colors = ["#E25A02", "#F1DB85", "#93D250", "#01A278", "#007BA7", "#9C014F",
              "#D18726", "#E7E7E7", "#CC6602", "#FED833", "#FDA8BB", "#FFFF66",
              "#336601", "#36C2A3", "#009900", "#FFCC66", "#DB9796", "#7F7F7F",
              "#96B2D7", "#C5E9DF"]
    color_index = [0] # hack for nonlocal variable
    name_colors = {}

    def get_color(name):
        if name not in name_colors:
            name_colors[name] = colors[color_index[0] % len(colors)]
            color_index[0] += 1
        return name_colors[name]


    def get_chart_data_by_date(table):
        sql = 'SELECT count(*) AS count, ' +\
              'STRFTIME("%Y-%m", SUBSTR(created_time, 1, 19)) ' +\
              'AS month FROM {} GROUP BY month ORDER BY month'.format(table)
        results = cached_sql_query(conn, sql)
        data = {}
        dataset = {"fillColor" : "rgba(86,61,124,0.5)",
                   "strokeColor" : "rgba(86,61,124,1)",
                   "pointColor" : "rgba(86,61,124,1)",
                   "pointStrokeColor" : "#fff"}
        dataset["data"] = [result["count"] for result in results]
        data["datasets"] = [dataset]
        data["labels"] = [result["month"] for result in results]
        return json.dumps(data)

    def get_top_ranked(table):
        sql = ("SELECT from_name, count(*) as count FROM {} GROUP BY from_name " +\
               "ORDER BY count DESC LIMIT 20").format(table)
        results = cached_sql_query(conn, sql)
        data = []
        for i, result in enumerate(results):
            color = get_color(result["from_name"])
            data.append({"value": result["count"], "color":color})
            result["color"] = color
        return results, data

    conn = get_conn(GROUP_ID)

    group = cached_sql_query(conn, "SELECT * FROM fb_group")[0]

    posts_data = get_chart_data_by_date("post")
    comments_data = get_chart_data_by_date("comment")
    rankings = {"post": get_top_ranked("post"),
                "comment": get_top_ranked("comment")}
    conn.close()
    return render_template("stats.html", **locals())

@app.route("/schema")
def schema_page():
    try:
        f = open("bootstrap.sql")
        schema = f.read()
        f.close()
    except:
        schema = "No schema found on server"
    return render_template("schema.html", **locals())

## Ajax endpoints
@app.route("/search/posts")
def search_posts():
    return query(search_web, "post")

@app.route("/search/comments")
def search_comments():
    return query(search_web, "comment")

@app.route("/query")
def query_web():
    return query(safe_query)

def query(fn, *args):
    a = request.args
    conn = get_conn(GROUP_ID)
    limit = int(a.get("limit", 10))
    offset = int(a.get("offset", 0))
    query = a.get("query")
    return fn(conn, query, limit, offset, *args)

def safe_query(conn, query, limit, offset):
    if limit > MAX_LIMIT :
        raise ViewerError("Limit exceeds MAX_LIMIT = " + str(MAX_LIMIT))
    try:
        results = sql_query(conn, query + " LIMIT ? OFFSET ?", limit, offset)
        results_length = len(results)
        return render_template("sql_result.html", **locals())
    except Exception as e:
        sql_str = query + " LIMIT {} OFFSET {}".format(limit, offset)
        return render_template("error.html", sql=sql_str, e=str(e))
    finally:
        conn.close()

def search_web(conn, query, limit, offset, where):
    results = search(where, conn, query, limit, offset)
    results_length=len(results)
    conn.close()
    return render_template("search_result.html", **locals())


class ViewerError(Exception):
    pass

def jsonize(fn):
    return lambda *args: json.dumps(fn(*args), indent=2)

def curry(fn, *args):
    return lambda *more_args: fn(*(args + more_args))

def get_conn(group_id):
    db_path = archiver.get_db_name(group_id)
    try:
        with open(db_path): pass
    except IOError:
        raise NameError("Database not found: " + db_path)

    if PROD:
        def row_trace(cursor, row):
            names = (l[0] for l in cursor.getdescription())
            return dict(zip(names, row))
        conn = apsw.Connection(db_path, flags=1) # SQLITE Read-Only flag
        conn.setrowtrace(row_trace)
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    return conn

def search(where, conn, search_string, limit=25, offset=0):
    if limit > MAX_LIMIT:
        raise ViewerError("Limit exceeds MAX_LIMIT = " + str(MAX_LIMIT))
    select_fields = ["from_name", "created_time", "id",
                     "snippet({}_fts) AS snippet".format(where)]
    sql = """SELECT {0} FROM {1}_fts JOIN {1} ON {1}_id={1}.id
             WHERE {1}_fts MATCH ? LIMIT ? OFFSET ?""".format(
                 ",".join(select_fields), where)
    return sql_query(conn, sql, search_string, limit, offset)

def sql_query(conn, sql, *args, **kwargs):
    cur = conn.cursor()
    rows = cur.execute(sql, args)
    ret_rows = []
    total = 0
    rate_limit = kwargs.get('rate-limit', True)
    for row in rows:
        total += 1
        if rate_limit and total > MAX_LIMIT:
            # Hard limit on maximum no. of rows that can be returned w/o paging
            break

        d = OrderedDict()
        for key in row.keys():
            d[key] = row[key]
        ret_rows.append(d)
    return ret_rows

def cached_sql_query(conn, sql, *args):
    global db_modified_time, query_cache
    last_mod_time = os.path.getmtime(archiver.get_db_name(GROUP_ID))

    if db_modified_time is None or last_mod_time > db_modified_time:
        # Flush cache
        query_cache = {}
        db_modified_time = last_mod_time

    query = sql + repr(args)

    if query in query_cache:
        return query_cache[query]
    else:
        result = sql_query(conn, sql, *args, rate_limit=False)
        query_cache[query] = result
        return result

class TimedRequestHandler(BaseRequestHandler):
    """Extend werkzeug request handler to suit our needs."""
    def handle(self):
        self.started = time.time()
        rv = super(TimedRequestHandler, self).handle()
        return rv

    def send_response(self, *args, **kw):
        self.processed = time.time()
        super(TimedRequestHandler, self).send_response(*args, **kw)

    def log_request(self, code='-', size='-'):
        duration = int((self.processed - self.started) * 1000)
        self.log('info', '"%s" %s %s [%sms]', self.requestline, code, size, duration)

def main():
    global GROUP_ID, PROD


    parser = argparse.ArgumentParser(description='Opens a saved group')
    parser.add_argument('group_id', action="store")
    parser.add_argument('-p', '--production', action="store_true")
    args = parser.parse_args()
    GROUP_ID = args.group_id
    PROD = args.production
    if PROD:
        global apsw # Hack so that app can still run in debug mode without APSW
        try :
            import apsw
        except:
            raise ViewerError("Viewer must use apsw for database connections " +
                              "during production mode")
        app.run(host="0.0.0.0", port=80, request_handler=TimedRequestHandler)
    else:
        print "Running in debug mode, full write access to database"
        app.run(debug=True, request_handler=TimedRequestHandler)

if __name__ == '__main__':
    main()
