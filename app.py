from flask import Flask, request
from worker import enqueue_keyword_search
from redis import Redis
from rq import Queue
import os

app = Flask(__name__)

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
redis_conn = Redis.from_url(redis_url)
queue = Queue(connection=redis_conn)

@app.route('/')
def home():
    return "<p>Welcome to the Link Tree application!</p>"

@app.route('/test')
def test():
    print("hello world")
    return "<p>This will print 'Hello World' to console.</p>"

@app.route("/find_keyword/<keyword>")
def find_keyword(keyword):
    try:
        # url_click_limit = request.args.get('click_limit', default=LINK_HARD_LIMIT, type=int)

        print(f"Searching for keyword {keyword}...")
        enqueue_keyword_search(keyword)
        # result = db.find_keyword(keyword)

        # if result:
        #     status = result["status"]
        #     if status == "complete":
        #         links = result["result"]
        #         if links:
        #             return f"<p>Result: {links}</p>"
        #         return "<p>No results found for this keyword</p>"
                
        #     elif status == "running":
        #         return "<p>Still searching for keyword!</p>"
        # else:
        #     search_for_keyword.enqueue(keyword, click_limit)
        #     return "<p>Starting a search for keyword!</p>"

        return "<p>Job was queued!</p>"
    except Exception as e:
        return f"<p>Something went wrong : {e}/</p>"
