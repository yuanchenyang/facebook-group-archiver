import pickle
import sys
import argparse

def open_group(group_id):
    filename = "{0}.dat".format(group_id)
    pkfile = open(filename, 'rb')
    data = pickle.load(pkfile)
    for item in data:
        try:
            print item["message"][:70]
            print item["id"]
        except:
            print "error"
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Opens a saved group')
    parser.add_argument('group_id', action="store")
    args = parser.parse_args()
    open_group(args.group_id)