from facepy import GraphAPI
import sys
import argparse
import json
import sqlite3
import pickle

LIMIT = 25

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

def get_group(graph, group_id):
    response = graph.get("{0}/feed?limit={1}".format(group_id, LIMIT))
    data = []
    while len(response["data"]) > 0:
        data.extend(response["data"])
        newUrl = response["paging"]["next"].replace(
            "https://graph.facebook.com/", "")
        response = graph.get(newUrl)
        print "Getting posts, total {0}".format(len(data))

    filename = "{0}.dat".format(group_id)
    output = open(filename, "wb")
    pickle.dump(data, output)
    output.close()

    print "Pickled into " + filename


        
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