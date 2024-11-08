from flask import Flask, render_template

app = Flask(__name__)


@app.route("/comic/<int:comic_id>")
def comic(comic_id: int):
    return render_template("comic.html", comic_id=comic_id)
