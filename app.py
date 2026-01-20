from flask import Flask
import math
from markupsafe import escape

import wiki_service

app = Flask(__name__)

@app.route('/')
def home():
    return "<p>Welcome to the Link Tree application!</p>"

@app.route("/wiki/<target>")
def wiki(target):
    target_string = f"{escape(target)}"
    return wiki_service.get_shortest_path(target_string)