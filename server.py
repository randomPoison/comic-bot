from flask import Flask, render_template

app = Flask(__name__)

# TODO: Figure this out at startup by scanning the contents of `static/comics`.
NUM_COMICS = 11
"""The total number of comics."""


@app.route("/comic/<int:comic_id>")
def comic(comic_id: int):
    return render_template("comic.html", comic_id=comic_id, num_comics=NUM_COMICS)
