# ai-music-recomender

########################################################################################

Hybrid AI music recommendation engine using Spotify/Last.fm APIs, ChromaDB, and React.

########################################################################################

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

In backend folder create ".env" file:

#Spotify Configuration

SPOTIPY_CLIENT_ID="..."

SPOTIPY_CLIENT_SECRET="..."

SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000/callback"

#Last.fm Configuration

LASTFM_API_KEY="..."

LASTFM_SECRET="..."

cd backend

windows:

python -m venv .venv

linux:

python3 -m venv .venv

Ctrl + Shift + P

Select python selece interpreter

Choose venv option

From this moment on, make sure that when using terminal, there is "(.venv)" at the beginig of the input line.

If it's not there, cloase the terminal with the dumpster button, open new one and wait for it to update.

If this doesn't help, turn off and on VS Code.

If nothing changes, it's probably because you choose wrong option in python selece interpreter or VS Code didn't register it correctly.

########################################################################################

To start the server, run

windows:

./start_server/start_server.bat

linux/mac os

(when using for the first time) chmod +x start_server/start_server.sh

./start_server/start_server.sh

Ctrl + C to shut down

You can see ai music recommender api at http://127.0.0.1:8000/docs

########################################################################################

warning trzeba pobrać Node.js z przeglądarki

1 Otwórz drugie, nowe okno terminala i wejdź do folderu frontendu:
cd frontend

2 Zainstaluj zależności zdefiniowane w pliku package.json:
npm install

3 Uruchom serwer deweloperski Vite:
npm run dev

########################################################################################
