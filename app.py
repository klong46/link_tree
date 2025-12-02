from flask import Flask
import math
from markupsafe import escape

import wiki_service

app = Flask(__name__)

@app.route('/')
def hello_world():
    return "<p>Hello World</p>"

@app.route('/test')
def test():
    return "<p>This is a test</p>"

@app.route("/sqrt/<int:num>")
def sqrt(num):
    sqrt = math.sqrt(num)
    return f"The square root of the url num is: {sqrt}"

@app.route("/wiki/<target>")
def wiki(target):
    target_string = f"{escape(target)}"
    return wiki_service.get_shortest_path(target_string)