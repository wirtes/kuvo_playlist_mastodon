#!/usr/bin/python

import time
import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from mastodon import Mastodon
from datetime import datetime
import re
from unidecode import unidecode
import sqlite3
from pprint import pprint


# Writes the state file
def write_state(file_path, id):
    with open(file_path, 'w') as file:
        file.write(id)
    return


# Reads the state from teh state file
def read_state(file_path):
    try:
        with open(file_path, 'r') as file:
            state = file.readline().strip()  # Read the first line and remove leading/trailing whitespace
    # If it fails, we don't have a state file yet. So make one.
    # This assumption is possibly dangerous. Time will tell.
    except:
        state = "starting up"
        write_state(file_path, state)
    return state


# Write playlist item into database
def write_database(song, db_file):
    # Connect to SQLite database (creates a new DB if it doesn't exist)
    conn = sqlite3.connect(db_file)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()
    # Create a table to store datetime
    cursor.execute('''CREATE TABLE IF NOT EXISTS playlist (
                        id INTEGER PRIMARY KEY,
                        datetime_column DATETIME,
                        playlist_id TEXT,
                        dj TEXT,
                        song TEXT,
                        artist TEXT,
                        album TEXT,
                        album_art TEXT
                        )''')
    # Get current datetime
    current_datetime = datetime.now()
    # Create Insert Statement
    sql = 'INSERT INTO playlist (datetime_column, playlist_id, dj, song, artist, album, album_art) VALUES (?, ?, ?, ?, ?, ?, ?)'
    # Insert current datetime into the table
    cursor.execute(sql, (current_datetime, song["i"], song['dj'], song['s'], song['a'], song['r'], song['image']))
    # Commit changes and close connection
    conn.commit()
    conn.close()
    return


# Loads the configuration file. Do all config in ./config/config.json & exclude from repo.
def get_config():
    try:
        with open(working_directory + '/config/config.json', 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print("Config file not found.")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to fix the style of the time that the song played
# example: changes "12:11 PM" to ""12:11pm"
def format_time(time_str):
    modified_time = time_str[:-3] + time_str[-3].replace(" ", "") + time_str[-2:].lower()
    return modified_time


# Cleanse the string
def clean_string(string):
    # Using unidecode to convertion UTF-8 diacriticals to standard ASCII because people probably won't type them in hashtags
    text = unidecode(string)
    # Remove any special characters, new lines, and spaces
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', text.replace('\n', '').replace(' ', ''))
    return clean_text


# Let's make some #hashtags!
def make_hashtags(artist, song, dj, always_tag):
    hashtag_string = "#" + clean_string(artist)
    hashtag_string += " #" + clean_string(song)
    hashtag_string += " #" + clean_string(dj)
    hashtag_string += " " + always_tag
    return hashtag_string


# Scrapes the KUVO playlist page & gets the current artist, song, album, art & song ID
# Sometimes the "Now Playing" song is more current on the KUVO playlist site. But it doesn't
# contain the name of the album & it rarely contains album art. So I'm choosing to read from
# the playlist table in order to get richer information.
def get_current_song(playlist_url, album_art_size):
    # Get the playlist HTML from KUVO
    response = requests.get(playlist_url)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the <tr> tag with class "spin-item"
        spin_item = soup.find('tr', class_='spin-item')
        # Check if the tag with class "spin-item" is found
        if spin_item:
            # Uncomment to debug. This will print the scraped HTML section of the playlist so you can see what's going on
            # pprint(spin_item)
            # Get the value of the "data-spin" attribute
            data_spin_value = spin_item.get('data-spin')
            # Convert it to a dict
            data_spin_item = json.loads(data_spin_value)
            # Pull the time the song was played out of the <td>
            data_spin_item["time"] = format_time( spin_item.find('td', class_='spin-time').get_text(strip=True) )
            if data_spin_item["i"] is None:
                data_spin_item["i"] = data_spin_item["s"]
                print(f"***** No ID on the song, so I set the i value to {data_spin_item['i']}")
        else:
            data_spin_item = json.loads({"i":"notfound","a":"artist_not_found","s":"song_not_found","r":"album_not_found"})
        # Find the DJ
        data_spin_item["dj"] = soup.find('h3', 'show-title').get_text(strip=True).title()
        # Get the image source
        img_tag = spin_item.find('td', class_='spin-art').find('img')
        if img_tag:
            # Get the value of the "src" attribute
            src_attribute = img_tag.get('src')
            # Check if the "src" attribute exists
            if src_attribute:
                # push album art link into data_spin_item and resize to size specified in config
                data_spin_item["image"] = src_attribute.replace("170x170", album_art_size)
            # Check if there's generic art because there's no album image:
            if data_spin_item["image"] == "https://spinitron.com/static/pictures/placeholders/loudspeaker.svg":
                data_spin_item["image_status"] = "no image"
            else:
                data_spin_item["image_status"] = "image"

    return data_spin_item 


# Your standard posting to Mastodon function
def post_to_mastodon(current_song, server, access_token):
    # Create an app on your Mastodon instance and get the access token
    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=server
    )
    # Text content to post
    text_to_post = current_song["time"] + " " + current_song["s"] + " by " + current_song["a"] + " from " + current_song["r"]
    text_to_post += "\n" + make_hashtags(current_song["a"], current_song["s"], current_song["dj"], config["hashtags"])
    print(text_to_post)
    alt_text = "An image of the cover of the record album '" + current_song["r"] + "' by " + current_song["a"]

    # Check if there's an image included. If there is, post it
    if current_song["image_status"] == "image":
    # URL of the image you want to attach
        image_data = requests.get(current_song["image"]).content
        # Upload the image and attach it to the status
        media = mastodon.media_post(image_data, mime_type='image/jpeg', description=alt_text)
        # Post the status with text and image attachment
        mastodon.status_post(status=text_to_post, media_ids=[media['id']], visibility="public")
    else:
        mastodon.status_post(status=text_to_post, visibility="public")
    print(f"***** Posted ID: {current_song['s']} by {current_song['a']} to Mastodon at {formatted_datetime}")
    return 


def orchestration_function():
    # Get the information about the current song playing
    current_song = get_current_song(config["playlist_url"], config["album_art_size"])
    # pprint(current_song)
    state_file = working_directory + "/state"
    # Get the latest ID written to the state file
    last_post = read_state(state_file)

    # Check if we've already posted this song by comparing the ID we recieved from the scrape
    # with the one in the state file
    if current_song["i"] != last_post:
        # Make sure we got a good scrape of playlist page
        if current_song["i"] == "notfound":
            print(f"***** Latest song not found.  {formatted_datetime}")
        else:
            post_to_mastodon(current_song, config["mastodon_server"], config["mastodon_access_token"])
            write_state(state_file, current_song["i"])
            write_database(current_song, working_directory + "/" + config["database"])
    else:
        print(f"***** Song: {current_song['s']} by {current_song['a']} already posted.  {formatted_datetime}")
    return


# Setup Global Variables:
if len(sys.argv) > 1:
    working_directory = sys.argv[1]
    print (f"{working_directory} provided")
    config = get_config()
else:
    print("No working directory argument provided. Exiting.\n")
    sys.exit()

for i in range(0, config["times_to_poll_per_minute"] - 1):
    # Get the current date and time
    current_datetime = datetime.now()
    # Format the date and time into a human-readable form
    formatted_datetime = current_datetime.strftime("%A, %B %d, %Y %I:%M:%S %p")
    orchestration_function()
    # Don't sleep after the last run 
    if i < (config["times_to_poll_per_minute"] - 1):
        time.sleep(60 / config["times_to_poll_per_minute"])


