import spotipy
import time
import os
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, url_for, request, redirect, session

SCOPES = "user-library-read playlist-modify-public playlist-read-private playlist-modify-private"
PORTNUMBER = 8080

app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = "Spotify Cookie"
load_dotenv()
app.secret_key = os.getenv("APP_SECRET_KEY")
TOKEN_INFO = "token_info"

#Default route, attempts to log user in through spotify and redirects them there
@app.route('/')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    print("AUTH URL: \n" + auth_url)
    return redirect(auth_url)

#once the user is logged in, redirect them to the create playlist page
@app.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for('create_playlist', external = True))



############################# CREATE PLAYLIST #######################################

@app.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    #return render_template('index.html', artist_name = f"Playlist successfully created with all 50 of Heux's songs!", spotify_src = "https://open.spotify.com/embed/playlist/5sf5Ks9FJjWtrDvSFx3rxv?utm_source=generator")

    #Check if the user is logged in
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        return redirect('/')
    
    sp = spotipy.Spotify(auth = token_info['access_token'])
    user_id = sp.current_user()['id']
    artist = None
    if request.method == 'POST':
    #Get the artist name from the form, check if its valid
        artist_name = request.form['content']
        if(artist_name == ""):
            return render_template('index.html', artist_name = "Please enter the name of an artist")
        
    #Get the artist from spotify, check if its valid
        artists = sp.search(q = artist_name, limit = 1, type = 'artist')
        if(len(artists['artists']['items']) == 0):
            return render_template('index.html', artist_name = "Artist not found")
        artist = artists['artists']['items'][0]

    #Get the artist's id and a list of all their albums
        artist_id = artist['id']
        artists_albums = sp.artist_albums(artist_id, album_type = 'album,single', limit = 50)
    #Get a list of all the artist's albums' uris
        all_artist_albums_uris = []
        for album in artists_albums['items']:
            all_artist_albums_uris.append(album['uri'])
    #Extract the list of tracks from each album
        tracks_list = []
        for uri in all_artist_albums_uris:
            tracks_list.append(sp.album(uri)['tracks'])
    #Loop through each track object and get the uri for the song
        tracks_uris = []
        for track in tracks_list:
            for item in track['items']:
                tracks_uris.append(item['uri'])
        amount_of_songs = len(tracks_uris)
    #Split the list of tracks into lists of 100 tracks
        tracks_uris_split_100 = [tracks_uris[i:i + 100] for i in range(0, len(tracks_uris), 100)]  
        if(len(tracks_uris_split_100) == 0):
            return render_template('index.html', artist_name = "Artist has no songs")
        
        playlist_of_all_songs = sp.user_playlist_create(user_id, f"Every {artist['name']} Song", True, None, None)
        for track in tracks_uris_split_100:
            sp.user_playlist_add_tracks(user_id, playlist_of_all_songs['id'], track, None)

        playlist_uri = playlist_of_all_songs['uri'].replace(':', '/')[-32:]
        print(playlist_uri)
        src = f"https://open.spotify.com/embed/{playlist_uri}?utm_source=generator"

        return render_template('index.html', artist_name = f"Playlist successfully created with all {amount_of_songs} of {artist['name']}'s songs!", spotify_src = src)
    else:
        return render_template('index.html')

############################# HELPER FUNCTIONS ######################################




############################# OAUTH AND TOKEN FUNCTIONS #############################

def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for('login', external = False))

    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

def create_spotify_oauth():
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    print("REDIRECT URI: \n" + url_for('redirect_page', _external=True) + "\n")

    return SpotifyOAuth(client_id = client_id,
                        client_secret = client_secret,
                        redirect_uri = url_for('redirect_page', _external=True),
                        scope = SCOPES
                        )

if __name__ == '__main__':
    app.run(debug=True, host="", port = PORTNUMBER)