import os
import logging as log
import json
import time

from redis import Redis
from rq import Queue
import link_service as ls
from db import DB

# ---- Logging ----
log.basicConfig(level=log.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---- Config ----
JOB_QUEUE_TIMEOUT = 300
DEPTH_LIMIT = 5
START_URL = "https://en.wikipedia.org/wiki/Dressage_judge"
CRAWL_WORKERS = 25  # number of crawl workers per keyword

# ---- Redis / Queues ----
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

keyword_q = Queue("keyword", connection=redis_conn, default_timeout=JOB_QUEUE_TIMEOUT)
crawl_q = Queue("crawl", connection=redis_conn, default_timeout=JOB_QUEUE_TIMEOUT)

# ---- Redis keys ----
def active_key(keyword):
    return f"keyword:{keyword}:active"

def frontier_key(keyword):
    return f"keyword:{keyword}:frontier"

def visited_key(keyword):
    return f"keyword:{keyword}:visited"

# ---- Helpers ----
def serialize(url, depth):
    return json.dumps({"url": url, "depth": depth})

def deserialize(item):
    data = json.loads(item)
    return data["url"], data["depth"]

def is_active(keyword):
    return redis_conn.exists(active_key(keyword))

def stop_keyword(keyword):
    redis_conn.delete(active_key(keyword))

def mark_visited(keyword, url):
    return redis_conn.sadd(visited_key(keyword), url) == 1

def build_ui_links(urls):
    return "<br>".join(f"<a href='{u}'>{u}</a>" for u in urls)

def get_elapsed_time(keyword):
    start_time = float(redis_conn.get(f"keyword:{keyword}:start_time") or time.time())
    end_time = time.time()
    return end_time - start_time

# ---- Crawl worker ----
def crawl_worker(keyword):
    """Process URLs from the frontier until empty or keyword found."""
    log.info(f"[{keyword}] Crawl worker started")

    db = DB()

    try:
        while is_active(keyword):
            item = redis_conn.lpop(frontier_key(keyword))
            if not item:
                # frontier empty → stop keyword
                log.info(f"[{keyword}] Frontier empty, stopping crawl")
                get_elapsed_time(keyword)
                log.info(f"Elapsed time was: {elapsed_time:.2f}s")
                stop_keyword(keyword)
                break

            url, depth = deserialize(item)

            if depth >= DEPTH_LIMIT:
                log.info(f"[{keyword}] Reached depth limit at {url}")
                continue

            if not mark_visited(keyword, url):
                log.info(f"[{keyword}] Already visited {url}, skipping")
                continue

            log.info(f"[{keyword}] Crawling {url} (depth={depth})")

            try:
                result = ls.search_for_keyword(keyword, url)

                # Keyword found → write to DB and stop
                if result.get("status") == "success":
                    links = result.get("result") or []
                    html = build_ui_links(links)
                    elapsed_time = get_elapsed_time(keyword)
                    elapsed_time_msg = f"Elapsed time was: {elapsed_time:.2f}s"
                    log.info(elapsed_time_msg)

                    db_result = f"{len(links)} keyword matches found at {url} in {depth} clicks. {elapsed_time_msg}<br>{html}"
                    db.update_keyword_with_result(keyword, db_result)

                    log.info(f"[{keyword}] Keyword FOUND at {url} — stopping crawl")
                    stop_keyword(keyword)
                    break

                if result.get("status") == "failure":
                    continue

                # Push discovered links to frontier
                for link in result.get("result") or []:
                    if is_active(keyword):
                        redis_conn.rpush(frontier_key(keyword), serialize(link, depth + 1))

            except Exception as e:
                log.warning(f"[{keyword}] Error crawling {url}: {e}")

            # Optional: small sleep to avoid hammering
            time.sleep(0.1)
    finally:
        db.client.close()
        log.info(f"[{keyword}] Crawl worker exiting")

# ---- Keyword job ----
def keyword_job(keyword):
    log.info(f"[{keyword}] Keyword job started")
    start_time = time.time()
    redis_conn.set(f"keyword:{keyword}:start_time", start_time)

    # Initialize state
    redis_conn.set(active_key(keyword), 1)
    redis_conn.delete(frontier_key(keyword))
    redis_conn.delete(visited_key(keyword))

    # Seed frontier
    redis_conn.rpush(frontier_key(keyword), serialize(START_URL, 0))

    # Start fixed number of crawl workers
    for _ in range(CRAWL_WORKERS):
        crawl_q.enqueue(crawl_worker, keyword)

    log.info(f"[{keyword}] Enqueued {CRAWL_WORKERS} crawl workers (non-blocking)")

# ---- Public API ----
def start_crawl(keyword):
    keyword_q.enqueue(keyword_job, keyword)
    log.info(f"[{keyword}] Enqueued keyword job")
