import archiver
import unittest
import datetime
import os
import sqlite3
import pdb

YEAR = 2013
MONTH = 1
TEST_DB = "test"

def dt(day):
    return datetime.datetime(YEAR, MONTH, day).isoformat()

class FBObject(object):
    fields = ["created_time", "message", "from_name"]
    
    def __init__(self, message, day, from_name="Test Name"):
        assert 1 <= day <= 31, "Must be valid day!"
        self.created_time = dt(day)
        self.day = day
        self.message = message
        self.from_name = from_name
        
    def to_object(self):
        return {"created_time" : self.created_time,
                "message": self.message,
                "from": {"name" : self.from_name},
                "id" : self.id}

    def check_equals(self, conn):
        conn.row_factory = sqlite3.Row
        c = conn.cursor();
        select_query = "SELECT * FROM {} WHERE id={}".format(self.table, self.id)
        fts_query = 'SELECT * FROM {0}_fts WHERE {0}_id = "{1}"'\
                    .format(self.table, self.id)
        c.execute(select_query)
        row = c.fetchone()
        for field in self.fields:
            assert field in row.keys(), "Not in selected row: " + field
            assert row[field] == getattr(self, field), \
                "{} is not synced for: {}".format(field, str(self))
        c.execute(fts_query)
        fts_body = c.fetchone()["body"]
        assert self.message in fts_body, "Message not in fts table: {} " +\
            "\n---------------\n{}".format(message, fts_body)

    def __str__(self):
        s = {}
        for i in self.fields + ["id"]:
            s[i]=  getattr(self, i)
        return str(s)

    def __repr__(self):
        return self.__str__()

class Comment(FBObject):
    """Wrapper for a facebook comment"""
    fields = FBObject.fields + ["post_id"]
    # This variable autoincrement as more comments are added
    comment_id = 1

    def __init__(self, parent_post, message, day, from_name="Test Name"):
        FBObject.__init__(self, message, day, from_name)
        self.id = str(Comment.comment_id)
        self.post_id = parent_post.id
        self.table = "comment"
        Comment.comment_id += 1

    #def to_object(self):
    #    obj = FBObject.to_object(self)
    #    obj["updated_time"] = self.updated_time
    #    return obj


class Post(FBObject):
    """Wrapper for a facebook post, containing comments as well"""
    fields = FBObject.fields + ["updated_time"]
    # This variable autoincrement as more posts are added
    post_id = 1
        
    def __init__(self, message, day, from_name="Test Name"):
        FBObject.__init__(self, message, day, from_name)
        self.updated_time = dt(day)
        self.comments = []
        self.id = str(Post.post_id)
        self.table = "post"
        Post.post_id += 1
    
    def update(self, new_day, message=None, from_name=None):
        assert new_day > self.day
        self.updated_time = dt(new_day)
        self.day = new_day
        if message: self.message = message
        if from_name: self.from_name = from_name

    def _add_comment(self, message, day, from_name="Test Name"):
        self.comments.append(Comment(self, message, day, from_name))
        self.update(day)

    def check_equals(self, conn):
        FBObject.check_equals(self, conn)
        for comment in self.comments:
            comment.check_equals(conn)

    def to_object(self):
        obj = FBObject.to_object(self)
        obj["updated_time"] = self.updated_time
        return obj

    
class Graph(object):
    """Imitator for GraphAPI's graph object"""
    
    def __init__(self, ):
        """Takes in a list of post objects"""
        # Stores all created posts
        self.posts = {}

    def assert_day(self, day):
        if len(self.posts) > 0:
            max_day = max(post.day for post in self.posts.values())
            assert day > max_day,\
                "Inserted day {} must be greater than {}".format(day, max_day)
        
        
    def insert_post(self, post):
        self.assert_day(post.day)
        self.posts[str(post.id)] = post

    def check_equals(self, conn):
        for id, post in self.posts.items():
            post.check_equals(conn)
        return True
    
    def add_comment(self, post_id, message, day, from_name="Test Name"):
        self.assert_day(day)
        self.posts[post_id]._add_comment(message, day, from_name)

    def update(self, name, val, post_id, comment_id=None):
        """silently updates without setting updated time"""
        post = self.posts[post_id]
        if comment_id:
            for comment in post.comments:
                if comment.id == comment_id:
                    setattr(comment, name, val)
        else:
            setattr(post, name, val)
    
    def get(self, endpoint):
        path, query = endpoint.split('?')
        path = path.split('/')
        query = query.split('&')
        params = {}
        for item in query:
            key, val = item.split('=')
            params[key] = val

        def time_sort(item):
            if isinstance(item, Comment):
                return item.created_time
            return item.updated_time

        to_object = lambda li: [o.to_object() for o in li]
            
        if path[1] == "feed":
            posts = self.posts.values()
            limit = int(params["limit"])
            offset = int(params["offset"]) if "offset" in params else 0
            end = offset+limit
            return {"data": to_object(sorted(posts, key=time_sort,
                                             reverse=True)[offset:end]),
                    "paging": {"next" : "{}/feed?limit={}&offset={}".format(
                        path[0], limit, end)}}
        elif path[1] == "comments":
            post_id = path[0]
            return {"data": to_object(sorted(self.posts[post_id].comments,
                                             key=time_sort))}


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.graph = Graph()
        self.p1 = Post("p1", 2)
        self.p2 = Post("p2", 1)
        self.graph.insert_post(self.p2)
        self.graph.insert_post(self.p1)
        self.graph.add_comment(self.p2.id, "c1", 3)
        self.graph.add_comment(self.p2.id, "c2", 4)
        

class MetaTest(BaseTest):
    def setUp(self):
        BaseTest.setUp(self)
        self.res = self.graph.get("test/feed?limit=1")
    
    def test_paging_url(self):
        self.assertEqual("test/feed?limit=1&offset=1", self.res["paging"]["next"],
                         "Returns incorrect paging information")

    def test_paging_result(self):
        res2 = self.graph.get(self.res["paging"]["next"])
        self.assertIs(1, len(res2["data"]))
        self.assertEqual(self.p1.to_object(), res2["data"][0], "Is not p1")
        
    def test_post_updating(self):
        last_post = self.res["data"]
        post = self.res["data"][0]
        self.assertIs(1, len(self.res["data"]))
        self.assertEqual(self.p2.to_object(), post, "Is not p2")
        self.assertEqual(dt(4), post["updated_time"],
                         "Post does not update time when comment is added")

    def test_get_comments(self):
        post = self.res["data"][0]
        comments = self.graph.get(str(post["id"]) + "/comments?limit=1000")["data"]
        self.assertEqual("c1", comments[0]["message"], "Is not c1")
        self.assertEqual("c2", comments[1]["message"], "Is not c2")



class ArchiverTest(BaseTest):
    dbpath = archiver.BASE_PATH + "/databases/{}.db".format(TEST_DB)
    def setUp(self):
        try:
            os.remove(ArchiverTest.dbpath)
        except OSError: pass
        
        BaseTest.setUp(self)
        archiver.POST_LIMIT = 1

    def check_graph(self):
        conn = sqlite3.connect(ArchiverTest.dbpath)
        result = self.graph.check_equals(conn)
        conn.close()
        return result

    def ggp(self, *args, **kwargs):
        archiver.get_group_posts(self.graph, TEST_DB, *args, **kwargs)

    def test_get_posts(self):
        self.ggp()
        self.check_graph()

    def test_get_new_post(self):
        self.ggp()
        self.graph.insert_post(Post("p3", 5))
        self.ggp()
        self.check_graph()

    def test_get_new_comment(self):
        self.ggp()
        self.graph.add_comment(self.p1.id, "c3", 5)
        self.ggp()
        self.check_graph()

    def test_get_new_post_and_comment(self):
        self.ggp()
        p = Post("p4", 5)
        self.graph.insert_post(p)
        self.graph.add_comment(p.id, "c4", 6)
        self.ggp()
        self.check_graph()

    def test_get_multiple_posts(self):
        archiver.POST_LIMIT = 100
        self.ggp()
        self.check_graph()
        
    def test_update_and_insert(self):
        self.ggp()
        p = Post("p4", 5)
        self.graph.insert_post(p)
        self.graph.add_comment(p.id, "c4", 6)
        self.graph.add_comment(self.p1.id, "c5", 7)
        self.ggp()
        self.check_graph()

    def test_update_post_time(self):
        self.ggp()
        self.graph.update("updated_time", dt(5), self.p1.id)
        self.ggp()
        self.check_graph()
        
    def test_update_all(self):
        self.ggp()
        self.graph.update("from_name", "Me!", self.p1.id)
        self.graph.update("from_name", "You!", self.p2.id)
        self.ggp(update_posts=True)
        self.check_graph()

    def test_update_all_and_insert(self):
        self.ggp()
        p = Post("p4", 5)
        self.graph.insert_post(p)
        self.graph.add_comment(p.id, "c4", 6)
        self.graph.update("from_name", "Me!", self.p1.id)
        self.ggp(update_posts=True)
        self.check_graph()


if __name__ == '__main__':
    unittest.main(verbosity=2, exit=False, buffer=False)
    