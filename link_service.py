from headers import link_tree_header
import re
import asyncio
from asynciolimiter import Limiter
from aiohttp import ClientTimeout
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

# todo
# save context of each page visited
# save tree structure
# optimize to catch more links (subpages)
# refactor request handling
# refactor logging
# refactor time printing
# refactor error handling
# create flask packaging structure
# optimize request efficiency and url access
# implement redis server job queue
# add db for batch jobs
# separate request errors instances

HTTP_LINK_PATTERN = re.compile("^http")
SUBPAGE_LINK_PATTERN = re.compile("^/.*")
RATE_LIMIT_PER_SECOND = 20
REQUEST_MAX_BURST = 10
REQUEST_TIMEOUT_IN_SECONDS = 3

limiter = Limiter(RATE_LIMIT_PER_SECOND, max_burst=REQUEST_MAX_BURST)
timeout = ClientTimeout(total=None, sock_connect=REQUEST_TIMEOUT_IN_SECONDS, sock_read=REQUEST_TIMEOUT_IN_SECONDS)

async def fetch_html(session, url):
    try:
        await limiter.wait()
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                return False

    except aiohttp.client_exceptions.ClientError:
        return False
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False


def get_soup(html_content):
    if not html_content:
        return None
    only_links_with_http_href = SoupStrainer("a", href=HTTP_LINK_PATTERN)
    soup = BeautifulSoup(html_content, 'lxml', parse_only=only_links_with_http_href)

    return soup

def get_target_links(soup, target_string):
    target_link_regex = f".*{target_string}"
    targets = soup.find_all("a", href=re.compile(target_link_regex, re.IGNORECASE))
    target_urls = set()
    for link in targets:
        if link['href']:
            target_urls.add(link['href'])
        
    if len(target_urls) > 0:
        return list(target_urls)
    return False

def get_all_child_links(soup):
    child_urls = set()
    for link in soup.find_all('a'):
        child_urls.add(link.get('href'))

    return list(child_urls)

async def get_html_from_all_links(urls):
    results = ""
    completed_count = 0
    html_content = ""
    async with aiohttp.ClientSession(headers=link_tree_header, timeout=timeout) as session:
        tasks = [fetch_html(session, url) for url in urls]

        for future in asyncio.as_completed(tasks):
            result = await future
            completed_count += 1
            if result:
                results += result
        html_content = results
        return html_content

async def link_search(target_string, urls):
    html_content = await get_html_from_all_links(urls)
    soup = get_soup(html_content)
    del html_content
    if not soup:
        return {"status": "failure", "result": "Hit a dead end: no valid soup found."}
    
    target_urls = get_target_links(soup, target_string)
    if target_urls:
        return {
            "status": "success",
            "result": target_urls
        }
    
    child_urls = get_all_child_links(soup)
    del soup
    return {
        "status": "continue",
        "result": child_urls
    }
    
async def perform_search(keyword, urls):
    return await link_search(target_string=keyword, urls=urls)

def search_for_keyword(keyword, urls):
    return asyncio.run(perform_search(keyword, urls))
