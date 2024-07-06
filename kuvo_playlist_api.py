#!/usr/bin/python

from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = '/home/pi/python/kuvo_playlist_mastodon/playlist.db'

# def init_db():
# 	conn = sqlite3.connect(DB_PATH)
# 	cursor = conn.cursor()
# 	cursor.execute('''
# 		CREATE TABLE IF NOT EXISTS playlist (
# 			id INTEGER PRIMARY KEY,
# 			datetime_column DATETIME,
# 			playlist_id TEXT,
# 			dj TEXT,
# 			song TEXT,
# 			artist TEXT,
# 			album TEXT,
# 			album_art TEXT
# 		)
# 	''')
# 	conn.commit()
# 	conn.close()

@app.route('/songs_by_dj', methods=['GET'])
def get_songs_by_dj():
	dj = request.args.get('dj')
	if not dj:
		return jsonify({'error': 'DJ name is required'}), 400
	
	# Calculate the time 12 hours ago from now
	twelve_hours_ago = datetime.now() - timedelta(hours=12)

	conn = sqlite3.connect(DB_PATH)
	cursor = conn.cursor()

	cursor.execute('''
		SELECT datetime_column, dj, song, artist, album
		FROM playlist
		WHERE dj = ? AND datetime_column >= ?
	''', (dj, twelve_hours_ago.strftime('%Y-%m-%d %H:%M:%S')))
	
	songs = cursor.fetchall()
	conn.close()

	# Format the results
	result = []
	for song in songs:
		result.append({
			'datetime': song[0],
			'dj': song[1],
			'song': song[2],
			'artist': song[3],
			'album': song[4]
		})

	return jsonify(result), 200

if __name__ == '__main__':
	# init_db()
	app.run(host='0.0.0.0', port=5000)
