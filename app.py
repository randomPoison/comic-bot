from flask import Flask, render_template, redirect, url_for, abort, request
from random import randrange
import json
import threading
import os


app = Flask(__name__)


LATEST_COMIC = 24
"""The latest comic that should be visible on the website. Comics with higher IDs are hidden."""


STRIPS_PER_PAGE = 10
"""The number of strips to show per page in the archive."""


DATABASE_FILE = os.environ.get("DATABASE_PATH", "database.json")
'''File to load/save our "database".'''


database_lock = threading.Lock()
'''Lock that must be acquired before reading/writing to the "database".'''


database = {}
'''Our "database", i.e. a dict that we load from disk.'''


def load_database():
    global database
    with database_lock:
        try:
            with open(DATABASE_FILE, 'r') as f:
                database = json.load(f)
        except FileNotFoundError:
            # Initialize with proper structure if file doesn't exist.
            database = {'likes': {}}
            with open(DATABASE_FILE, 'w') as f:
                json.dump(database, f, indent=4)
        
        # Ensure the database has the expected structure.
        if 'likes' not in database:
            database['likes'] = {}


# Why define a function when we're just going to invoke it immediately?
load_database()


# TODO: Make this a class I guess?
def strip(id: int) -> dict:
    """Builds the strip dict from the comic ID."""

    with database_lock:
        likes = database['likes'].get(str(id), {}).get('likes', 0)

    return {
        'id': id,
        'url': url_for('static', filename='comics/comic-{0:03d}.png'.format(id)),
        'likes': likes,
    }


@app.route("/")
@app.route("/comic/")
def comic_latest():
    return render_template("comic.html.jinja", strip=strip(LATEST_COMIC), page=LATEST_COMIC, num_pages=LATEST_COMIC, route='comic')


@app.route("/comic/<int:page>")
def comic(page: int):
    # Validate the page number.
    if page < 1 or page > LATEST_COMIC:
        abort(404)

    return render_template("comic.html.jinja", strip=strip(page), page=page, num_pages=LATEST_COMIC, route='comic')


@app.route("/random")
def random():
    page = randrange(1, LATEST_COMIC + 1)
    return redirect(url_for('comic', page=page))


@app.route("/archive/")
def archive_home():
    return redirect(url_for('archive', page=1))


@app.route("/archive/<int:page>")
def archive(page: int):
    # Calculate total pages.
    num_pages = (LATEST_COMIC + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        abort(404)

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Generate the list of strips.
    strips = list(range(LATEST_COMIC, 0, -1))
    strips = strips[start_index:end_index]
    strips = [strip(i) for i in strips]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages, route='archive')


@app.post("/like/<int:id>")
def like(id: int):
    # Validate the comic number.
    if id < 1 or id > LATEST_COMIC:
        abort(404)

    # Update the likes for the comic.
    with database_lock:
        comic_data = database['likes'].setdefault(str(id), {})
        likes = comic_data.setdefault('likes', 0)

        # Check the request's IP address to check for duplicate votes. We only
        # allow one vote per so that it's at least not trivial to cast votes.
        #
        # NOTE: This way of getting the IP address won't work if we run the
        # server behind a reverse proxy, because every request will have the
        # proxy's IP. If we end up doing that, we'll have to instead look at the
        # headers to see what the original IP was. But that approach has
        # additional details to consider, so we're going with the simple
        # approach to start.
        ip = request.remote_addr
        votes = comic_data.setdefault('votes', [])
        if ip not in votes:
            likes += 1
            comic_data['likes'] = likes
            votes.append(ip)

            # Update the database on disk with the new data.
            with open(DATABASE_FILE, 'w') as database_file:
                json.dump(database, database_file, indent=4)

    return {
        'likes': likes,
    }

@app.route("/top/")
def top_home():
    return redirect(url_for('top', page=1))


@app.route("/top/<int:page>")
def top(page: int):
    # Calculate total pages.
    num_pages = (LATEST_COMIC + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        abort(404)

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Generate the list of strips.
    strips = list(range(LATEST_COMIC, 0, -1))
    strips = [strip(i) for i in strips]
    strips = sorted(strips, key=lambda s: s['likes'], reverse=True)
    strips = strips[start_index:end_index]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages, route='top')
