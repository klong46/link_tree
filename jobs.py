import time
import json
import logging as log
from redis import Redis
from rq import Queue
import link_service as ls
from db import DB
import os

log.basicConfig(level=log.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---- Config ----
KEYWORD_QUEUE_TIMEOUT = 86400 # 24 hours
CRAWL_QUEUE_TIMEOUT = 86400 # 24 hours
DEPTH_LIMIT = 5
START_URL = "https://en.wikipedia.org/wiki/Dressage_judge"
CRAWL_WORKERS = 30
BATCH_SIZE = 50

# ---- Redis / Queues ----
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

keyword_q = Queue("keyword", connection=redis_conn, default_timeout=KEYWORD_QUEUE_TIMEOUT)
crawl_q = Queue("crawl", connection=redis_conn, default_timeout=CRAWL_QUEUE_TIMEOUT)

# ---- Redis keys ----
def active_key(keyword):
    return f"keyword:{keyword}:active"

def frontier_key(keyword):
    return f"keyword:{keyword}:frontier"

def visited_key(keyword):
    return f"keyword:{keyword}:visited"

def start_time_key(keyword):
    return f"keyword:{keyword}:start_time"

# ---- Helpers ----
def serialize(url, depth):
    return json.dumps({"url": url, "depth": depth})

def deserialize(item):
    data = json.loads(item)
    return data["url"], data["depth"]

def is_active(keyword):
    return redis_conn.exists(active_key(keyword))

def stop_keyword(keyword):
    redis_conn.delete(start_time_key(keyword))
    redis_conn.delete(active_key(keyword))

def mark_visited(keyword, url):
    return redis_conn.sadd(visited_key(keyword), url) == 1

def build_ui_links(urls):
    return "<br>".join(f"<a href='{u}'>{u}</a>" for u in urls)

def get_elapsed_time(keyword):
    start_time = float(redis_conn.get(f"keyword:{keyword}:start_time") or time.time())
    return time.time() - start_time

# ---- Crawl worker ----
def crawl_worker(keyword):
    db = DB()
    try:
        while is_active(keyword):
            # Atomically claim a batch from the frontier
            batch = []
            for _ in range(BATCH_SIZE):
                item = redis_conn.lpop(frontier_key(keyword))
                if not item:
                    break
                url, depth = deserialize(item)
                if mark_visited(keyword, url):
                    batch.append((url, depth))

            if not batch:
                # Frontier might still get new URLs from other workers or child links
                frontier_size = redis_conn.llen(frontier_key(keyword))
                if frontier_size == 0 and is_active(keyword):
                    # Only write "No matches" if no success has been recorded yet
                    existing_result = db.find_keyword(keyword)  # implement in DB
                    if not existing_result:
                        db.update_keyword_with_result(
                            keyword, f"No matches found in {get_elapsed_time(keyword):.2f}s"
                        )
                        stop_keyword(keyword)
                        log.info(f"[{keyword}] Frontier empty, stopping crawl with no matches.")
                # Wait for other workers / next batch
                time.sleep(0.1)
                continue

            urls, depths = zip(*batch)
            log.info(f"[{keyword}] Processing batch of {len(batch)} URLs")

            try:
                results = ls.search_for_keyword(keyword, urls)
                if isinstance(results, dict):
                    results = [results]  # single URL → make list

                for i, res in enumerate(results):
                    url = urls[i]
                    depth = depths[i]
                    log.info(f"[{keyword}] Crawling {url} (depth={depth}) elapsed {get_elapsed_time(keyword):.2f}s")

                    if depth >= DEPTH_LIMIT:
                        log.info(f"[{keyword}] Depth limit reached at {url}")
                        continue

                    # Success → update DB, stop all workers
                    if res.get("status") == "success":
                        child_links = res.get("result") or []
                        db_result = f"""
                        {len(child_links)} matches at {url} in {depth} clicks.<br>
                        It took {get_elapsed_time(keyword):.2f}s total.<br>
                        {build_ui_links(child_links)}
                        """
                        db.update_keyword_with_result(keyword, db_result)
                        stop_keyword(keyword)
                        log.info(f"[{keyword}] Keyword found at {url}, stopping crawl.")
                        break  # stop processing remaining URLs in this batch

                    # Push child URLs to frontier (BFS)
                    child_links = res.get("result") or []
                    if child_links:
                        serialized_links = [serialize(link, depth + 1) for link in child_links]
                        redis_conn.rpush(frontier_key(keyword), *serialized_links)
                        log.info(f"[{keyword}] Enqueued {len(child_links)} child URLs from {url}")

                # Frontier size after batch
                frontier_size = redis_conn.llen(frontier_key(keyword))
                log.info(f"[{keyword}] Frontier size after batch: {frontier_size}")

            except Exception as e:
                log.warning(f"[{keyword}] Error processing batch: {e}")

    finally:
        db.client.close()

# ---- Keyword job ----
def keyword_job(keyword):
    log.info(f"[{keyword}] Keyword job started")

    start_time = time.time()
    redis_conn.set(start_time_key(keyword), start_time)

    # Initialize keyword state
    redis_conn.set(active_key(keyword), "1")
    redis_conn.delete(frontier_key(keyword))
    redis_conn.delete(visited_key(keyword))

    # Seed frontier with the start URL
    redis_conn.rpush(frontier_key(keyword), serialize(START_URL, 0))
    log.info(f"[{keyword}] Frontier seeded with {START_URL}")

    # Enqueue crawl workers (non-blocking)
    for i in range(CRAWL_WORKERS):
        crawl_q.enqueue(crawl_worker, keyword)
        log.info(f"[{keyword}] Enqueued crawl worker {i+1}/{CRAWL_WORKERS}")

    log.info(f"[{keyword}] All crawl workers enqueued for keyword.")


# ---- Public API ----
def start_crawl(keyword):
    keyword_q.enqueue(keyword_job, keyword)
    log.info(f"[{keyword}] Keyword job enqueued in keyword queue")

