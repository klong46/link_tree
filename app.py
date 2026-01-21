from flask import Flask, request
from markupsafe import escape

LINK_HARD_LIMIT = 5

import link_service

app = Flask(__name__)

@app.route('/')
def home():
    return "<p>Welcome to the Link Tree application!</p>"

@app.route("/find_keyword/<target>")
def find_keyword(target):
    click_limit = LINK_HARD_LIMIT
    url_click_limit = request.args.get('click_limit', default=LINK_HARD_LIMIT, type=int)
    if url_click_limit <= LINK_HARD_LIMIT:
        click_limit = url_click_limit
    target_string = f"{escape(target)}"
    return link_service.get_shortest_path(target_string, click_limit)