#!/usr/bin/python

import sqlite3


sql = "select * from playlist order by datetime_column desc limit 1"

# Connect to the SQLite database
conn = sqlite3.connect('playlist.db')

# Create a cursor object to interact with the database
cursor = conn.cursor()

# Execute a query 
cursor.execute(sql)

# Fetch all the results
rows = cursor.fetchall()

# Print the column names
column_names = [description[0] for description in cursor.description]
print("Column Names:", column_names)

# Print the fetched rows
for row in rows:
    print(row)

# Close the connection
conn.close()