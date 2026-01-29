from flask import Flask, session, request, jsonify
from db import DB
from redis import Redis
from jobs import start_crawl, visited_key, should_stop, stop_key
import os, uuid

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set! Set it in your environment.")

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

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
            if "user_id" not in session:
                session["user_id"] = str(uuid.uuid4())
            user_id = session["user_id"]
            db.create_keyword(keyword)
            crawl_id = start_crawl(user_id, keyword)

            return f"<p>Starting a search for keyword! crawl id is: {crawl_id}</p>"

        return "<p>Job was queued!</p>"
    except Exception as e:
        return f"<p>Something went wrong : {e}/</p>"
    finally:
        db.client.close()

@app.route("/stop_crawl/<keyword>")
def stop_crawl(keyword):
    user_id = session.get("user_id")
    
    if not user_id or not keyword:
        return jsonify({"error": "Missing user_id or keyword"}), 400

    redis_conn.set(stop_key(user_id, keyword), 1)
    return jsonify({"message": f"Crawl for keyword '{keyword}' stopped.", "crawl_id": f"{user_id}:{keyword}"})


@app.route("/crawl_status/<keyword>")
def crawl_status(keyword):
    user_id = session.get("user_id")

    if not user_id or not keyword:
        return jsonify({"error": "Missing user_id or keyword"}), 400

    stop = should_stop(user_id, keyword)
    visited_count = redis_conn.scard(visited_key(user_id, keyword))
    return jsonify({
        "crawl_id": f"{user_id}:{keyword}",
        "stopped": bool(stop),
        "urls_visited": visited_count
    })

