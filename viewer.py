import pickle
import sys
import argparse
import archiver
import sqlite3
import json

from flask import Flask, request, render_template, flash, url_for, redirect
app = Flask(__name__)

MAX_LIMIT = 50
GROUP_ID = None # Will be set once when program starts

@app.route("/")
def main_page():
    return render_template("main.html")

@app.route("/search/posts")
def search_posts():
    return search_web("post")

@app.route("/search/comments")
def search_comments():
    return search_web("comment")

def search_web(where):
    conn = get_conn(GROUP_ID)
    a = request.args
    limit = int(a.get("limit", 10))
    offset = int(a.get("offset", 0))
    results = search(where, conn, a.get("query"), limit, offset)
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
    return query(conn, sql, search_string, limit, offset)

sp = jsonize(curry(search, "post"))
sc = jsonize(curry(search, "comment"))
    
def query(conn, sql, *args):
    rows = conn.execute(sql, args).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]

def main():
    global GROUP_ID
    parser = argparse.ArgumentParser(description='Opens a saved group')
    parser.add_argument('group_id', action="store")
    parser.add_argument('-p', '--production', action="store_true")
    args = parser.parse_args()
    GROUP_ID = args.group_id
    if args.production:
        app.run(host="0.0.0.0", port=80)
    else:
        app.run(debug=True)

if __name__ == '__main__':
    main()
    