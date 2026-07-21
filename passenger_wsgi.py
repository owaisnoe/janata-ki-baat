"""cPanel 'Setup Python App' (Passenger) entry point.

cPanel expects a module-level `application` WSGI callable in this file.
Point the app's 'Application startup file' at passenger_wsgi.py and
'Application Entry point' at `application`.
"""
from app import create_app

application = create_app()
