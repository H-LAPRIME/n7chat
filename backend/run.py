"""
backend/run.py
──────────────
Entry point — run the Flask + SocketIO server.
"""

from app import create_app, socketio
from config import Config

app = create_app(Config)

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )
