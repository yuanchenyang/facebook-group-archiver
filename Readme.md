Facebook Group Archiver
=======================

Dependencies
------------
This package needs the `facepy` package, which needs the `requests` package.

```
pip install facepy
```

How to Use
----------
Get an access token with `user_groups` permission from [here]("https://developers.facebook.com/tools/explorer")


To view groups:
```
python archiver.py <access-token>
```

To archive a group, saving as a list of [post]("https://developers.facebook.com/docs/reference/api/post/") objects in a pickled file:
```
python archiver.py -g <group-id> <access-token>
```