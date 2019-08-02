import os

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = BASE_PATH + "/databases"

def get_db_name(group_id):
     return DATABASE_DIR + "/" + str(group_id) + ".db"