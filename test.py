import archiver
import unittest
import datetime
import os

YEAR = 2013
MONTH = 1

def dt(day):
    return datetime.datetime(YEAR, MONTH, day)

class FBObject(object):
    def __init__(self, message, day, from_name="Test Name"):
        assert 1 <= day <= 31, "Must be valid day!"
        self.created_time = dt(day)
        self.day = day
        self.message = message
        self.from_name = from_name
        
    def to_object(self):
        return {"created_time" : self.created_time.isoformat(),
                "message": self.message,
                "from": {"name" : self.from_name},
                "id" : self.id}

    def __str__(self):
        return str(self.to_object())

    def __repr__(self):
        return self.__str__()

class Comment(FBObject):
    """Wrapper for a facebook comment"""
    comment_id = 1

    def __init__(self, parent_post, message, day, from_name="Test Name"):
        FBObject.__init__(self, message, day, from_name)
        self.id = Comment.comment_id
        self.post_id = parent_post.id
        Comment.comment_id += 1


class Post(FBObject):
    """Wrapper for a facebook post, containing comments as well"""
    
    # This variable autoincrement as more posts are added
    post_id = 1
        
    def __init__(self, message, day, from_name="Test Name"):
        FBObject.__init__(self, message, day, from_name)
        self.updated_time = dt(day)
        self.comments = []
        self.id = Post.post_id
        Post.post_id += 1
    
    def update(self, new_day, message=None, from_name=None):
        assert new_day > self.day
        self.updated_time = dt(new_day)
        self.day = new_day
        if message: self.message = message
        if from_name: self.from_name = from_name

    def add_comment(self, message, day, from_name="Test Name"):
        self.comments.append(Comment(self, message, day, from_name))
        self.update(day)

    def to_object(self):
        obj = FBObject.to_object(self)
        obj["updated_time"] = self.updated_time.isoformat()
        return obj

    
class Graph(object):
    """Imitator for GraphAPI's graph object"""
    
    def __init__(self, ):
        """Takes in a list of post objects"""
        # Stores all created posts
        self.posts = {}
        
    def insert_post(self, post):
        self.posts[str(post.id)] = post
    
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
        self.p2.add_comment("c1", 2)
        self.p2.add_comment("c2", 3)
        self.graph.insert_post(self.p1)
        self.graph.insert_post(self.p2)

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
        self.assertEqual(dt(3).isoformat(), post["updated_time"],
                         "Post does not update time when comment is added")

    def test_get_comments(self):
        post = self.res["data"][0]
        comments = self.graph.get(str(post["id"]) + "/comments?limit=1000")["data"]
        self.assertEqual("c1", comments[0]["message"], "Is not c1")
        self.assertEqual("c2", comments[1]["message"], "Is not c2")


class ArchiverTest(BaseTest):
    def setUp(self):
        try:
            os.remove(archiver.BASE_PATH + "/databases/test.db")
        except OSError: pass
                
        BaseTest.setUp(self)
        archiver.LIMIT = 1
        archiver.get_group_posts(self.graph, "test", False)

    def test_dummy(self):
        self.assertIs(1,1)


if __name__ == '__main__':
    unittest.main(verbosity=3)
    