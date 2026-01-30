from flask import Flask
from db import DB
from redis import Redis
from jobs import start_crawl, visited_key, stop_keyword, is_active, get_elapsed_time
import os

app = Flask(__name__)

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

@app.route("/")
def home():
    return "<p>Welcome to the Link Tree application!</p>"

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
                return f"<p>No results found for keyword: {keyword}.</p>"
                
            elif status == "running":
                return f"""
                <p>Searching for keyword: {keyword}. This could take a while...</p>
                <a href="../crawl_status/{keyword}">status</a>
                """
        else:
            db.create_keyword(keyword)
            start_crawl(keyword)

            return f"<p>Starting a keyword search for: {keyword}</p>"

        return "<p>Job was queued!</p>"
    except Exception as e:
        return f"<p>Something went wrong: {e}/</p>"
    finally:
        if db:
            db.client.close()

@app.route("/stop_crawl/<keyword>")
def stop_crawl(keyword):
    stop_keyword(keyword)
    return f"<p>Crawl for keyword '{keyword}' stopped.</p>"


@app.route("/crawl_status/<keyword>")
def crawl_status(keyword):
    visited_count = redis_conn.scard(visited_key(keyword))
    return f"""
    <p>URLs visited for keyword {keyword}: {visited_count}.</p>
    <p>Status: {"Active" if is_active(keyword) == 1 else "Finished"}</p>
    <p>Elapsed time: {get_elapsed_time(keyword):.2f}s</p>
    """

