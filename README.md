# KUVO Playlist in Mastodon

This code posts the current playing song on KUVO Jazz 89.3FM Denver to Mastodon.

See the results in the account: https://botsin.space/@kuvo_playlist

There's a database included in the repository, `playlist.db`. I've only included it to have a backup in the repo, which is only a little sleazy. You can delete the `playlist.db` database and the next time the script runs it will create a new one.

## Playlist API

The `kuvo_playlist_api.py` file creates an API on port 5000. It has a `/songs_by_dj` endpoint which requires a `dj` URL parameter. This returns every song played by that DJ in the last 12 hours in the database. I intend to use this API to build playlists to go along with my radio recordings.


