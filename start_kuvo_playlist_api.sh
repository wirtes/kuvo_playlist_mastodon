#!/bin/bash
cd /home/pi/kuvo_playlist_mastodon/
export FLASK_APP=kuvo_playlist_api.py
/usr/bin/python3 -m flask run --host=0.0.0.0 --port=5000 > /home/pi/kuvo_playlist_mastodon/flask.log 2>&1
