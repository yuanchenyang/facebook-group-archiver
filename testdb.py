import sqlite3

f = open("bootstrap.sql", 'r')
init = f.read()

conn = sqlite3.connect('test.db')
c = conn.cursor()
c.execute(init)

conn.commit()
conn.close()