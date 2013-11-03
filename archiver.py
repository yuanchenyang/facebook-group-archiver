from facepy import GraphAPI
import argparse
import sqlite3
import sys
import os
import datetime
import iso8601

POST_LIMIT = 100
COMMENT_LIMIT = 1000

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = BASE_PATH + "/databases"

def if_present(*args):
    def get(obj):
        for arg in args:
            if isinstance(obj, dict) and arg in obj:
                obj = obj[arg]
            else:
                return None
        return obj
    return get

def compose(f, g):
    return lambda *args: f(g(*args))

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
               'from_id': if_present('from', 'id'),
               'to_name': compose(str, if_present("to", "data")),
               'message': if_present('message'),
               'link': if_present('link'),
               'name': if_present('name'),
               'caption': if_present('caption'),
               'description': if_present('description'),
               'source': if_present('source') ,
               'type': if_present('type'),
               'place': compose(str, if_present('place'))}

COMMENT_PARAMS = {'id': if_present('id'),
                  'post_id': if_present('post_id'),
                  'from_name': if_present('from', 'name'),
                  'message': if_present('message'),
                  'created_time': if_present('created_time')}

UPDATE_EXCLUDED = {'id', 'created_time', 'message'}

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
    result = build_result(obj, params)
    if insert_row(conn, kind, result):
        insert_row(conn, kind+"_fts", build_fts(result, kind))

def update(conn, update_dict, obj_id, table_name):
    c = conn.cursor()
    keys, vals = zip(*update_dict.items())
    query = "UPDATE {} SET {} WHERE id=?"\
        .format(table_name, ",".join(k + "=?" for k in keys))
    try:
        c.execute(query, vals + (obj_id,))
    except Exception as e:
        print >>sys.stderr, "Error updating {} table id {}: {}"\
                   .format(table_name, obj_id, e)

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
    facebook's comments API's paging is pretty screwed up right now.

    """
    if post_id is None:
        return
    response = graph.get("{}/comments?limit={}".format(post_id, COMMENT_LIMIT))
    comments = 0
    if 'data' in response and response['data']:
        for comment in response['data']:
            comment_id = if_present('id')(comment)
            if not exists(conn, comment_id, "comment"):
                comment['post_id'] = post_id
                if not if_present('message')(comment):
                    # Some comments may not have a message, we still need to
                    # insert something into the database:
                    comment['message'] = " "
                insert_comment(comment, conn)
                comments += 1
    return comments

def get_db_name(group_id):
     return DATABASE_DIR + "/" + str(group_id) + ".db"

def update_group_info(conn, graph, group_id):
    """Updates the fb_group table of the database"""
    result = graph.get(str(group_id))
    ip = if_present
    data = {"group_id": ip("id")(result),
            "owner_name": ip("owner", "name")(result),
            "name": ip("name")(result),
            "description": ip("description")(result),
            "updated_time": ip("updated_time")(result)}

    update(conn, data, 1, "fb_group") # 1 is the id of the only row in fb_group
                                      # table

def get_group_posts(graph, group_id, update_posts=False):
    # Make databases directory if not present
    if not os.path.isdir(DATABASE_DIR):
        os.mkdir(DATABASE_DIR)
    db_name = get_db_name(group_id)
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

    # Updates every time
    update_group_info(conn, graph, group_id)

    def get_posts():
        response = graph.get("{0}/feed?limit={1}".format(group_id, POST_LIMIT))
        posts_new = 0
        posts_updated = 0
        comments = 0

        while 'data' in response and response['data'] and \
              len(response["data"]) > 0:
            for post in response['data']:
                post_id = if_present('id')(post)
                time = iso8601.parse_date(if_present('updated_time')(post))
                if latest_datetime and time <= latest_datetime and\
                   not update_posts:
                    return posts_new, comments, posts_updated

                if exists(conn, post_id, "post"):
                    update_dict = {}
                    if update_posts:
                        # Update everything in post, not comments
                        for key, val in build_result(post, POST_PARAMS).items():
                            if key not in UPDATE_EXCLUDED:
                                update_dict[key] = val
                    else:
                        # Update "updated_time" and adds new comments
                        updated_time = if_present('updated_time')(post)
                        assert updated_time is not None
                        update_dict["updated_time"] = updated_time
                        comments += get_comments(conn, graph, post_id)

                    update(conn, update_dict, post_id, "post")
                    posts_updated += 1
                else:
                    # Insert new post and its comments
                    insert_post(post, conn)
                    comments += get_comments(conn, graph, post_id)
                    posts_new += 1

            print "Getting posts, total {0}".format(posts_new + posts_updated)
            conn.commit()
            newUrl = response["paging"]["next"].replace(
                "https://graph.facebook.com/", "")
            response = graph.get(newUrl)
        return posts_new, comments, posts_updated

    print "Inserted {} post(s), {} comment(s). Updated {} post(s)"\
        .format(*get_posts())
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
        get_group_posts(graph, args.group, update_posts=args.update)

if __name__ == '__main__':
    main()
