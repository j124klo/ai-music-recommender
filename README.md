# ai-music-recomender

################################################################################################

Hybrid AI music recommendation engine using Spotify/Last.fm APIs, ChromaDB, and React.

################################################################################################

After downloading code from github:
In main ai-music-recommender folder, create folder ".vscode" with "settings.json" file inside

windows:
{
"python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
}
linux:
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python"
}

cd backend
windows:
python -m venv .venv
linux:
python3 -m venv .venv
Ctrl + Shift + P
Select python selece interpreter
Choose venv option

In backend folder create ".env" file:
#Spotify Configuration
SPOTIPY_CLIENT_ID="93f76b85a37243fc9df1a54bbc3cf6bd"
SPOTIPY_CLIENT_SECRET="90ddba580b734d0d9e7df475f1bfb1c3"
SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000/callback"
#Last.fm Configuration
LASTFM_API_KEY="..."
LASTFM_SECRET="..."

################################################################################################

To start the server, run
windows:
./backend/start_backend/start_backend.bat
linux/mac os
(when using for the first time) chmod +x backend/start_backend/start_backend.sh
./backend/start_backend/start_backend.sh
Ctrl + C to shut down

################################################################################################
