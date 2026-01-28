from flask import Flask
from redis import Redis
from rq import Queue
import os
from db import DB

from jobs import search_for_keyword

app = Flask(__name__)

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
q = Queue(connection=redis_conn)

@app.route("/")
def home():
    return "<p>Welcome to the Link Tree application!</p>"

@app.route("/test")
def test():
    print("hello world")
    return "<p>This will print 'Hello World' to console.</p>"

@app.route("/find_keyword/<keyword>")
def find_keyword(keyword):
    db = DB()
    try:
        # url_click_limit = request.args.get("click_limit", default=LINK_HARD_LIMIT, type=int)
        print(f"Searching for keyword {keyword}...")
        keyword_record = db.find_keyword(keyword)
        
        if keyword_record:
            status = keyword_record["status"]
            if status == "complete":
                links = keyword_record["result"]
                if links:
                    return f"<p>Result: {links}</p>"
                return "<p>No results found for this keyword</p>"
                
            elif status == "running":
                return "<p>Still searching for keyword!</p>"
        else:
            q.enqueue(search_for_keyword, keyword)
            return "<p>Starting a search for keyword!</p>"

        return "<p>Job was queued!</p>"
    except Exception as e:
        return f"<p>Something went wrong : {e}/</p>"
    finally:
        db.client.close()
