import pickle
import sys
import argparse
import archiver
import json
import sqlite3

from collections import OrderedDict
from flask import Flask, request, render_template, flash, url_for, redirect

app = Flask(__name__)

MAX_LIMIT = 50
GROUP_ID = None # Will be set once when program starts

@app.route("/")
def main_page():
    return render_template("main.html")

@app.route("/search/posts")
def search_posts():
    return query(search_web, "post")

@app.route("/search/comments")
def search_comments():
    return query(search_web, "comment")

@app.route("/query")
def query_web():
    return query(safe_query)

@app.route("/sql")
def sql_page():
    return render_template("sql.html")

@app.route("/stats")
def stats():
    conn = get_conn(GROUP_ID)
    return render_template("stats.html")

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
        return render_template("sql_result.html", results=results,
                               results_length=len(results), limit=limit,
                               offset=offset)
    except Exception as e:
        sql_str = query + " LIMIT {} OFFSET {}".format(limit, offset)
        return render_template("error.html", sql=sql_str, e=str(e))
    

def search_web(conn, query, limit, offset, where):
    results = search(where, conn, query, limit, offset)
    conn.close()
    return render_template("search_result.html", results=results, where=where,
                           limit=limit, offset=offset,
                           results_length=len(results))

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

    try:
        def row_trace(cursor, row):
            names = (l[0] for l in cursor.getdescription())
            return dict(zip(names, row))
        conn = apsw.Connection(db_path, flags=1) # SQLITE Read-Only flag
        conn.setrowtrace(row_trace)
    except:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    return conn

def search(where, conn, search_string, limit=25, offset=0):
    if limit > MAX_LIMIT:
        raise ViewerError("Limit exceeds MAX_LIMIT = " + str(MAX_LIMIT))
    select_fields = ["from_name", "created_time", "id",
                     "snippet({}_fts)".format(where)]
    sql = """SELECT {0} FROM {1}_fts JOIN {1} ON {1}_id={1}.id
             WHERE {1}_fts MATCH ? LIMIT ? OFFSET ?""".format(
                 ",".join(select_fields), where)
    return sql_query(conn, sql, search_string, limit, offset)

sp = jsonize(curry(search, "post"))
sc = jsonize(curry(search, "comment"))
    
def sql_query(conn, sql, *args):
    cur = conn.cursor()
    rows = cur.execute(sql, args).fetchall()
    ret_rows = []
    for row in rows:
        d = OrderedDict()
        for key in row.keys():
            d[key] = row[key]
        ret_rows.append(d)
    return ret_rows

def main():
    global GROUP_ID
    parser = argparse.ArgumentParser(description='Opens a saved group')
    parser.add_argument('group_id', action="store")
    parser.add_argument('-p', '--production', action="store_true")
    args = parser.parse_args()
    GROUP_ID = args.group_id
    if args.production:
        try :
            import apsw
        except:
            raise ViewerError("Viewer must use apsw for database connections " +
                              "during production mode")
        app.run(host="0.0.0.0", port=80)
    else:
        print "Running in debug mode, full write access to database"
        app.run(debug=True)

if __name__ == '__main__':
    main()
    