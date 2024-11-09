from flask import Flask, render_template, redirect, url_for
from random import randrange

app = Flask(__name__)

# TODO: Figure this out at startup by scanning the contents of `static/comics`.
NUM_COMICS = 11
"""The total number of comics."""


STRIPS_PER_PAGE = 10
"""The number of strips to show per page in the archive."""


@app.route("/comic/<int:comic_id>")
def comic(comic_id: int):
    return render_template("comic.html.jinja", comic_id=comic_id, num_comics=NUM_COMICS)


@app.route("/random")
def random():
    comic_id = randrange(NUM_COMICS)
    return redirect(url_for('comic', comic_id=comic_id))


@app.route("/archive")
def archive_home():
    return redirect(url_for('archive', page=1))


@app.route("/archive/<int:page>")
def archive(page: int):
    # Calculate total pages.
    num_pages = (NUM_COMICS + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        return []  # Or raise an exception if you prefer

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Generate the list of images.
    strips = list(range(NUM_COMICS, 0, -1))
    strips = strips[start_index:end_index]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages)
