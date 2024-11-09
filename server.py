from flask import Flask, render_template, redirect, url_for
from random import randrange

app = Flask(__name__)

# TODO: Figure this out at startup by scanning the contents of `static/comics`.
NUM_COMICS = 11
"""The total number of comics."""


@app.route("/comic/<int:comic_id>")
def comic(comic_id: int):
    return render_template("comic.html.jinja", comic_id=comic_id, num_comics=NUM_COMICS)


@app.route("/random")
def random():
    comic_id = randrange(NUM_COMICS)
    return redirect(url_for('comic', comic_id=comic_id))
