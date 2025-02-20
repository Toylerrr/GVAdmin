from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from requests.auth import HTTPBasicAuth
import configparser
import os

# Load configuration from config.ini
config = configparser.ConfigParser()

# Check if config.ini exists, if not create it with default values
config_file = 'config.ini'
if not os.path.exists(config_file):
    config['API'] = {'BaseURL': 'https://demo.gamevau.lt/api'}
    config['AUTH'] = {'Username': 'demo', 'Password': 'demodemo'}
    with open(config_file, 'w') as configfile:
        config.write(configfile)

config.read(config_file)

# Base URL of the external API
API_BASE_URL = config['API']['BaseURL']

# Basic Auth credentials
AUTH_USERNAME = config['AUTH']['Username']
AUTH_PASSWORD = config['AUTH']['Password']

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for flash messages and form security

@app.route('/')
def home():
    """
    Home page - Displays available options to interact with the GameVault server.
    """
    return render_template('index.html')

@app.route('/games', methods=['GET'])
def get_games():
    """
    Fetch and display the list of games.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/games", auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD))
        response.raise_for_status()  # Ensure the request succeeded

        # Extract the `data` key from the response JSON safely
        raw_data = response.json()  # API response
        games = raw_data.get("data", [])  # Use .get() in case `raw_data` is structured as a dictionary
        
        valid_games = []  # List to store validated games
        for game in games:
            if isinstance(game, dict):  # Ensure each game is a dictionary
                metadata = game.get('metadata', {}) or {}  # Safeguard: Fallback to empty dict if `metadata` is None
                cover = metadata.get('cover', {}) or {}  # Safeguard: Fallback to empty dict if `cover` is None
                game['cover_url'] = cover.get('source_url', '')  # Extract the cover URL safely
                valid_games.append(game)
            else:
                print(f"Skipping invalid game object: {game}")  # For debugging invalid entries

        return render_template('games.html', games=valid_games)
    
    except requests.exceptions.RequestException as e:
        flash(f"Error retrieving games: {e}", 'error')
        return redirect(url_for('home'))

@app.route('/game/<int:game_id>', methods=['GET', 'POST'])
def game_details(game_id):
    try:
        # Fetch game details from API
        response = requests.get(
            f"{API_BASE_URL}/games/{game_id}",
            auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD)
        )
        response.raise_for_status()
        game = response.json()

        # Process release date
        release_date = game.get('release_date')
        game['release_date'] = release_date.split('T')[0] if release_date else ''

        # Extract description
        game['description'] = game.get('metadata', {}).get('description', "No description available.")

        # Extract cover image
        game['cover_url'] = game.get('metadata', {}).get('cover', {}).get('source_url', '')

        # Extract screenshots
        game['screenshots'] = game.get('metadata', {}).get('url_screenshots', [])

        return render_template('game_details.html', game=game)
    except requests.exceptions.RequestException as e:
        flash(f"Error fetching game details: {e}", "error")
        return redirect(url_for('get_games'))

@app.route('/game/update/<int:game_id>', methods=['POST'])
def update_game(game_id):
    """
    Update game information using a PUT request.
    """
    try:
        game_data = {
            "name": request.form['name'],
            "description": request.form['description']
            # Add other fields as needed
        }
        response = requests.put(f"{API_BASE_URL}/games/{game_id}", json=game_data, auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD))
        response.raise_for_status()
        flash("Game updated successfully!", "success")
    except requests.exceptions.RequestException as e:
        flash(f"Error updating game: {e}", "error")
    return redirect(url_for('get_games'))

@app.route('/users', methods=['GET'])
def get_users():
    """
    Fetch and display the list of users.
    """
    try:
        # Fetch the list of users from the external API
        response = requests.get(f"{API_BASE_URL}/users", auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD))
        response.raise_for_status()
        users = response.json()  # Assume `response.json()` returns a list of users
        
        if not isinstance(users, list):
            flash("Unexpected response format. Please contact support.", "error")
            return redirect(url_for('home'))
        
        return render_template('users.html', users=users)

    except requests.exceptions.RequestException as e:
        flash(f"Error fetching users: {e}", 'error')
        return redirect(url_for('home'))
    

if __name__ == '__main__':
    app.run(debug=True)