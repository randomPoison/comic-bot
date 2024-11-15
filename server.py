from flask import Flask, render_template, redirect, url_for, abort
from random import randrange


app = Flask(__name__)


# TODO: Figure this out at startup by scanning the contents of `static/comics`.
NUM_COMICS = 11
"""The total number of comics."""


STRIPS_PER_PAGE = 10
"""The number of strips to show per page in the archive."""


# TODO: Make this a class I guess?
def strip(id: int) -> dict:
    """Builds the strip dict from the comic ID."""

    return {
        'id': id,
        'url': url_for('static', filename='comics/comic-{0:03d}.png'.format(id)),
    }


@app.route("/")
@app.route("/comic/")
def comic_latest():
    return render_template("comic.html.jinja", strip=strip(NUM_COMICS), page=NUM_COMICS, num_pages=NUM_COMICS, route='comic')


@app.route("/comic/<int:page>")
def comic(page: int):
    # Validate the page number.
    if page < 1 or page > NUM_COMICS:
        abort(404)

    return render_template("comic.html.jinja", strip=strip(page), page=page, num_pages=NUM_COMICS, route='comic')


@app.route("/random")
def random():
    page = randrange(NUM_COMICS)
    return redirect(url_for('comic', page=page))


@app.route("/archive/")
def archive_home():
    return redirect(url_for('archive', page=1))


@app.route("/archive/<int:page>")
def archive(page: int):
    # Calculate total pages.
    num_pages = (NUM_COMICS + STRIPS_PER_PAGE - 1) // STRIPS_PER_PAGE

    # Validate the page number.
    if page < 1 or page > num_pages:
        abort(404)

    # Calculate start and end indices.
    start_index = (page - 1) * STRIPS_PER_PAGE
    end_index = page * STRIPS_PER_PAGE

    # Generate the list of strips.
    strips = list(range(NUM_COMICS, 0, -1))
    strips = strips[start_index:end_index]
    strips = [strip(i) for i in strips]

    return render_template('archive.html.jinja', strips=strips, page=page, num_pages=num_pages, route='archive')
