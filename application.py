from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
import json
import requests
from helpers import *
from datetime import datetime


# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///spotify.db")

CLIENT_ID = "8f43cf1138c540c2a5f38f9152dee009"
CLIENT_SECRET = "acba3ce8faa1433282cc75eefcd9b05c"
REDIRECT_URL = "https://ide50-edgarthornton.cs50.io/callback"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    
    # forget any user_id
    session.clear()
    url = "https://accounts.spotify.com/authorize/?client_id={}&response_type=code&redirect_uri={}&scope=user-read-private%20user-read-email&state=34fFs29kd09".format(CLIENT_ID, REDIRECT_URL)
    return redirect(url)
    

@app.route("/callback")
def callback():
    auth = request.args.get('code')
    
    data = {
        "grant_type": "authorization_code",
        "code": str(auth),
        "redirect_uri": REDIRECT_URL,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    
    post_request = requests.post("https://accounts.spotify.com/api/token", data = data)
    response_data = json.loads(post_request.text)

    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]
    
     # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization":"Bearer {}".format(access_token)}

    # Get profile data
    user_profile_api_endpoint = "https://api.spotify.com/v1/me"
    profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)

    profile_data = json.loads(profile_response.text)
    check = db.execute("SELECT * FROM users WHERE email = :email", email = profile_data['email'])    
    if not check:
        db.execute("INSERT INTO users (email) VALUES (:email)", email = profile_data['email'])
        check1 = db.execute("SELECT * FROM users WHERE email = :email", email = profile_data['email'])    
        session["user_id"] = check1[0]["user_id"]  
    if check: 
        session["user_id"] = check[0]["user_id"]    
    delete = db.execute("DELETE FROM temp_artist_data")
    delete = db.execute("DELETE FROM temp_track_data")
    
    
    # get top aritst info
    top_artist_api_endpoint = "https://api.spotify.com/v1/me/top/artists?time_range=long_term"
    top_artist_response = requests.get(top_artist_api_endpoint, headers=authorization_header)
    artists_data = json.loads(top_artist_response.text)
    
    # if no artist data
    if artists_data['total'] == 0:
        return apology("listen to more music")
        
    # set counting var
    i = 0    
    
    # while loop over number of artists 
    while (i < artists_data["limit"]):   
        
        # first step is to add artists into artist table
        
        # check to see if artist is in artist table
        artists_check = db.execute("SELECT * FROM artists WHERE spotify_artist_id = :spotify_artist_id", spotify_artist_id = artists_data['items'][i]['id'])    

        # if not insert artist into table     
        if not artists_check:
            artists_db = db.execute("INSERT INTO artists (spotify_artist_id) VALUES (:spotify_artist_id)", spotify_artist_id = artists_data['items'][i]['id'])    
            
            
        # gets artist_id
        id1 = db.execute("SELECT artist_id FROM artists WHERE spotify_artist_id = :spotify_artist_id", spotify_artist_id = artists_data['items'][i]['id'])
        artist_id1 = id1[0]["artist_id"]     
        # second step is to add artist into user artist table
        
        # set one var
        field = "artist{}".format(i)
        # check to see if user_artist_data has already been created
        check2 = db.execute("SELECT * FROM user_artist_data WHERE user_id = :user_id", user_id = session["user_id"])
        
        # if not create new row
        if not check2:
            artists_user = db.execute("INSERT INTO user_artist_data (artist0, user_id) VALUES (:artist0, :user_id)", artist0 = artist_id1, user_id = session["user_id"])    
    
        # if so update field with artist id
        if check2:
            artists_user = db.execute("UPDATE user_artist_data SET :field1 = :field WHERE user_id = :user_id", field1 = field, field = artist_id1, user_id = session["user_id"]) 
            
        
        # insert into tempart table     
        tempartdata = db.execute("INSERT INTO temp_artist_data (artist_id, name, image_url, artist_url) VALUES (:artist_id, :name, :image_url, :artist_url)", artist_id = artist_id1, name = artists_data['items'][i]['name'], image_url = artists_data['items'][i]['images'][0]['url'], artist_url = artists_data['items'][i]['external_urls']['spotify'])    
        
        # increases counting var 
        i = i + 1
    tempart = db.execute("SELECT * FROM temp_artist_data")
    
    # get top tracks info 
    top_tracks_api_endpoint = "https://api.spotify.com/v1/me/top/tracks?time_range=long_term"
    top_tracks_response = requests.get(top_tracks_api_endpoint, headers=authorization_header)
    tracks_data = json.loads(top_tracks_response.text)
    
    # return apology if no tracks
    if tracks_data['total'] == 0:
        return apology("listen to more music")
        
    # set counting varable    
    i = 0    
    
    # iterate over each song
    for element in tracks_data["items"]:   
        
        # first step is to insrt into tracks database
        
        # check to see if  is in track table
        tracks_check = db.execute("SELECT * FROM tracks WHERE spotify_track_id = :spotify_track_id", spotify_track_id = tracks_data['items'][i]['id'])    

        # if not insert track into table     
        if not tracks_check:
            tracks_db = db.execute("INSERT INTO tracks (spotify_track_id) VALUES (:spotify_track_id)", spotify_track_id = tracks_data['items'][i]['id'])    
            
            
        # gets track_id
        id2 = db.execute("SELECT track_id FROM tracks WHERE spotify_track_id = :spotify_track_id", spotify_track_id = tracks_data['items'][i]['id'])
        track_id1 = id2[0]['track_id']
            
        # second step is to add track into user track table
        
        # set one var
        field = "track{}".format(i)
        
        # check to see if user_track_data has already been created
        check2 = db.execute("SELECT * FROM user_track_data WHERE user_id = :user_id", user_id = session["user_id"])
        
        # if not create new row
        if not check2:
            tracks_user = db.execute("INSERT INTO user_track_data (track0, user_id) VALUES (:track0, :user_id)", track0 = track_id1, user_id = session["user_id"])    
    
        # if so update field with track id
        if check2:
            tracks_user = db.execute("UPDATE user_track_data SET :field1 = :field WHERE user_id = :user_id", field1 = field, field = track_id1, user_id = session["user_id"]) 
           
           
        # insert into tempart table     
        temptrakdata = db.execute("INSERT INTO temp_track_data (track_id, name, artist_name, image_url, track_url) VALUES (:track_id, :name, :artist_name, :image_url, :track_url)", track_id = track_id1, name = tracks_data['items'][i]['name'], artist_name= tracks_data['items'][i]['artists'][0]['name'], image_url = tracks_data['items'][i]['album']['images'][0]['url'], track_url = tracks_data['items'][i]['external_urls']['spotify'])    
        
        # increases counting var 
        i = i + 1
        
    temptrak = db.execute("SELECT * FROM temp_track_data")
    return render_template("stuff.html",temptrak = temptrak, tempart = tempart)
    



@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    
    # selects data from history table
    data = db.execute("SELECT * FROM history where id = :id", id=session["user_id"])
    if not data:
        return apology("unable to access user data")
    
    # returns history.html and data 
    return render_template("history.html", data = data) 


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()
    url = "https://www.spotify.com/us/logout/"
    # redirect user to login form
    return redirect(url)

