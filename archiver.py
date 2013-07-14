from facepy import GraphAPI
import argparse
import pickle
import sqlite3

LIMIT = 25

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
    f = open("bootstrap.sql", 'r')
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
               'search_string': lambda o: "Test",
               'to_name': lambda o: None,
               'message': if_present('message'), 
               'link': if_present('link'),
               'name': if_present('name'), 
               'caption': if_present('caption'), 
               'description': if_present('description'), 
               'source': if_present('source') ,
               'type': if_present('type')}

def insert_post(post, conn):
    result = {}
    for key, fn in POST_PARAMS.items():
        val = fn(post)
        if val:
            result[key] = val
    insert_column("post", result, conn)

def insert_column(table_name, key_val_map, conn):
    keys, vals = zip(*key_val_map.items())
    c = conn.cursor()
    c.execute("INSERT INTO {} ({}) VALUES ({})".format(
        table_name, ",".join(keys), ",".join(['?' for _ in keys])), vals)

#testing
def get_test_post():
    import random
    f = open('195621888632.dat', 'rb')
    data = pickle.load(f)
    return random.choice(data)

def get_group(graph, group_id):
    db_name = str(group_id) + ".db"
    try:
        with open(db_name): pass
    except IOError:
        create_new_db(db_name)
    conn = sqlite3.connect(db_name)

    response = graph.get("{0}/feed?limit={1}".format(group_id, LIMIT))
    total = 0
    while len(response["data"]) > 0:
        total += len(response['data'])
        map(lambda o: insert_post(o, conn), response['data'])
        
        newUrl = response["paging"]["next"].replace(
            "https://graph.facebook.com/", "")
        response = graph.get(newUrl)
        print "Getting posts, total {0}".format(total)

    # filename = "{0}.dat".format(group_id)
    # output = open(filename, "wb")
    # pickle.dump(data, output)
    # output.close()

    conn.commit()
    conn.close()
    print "Saved in database: " + db_name
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Downloads a facebook group')
    parser.add_argument('access_token', action="store")
    parser.add_argument('--group', '-g', metavar="group_id", action="store",
                        type=int)
    parser.add_argument('--opengroup', '-o', metavar="group_id", action="store",
                        type=int)
    args = parser.parse_args()
    graph = GraphAPI(args.access_token)
    
    if not args.group:
        print_groups(graph)
    else:
        get_group(graph, args.group)