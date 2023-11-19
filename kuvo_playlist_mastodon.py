#!/usr/bin/python

import time
import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from mastodon import Mastodon
from pprint import pprint


def write_state(file_path, id):
    with open(file_path, 'w') as file:
        file.write(id)
    return


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
            pprint(spin_item)
            # Get the value of the "data-spin" attribute
            data_spin_value = spin_item.get('data-spin')
            # Convert it to a dict
            data_spin_item = json.loads(data_spin_value)
            # Pull the time the song was played out of the <td>
            data_spin_item["time"] = spin_item.find('td', class_='spin-time').get_text(strip=True)
            if data_spin_item["i"] is None:
                data_spin_item["i"] = data_spin_item["s"]
                print(f"\n\n***** No ID on the song, so I set the i value to {data_spin_item['i']}\n\n")
        else:
            data_spin_item = json.loads({"i":"notfound","a":"artist_not_found","s":"song_not_found","r":"album_not_found"})
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


def post_to_mastodon(current_song, server, access_token):
    # Create an app on your Mastodon instance and get the access token
    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=server
    )
    # Text content to post
    text_to_post = current_song["time"] + " " + current_song["s"] + " by " + current_song["a"] + " from " + current_song["r"]
    alt_text = "An image of the cover of the record album '" + current_song["r"] + "' by " + current_song["a"]

    # Check if there's an image included. If there is, post it
    if current_song["image_status"] == "image":
    # URL of the image you want to attach
        image_data = requests.get(current_song["image"]).content
        # Upload the image and attach it to the status
        media = mastodon.media_post(image_data, mime_type='image/jpeg', description=alt_text)
        # Post the status with text and image attachment
        mastodon.status_post(text_to_post, media_ids=[media['id']])
    else:
        mastodon.status_post(text_to_post)
    print(f"\n\n***** Posted ID: {current_song['i']} to Mastodon.\n\n")
    return




# Setup Global Variables:
if len(sys.argv) > 1:
    working_directory = sys.argv[1]
    print (f"{working_directory} provided")
    config = get_config()
else:
    print("No working directory argument provided. Exiting.\n")
    sys.exit()

# Iterate
while True:
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
            print("\n\n***** Latest song not found.\n\n")
        else:
            post_to_mastodon(current_song, config["mastodon_server"], config["mastodon_access_token"])
            write_state(state_file, current_song["i"])
    else:
        print("\n\n***** Song already posted.\n\n")

    time.sleep(config["frequency"])