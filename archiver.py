from facepy import GraphAPI
import argparse
import pickle
import sqlite3
import sys, os
import datetime
import iso8601

POST_LIMIT = 100
COMMENT_LIMIT = 1000

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = BASE_PATH + "/databases"

def get_date(*keys):
    def f(o):
        date = if_present(*keys)(o)
        if date:
            return iso8601.parse_date(date)
    return f

def if_present(*args):
    def get(obj):
        for arg in args:
            if isinstance(obj, dict) and arg in obj:
                obj = obj[arg]
            else:
                return None
        return obj
    return get

def print_groups(graph):
    groups = graph.get("me?fields=groups")
    try:
        data = groups["groups"]["data"]
        for g in data:
            print "name: " + g["name"]
            print "id  : " + g["id"]
            print
    except KeyError:
        raise ValueError("Invalid response: " + groups)

def create_new_db(db_name):
    f = open(BASE_PATH + "/bootstrap.sql", 'r')
    init = f.read()
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.executescript(init)
    conn.commit()
    conn.close()

POST_PARAMS = {'id': if_present('id'),
               'created_time': if_present('created_time'),
               'updated_time': if_present('updated_time'),
               'from_name': if_present('from', 'name'),
               'to_name': lambda o: None,
               'message': if_present('message'), 
               'link': if_present('link'),
               'name': if_present('name'), 
               'caption': if_present('caption'), 
               'description': if_present('description'), 
               'source': if_present('source') ,
               'type': if_present('type')}

COMMENT_PARAMS = {'id': if_present('id'),
                  'post_id': if_present('post_id'),
                  'from_name': if_present('from', 'name'),
                  'message': if_present('message'),
                  'created_time': if_present('created_time')}

def build_result(obj, params):
    result = {}
    for key, fn in params.items():
        val = fn(obj)
        if val:
            result[key] = val
    return result

def build_fts(result, kind):
    # Build searchable text
    fts = {'body' : '', kind+'_id': result['id']}
    for item in ['message', 'name', 'caption', 'description']:
        if item in result:
            fts['body'] += result[item] + " "
    return fts

def insert(conn, obj, params, kind):
    item_id = if_present('id')(obj)
    if exists(conn, item_id, kind):
        if kind == 'post':
            update_post(conn, obj, item_id)
            return
        elif kind == 'comment':
            return

    result = build_result(obj, params)
    if insert_row(conn, kind, result):
        insert_row(conn, kind+"_fts", build_fts(result, kind))

def update_post(conn, obj, post_id):
    c = conn.cursor()
    updated_time = if_present('updated_time')(obj)
    assert updated_time is not None
    try:
        c.execute("UPDATE post SET updated_time=? WHERE id=?",
                  (updated_time, post_id))
    except Exception as e:
        print >>sys.stderr, "Error updating post table: " + str(e)

def exists(conn, item_id, table_name):
    c = conn.cursor()
    return c.execute("select count(1) from {} where id=?".format(table_name),
                     (item_id,)).fetchone()[0] == 1

insert_comment = lambda comment, conn: insert(conn, comment,
                                              COMMENT_PARAMS, "comment")
insert_post = lambda post, conn: insert(conn, post, POST_PARAMS, "post")
    
def insert_row(conn, table_name, key_val_map, update=False):
    keys, vals = zip(*key_val_map.items())
    c = conn.cursor()
    try:
        c.execute("INSERT INTO {} ({}) VALUES ({})".format(
            table_name, ",".join(keys), ",".join(['?' for _ in keys])), vals)
        return True
    except Exception as e:
        print >>sys.stderr, "Error inserting {} into table {}: {}"\
                   .format(str(key_val_map), table_name, str(e))
        return False

def get_comments(conn, graph, post_id):
    """WARNING: this function only gets one set of comments, up to
    COMMENT_LIMIT. If the total number of comments is greater than
    COMMENT_LIMIT, this will not get all the comments. This will be fixed when I
    manage to figure out how to incrementally get all the comments, as
    facebook's comments API is pretty screwed up right now.

    """
    if post_id is None:
        return
    response = graph.get("{}/comments?limit={}".format(post_id, COMMENT_LIMIT))
    if 'data' in response and response['data']:
        for obj in response['data']:
            obj['post_id'] = post_id
            insert_comment(obj, conn)
        
def get_group_posts(graph, group_id, update):
    # Make databases directory if not present
    if not os.path.isdir(DATABASE_DIR):
        os.mkdir(DATABASE_DIR)
    db_name = DATABASE_DIR + "/" + str(group_id) + ".db"
    # Make <group_id>.db file if not present
    try:
        with open(db_name): pass
    except IOError:
        create_new_db(db_name)

    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    latest_time_str = c.execute("SELECT MAX(updated_time) FROM post;").fetchone()[0]
    if latest_time_str is None:
        # Database is empty
        latest_datetime = None
    else:
        latest_datetime = iso8601.parse_date(latest_time_str)
    def get_posts():
        response = graph.get("{0}/feed?limit={1}".format(group_id, POST_LIMIT))
        total = 0
        while 'data' in response and response['data'] and \
              len(response["data"]) > 0:
            for obj in response['data']:
                if update:
                    pass
                else:
                    time = iso8601.parse_date(if_present('updated_time')(obj))
                    print time, latest_datetime
                    if latest_datetime and time <= latest_datetime:
                        return total
                    insert_post(obj, conn)
                    get_comments(conn, graph, if_present('id')(obj))
                total += 1
            print "Getting posts, total {0}".format(total)
            conn.commit()
            newUrl = response["paging"]["next"].replace(
                "https://graph.facebook.com/", "")
            response = graph.get(newUrl)
        return total
    print "Inserted total {0}".format(get_posts())
    conn.commit()
    conn.close()
    print "Saved in database: " + db_name

def main():
    parser = argparse.ArgumentParser(description='Downloads a facebook group')
    parser.add_argument('access_token', action="store",
                        help="Token from facebook authentication")
    parser.add_argument('-u', '--update', action="store_true",
                        help="Updates all the posts of a group, if a group_id "+
                             "is provided")
    parser.add_argument('-g', '--group', metavar="group_id", action="store",
                        type=int, help="Archive a group")
    args = parser.parse_args()
    graph = GraphAPI(args.access_token)
    
    if not args.group:
        print_groups(graph)
    else:
        get_group_posts(graph, args.group, args.update)
        
if __name__ == '__main__':
    main()