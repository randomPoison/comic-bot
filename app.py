from flask import Flask, render_template, redirect, url_for, abort, request
from random import randrange
import json
import threading
import os


app = Flask(__name__)


STRIPS_PER_PAGE = 10
"""The number of strips to show per page in the archive."""


DATABASE_FILE = os.environ.get("DATABASE_PATH", "database.json")
'''File to load/save our "database".'''


POSTS_FILE = "posts.json"
'''File containing all post metadata.'''


posts = []
'''List of all posts loaded from posts.json.'''


published_posts = {}
'''Dict of published posts keyed by ID.'''


latest_published_id = 1
'''ID of the most recent published post.'''

published_post_ids: list[int] = []
'''List of published post IDs for quick random selection.'''


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


def load_posts():
    global posts, published_posts, latest_published_id, published_post_ids
    with open(POSTS_FILE, 'r') as f:
        posts = json.load(f)

    # Build dict of published posts keyed by ID
    published_posts = { post['id']: post for post in posts if post.get('published', False) }
    # Build list of published post IDs (preserving file order)
    published_post_ids = [post['id'] for post in posts if post.get('published', False)]

    # Latest is the last published ID (preserving file order), or 1 if none
    latest_published_id = published_post_ids[-1] if published_post_ids else 1


# Why define a function when we're just going to invoke it immediately?
load_posts()
load_database()


# TODO: Make this a class I guess?
def strip(id: int) -> dict | None:
    # Lookup published post by ID (only published available)
    post = published_posts.get(id)
    if post is None:
        return None

    with database_lock:
        likes = database['likes'].get(str(id), {}).get('likes', 0)

    # Create a copy of the post and add likes and comic URL.
    result = post.copy()
    result['likes'] = likes
    result['url'] = url_for('static', filename=f"comics/{post['file']}")
    return result


@app.route("/")
@app.route("/comic/")
def comic_latest():
    num_pages = len(published_posts)
    return render_template("comic.html.jinja", strip=strip(latest_published_id), page=latest_published_id, num_pages=num_pages, route='comic')


@app.route("/comic/<int:page>")
def comic(page: int):
    # Validate the page number - check if it's a published post
    if page not in published_posts:
        abort(404)

    num_pages = len(published_posts)
    return render_template("comic.html.jinja", strip=strip(page), page=page, num_pages=num_pages, route='comic')


@app.route("/random")
def random():
    random_id = published_post_ids[randrange(len(published_post_ids))]
    return redirect(url_for('comic', page=random_id))


@app.route("/archive/")
def archive_home():
    return redirect(url_for('archive', page=1))


@app.route("/archive/<int:page>")
def archive(page: int):
    # Calculate total pages.
    num_published = len(published_posts)
    num_pages = (num_published + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        abort(404)

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Ordered published IDs newest first using precomputed list
    ordered_ids = list(reversed(published_post_ids))
    page_ids = ordered_ids[start_index:end_index]
    strips = [strip(i) for i in page_ids]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages, route='archive')


@app.post("/like/<int:id>")
def like(id: int):
    # Validate the comic number - check if it's a published post
    if id not in published_posts:
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
    num_published = len(published_posts)
    num_pages = (num_published + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        abort(404)

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Generate the list of strips sorted by likes.
    strips = [s for s in (strip(i) for i in published_post_ids) if s is not None]
    strips = sorted(strips, key=lambda s: s['likes'], reverse=True)
    strips = strips[start_index:end_index]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages, route='top')
