import os
import uuid
import link_service as ls
from db import DB
from redis import Redis
from rq import Queue

# ---- Config ----
JOB_QUEUE_TIMEOUT = 300  # 5 minutes
DEPTH_LIMIT = 5
START_URL = "https://en.wikipedia.org/wiki/Main_Page"

# Redis connection
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Single queue for all jobs
q = Queue("default", connection=redis_conn, default_timeout=JOB_QUEUE_TIMEOUT)

# ---- Helper functions ----

def build_ui_links(urls):
    ui_links = []
    for url in urls:
        ui_links.append(f"<a href='{url}'>{url}<a>")
    
    return "<br>".join(ui_links)

def generate_user_id():
    """Generate a unique ID for each user/session."""
    return str(uuid.uuid4())

def stop_key(user_id, keyword):
    """Stop flag per user+keyword."""
    return f"crawl:stop:{user_id}:{keyword}"

def visited_key(user_id, keyword):
    """Visited URLs per user+keyword."""
    return f"visited:{user_id}:{keyword}"

def should_stop(user_id, keyword):
    """Check if this crawl should stop."""
    return redis_conn.get(stop_key(user_id, keyword)) is not None

def mark_visited(user_id, keyword, url):
    """Mark URL as visited for this crawl. Returns True if first visit."""
    return redis_conn.sadd(visited_key(user_id, keyword), url) == 1

def clear_crawl_flags(user_id, keyword):
    """Clear stop flag and visited set for a new crawl."""
    redis_conn.delete(stop_key(user_id, keyword))
    redis_conn.delete(visited_key(user_id, keyword))

# ---- Crawl functions ----

def enqueue_crawl(user_id, keyword, url=START_URL, depth=0):
    """Enqueue a crawl job in the single queue."""
    job = q.enqueue(crawl_url, user_id, keyword, url, depth)
    job.meta['user_id'] = user_id
    job.meta['keyword'] = keyword
    job.save()

def crawl_url(user_id, keyword, url, depth=0):
    """
    Crawl a URL recursively. Stops if stop flag is set or depth limit reached.
    """
    print(f"[{user_id}:{keyword}] Crawling {url} at depth {depth}")

    # --- Check stop flag immediately ---
    if should_stop(user_id, keyword):
        print(f"[{user_id}:{keyword}] Stop flag detected. Skipping {url}.")
        return

    # --- Check depth ---
    if depth >= DEPTH_LIMIT:
        print(f"[{user_id}:{keyword}] Depth limit reached at {url}.")
        return

    # --- Avoid revisiting URLs ---
    if not mark_visited(user_id, keyword, url):
        print(f"[{user_id}:{keyword}] Already visited {url}. Skipping.")
        return

    db = None
    try:
        # --- Perform the keyword search ---
        keyword_search_result = ls.search_for_keyword(keyword, url)
        print(f"[{user_id}:{keyword}] Search complete for {url}")

        # --- Update DB if success ---
        db = DB()
        if keyword_search_result.get("status") == "success":
            target_link_list = keyword_search_result.get("result") or []
            target_link_html = build_ui_links(target_link_list)
            db_result = f"{len(target_link_list)} targets found in {depth} clicks: <br> {target_link_html}"
            db.update_keyword_with_result(keyword, db_result)
            print(f"[{user_id}:{keyword}] DB updated for {url}")

            # --- Stop this crawl ---
            redis_conn.set(stop_key(user_id, keyword), 1)
            print(f"[{user_id}:{keyword}] Target found! Stop signal set.")

            # --- Clear any pending queued jobs for this user+keyword ---
            for job in q.jobs:
                job_user = job.meta.get("user_id")
                job_keyword = job.meta.get("keyword")
                if job_user == user_id and job_keyword == keyword:
                    job.delete()
            print(f"[{user_id}:{keyword}] Pending jobs cleared.")
            return

        # --- Stop if the job does not continue ---
        if keyword_search_result.get("status") != "continue":
            return

        # --- Enqueue child links, stop if stop flag is set ---
        links = keyword_search_result.get("result") or []
        for link in links:
            if should_stop(user_id, keyword):
                print(f"[{user_id}:{keyword}] Stop detected, not enqueuing further links.")
                break
            enqueue_crawl(user_id, keyword, link, depth + 1)

    except Exception as e:
        print(f"[{user_id}:{keyword}] Error crawling {url}: {e}")

    finally:
        if db:
            db.client.close()


# ---- Public API ----

def start_crawl(user_id, keyword):
    print("Start a crawl for a user with a specific keyword.")
    clear_crawl_flags(user_id, keyword)
    enqueue_crawl(user_id, keyword)
    print(f"[{user_id}:{keyword}] Crawl started for keyword '{keyword}'")
    return f"{user_id}:{keyword}"  # crawl ID for tracking
