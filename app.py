import asyncio
from flask import Flask, request, url_for, session, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import requests
import pandas as pd
import os
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from youtubesearchpython import VideosSearch
from pathlib import Path
import yt_dlp as youtube_dl
from threading import Thread

app = Flask(__name__)

app.secret_key = "Random String"
app.config['SESSION_COOKIE_NAME'] = 'Cookie'
TOKEN_INFO = "token_info"

@app.route('/')
def Home():
    # Read the file content
    with open("output.html", "r") as file:
        content = file.read()

    # Return the content as the response
    return content

@app.route('/Login')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirectPage():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect("/getTracks")

@app.route('/getTracks')
def get_all_tracks():
    try:
        token_info = get_token()
    except Exception as e:
        print("User not logged in:", e)
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    track_names = []  
    iter = 0
    while True:
        items = sp.current_user_saved_tracks(limit=50, offset=iter * 50)['items']
        for item in items:
            track = item['track']
            name = track['name'] + " - " + track['artists'][0]['name']
            
            track_names.append(name)  # Append the track name to the list      
        if len(items) < 50:
            break
        iter += 1 
        
    with open("waiting.html", "r") as file:
        content = file.read()
    
    # Start the download process in a separate thread
    def async_download():
        DownloadVideosFromTitles(track_names)
    
    download_thread = Thread(target=async_download)
    download_thread.start()

    return content

def DownloadVideosFromTitles(los):
    ids = []
    for index, item in enumerate(los):
        vid_id = ScrapeVidId(item)
        if vid_id:
            ids.append(vid_id)
    print("Downloading songs")
    print(ids)
    DownloadVideosFromIds(ids)


def DownloadVideosFromIds(lov):
    SAVE_PATH = str(os.path.join(Path.home(), "Downloads/songs"))
    try:
        os.mkdir(SAVE_PATH)
    except FileExistsError:
        print("Download folder exists")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': SAVE_PATH + '/%(title)s.%(ext)s',
    }
    x = 0
    print(lov)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for id in lov:
            ydl.download([lov[x]])
            x += 1
         
def ScrapeVidId(query):
    print("Getting video id for:", query)
    try:
        videosSearch = VideosSearch(query, limit=1)
        result = videosSearch.result()
        video_id = result['result'][0]['id']
        return video_id
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

def get_token():
    token_info = session.get(TOKEN_INFO)
    if not token_info:
        raise Exception("Token info not found in session")
    
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session[TOKEN_INFO] = token_info  # Update the session with the new token info
    
    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id="Insert Spotify Developer Id",
        client_secret="Insert Spotify Client Key",
        redirect_uri=url_for('redirectPage', _external=True),
        scope="user-library-read"
    )

if __name__ == '__main__':
    app.run(debug=True)
