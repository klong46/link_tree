from headers import link_tree_header
import re
import asyncio
from asynciolimiter import Limiter
from aiohttp import ClientTimeout
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import time
from progress_bar import ProgressBar
from request_errors import RequestErrors

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
request_errors = RequestErrors()

def clear_lines(num_lines):
    for i in range(num_lines):
        print("\033[1A\033[2K", end="")

async def fetch_html(session, url):
    try:
        await limiter.wait()
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                request_errors.add_error(f"{response.status} :: {url}")
                return False

    except aiohttp.client_exceptions.ClientError as error:
        request_errors.add_error(error)
        return False
    except asyncio.TimeoutError as error:
        request_errors.add_error(error)
        return False
    except Exception as error:
        request_errors.add_error(error)
        return False


def get_soup(html_content):
    if not html_content:
        return None
    start_time = time.time()
    only_links_with_http_href = SoupStrainer("a", href=HTTP_LINK_PATTERN)
    soup = BeautifulSoup(html_content, 'lxml', parse_only=only_links_with_http_href)

    end_time = time.time()
    elapsed_time = end_time-start_time
    # print(f"TIME TO GET SOUP: {elapsed_time:.2f} seconds")
    return soup

def get_target_links(soup, target_string):
    start_time = time.time()
    target_link_regex = f".*{target_string}"
    targets = soup.find_all("a", href=re.compile(target_link_regex, re.IGNORECASE))
    # print(f"TARGETS RETRIEVED: {len(targets)}")

    end_time = time.time()
    elapsed_time = end_time-start_time
    # print(f"TIME TO GET TARGET LINK: {elapsed_time:.2f} seconds")
    target_urls = set()
    for link in targets:
        if link['href']:
            target_urls.add(link['href'])
        
    if len(target_urls) > 0:
        return list(target_urls)
    return False

def get_all_child_links(soup):
    start_time = time.time()
    child_urls = set()
    for link in soup.find_all('a'):
        child_urls.add(link.get('href'))

    end_time = time.time()
    elapsed_time = end_time-start_time
    # print(f"TIME TO GET CHILD LINKS: {elapsed_time:.2f} seconds")
    return list(child_urls)

async def get_html_from_link(url):
    html_content = ""
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(headers=link_tree_header, timeout=timeout) as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                else:
                    print(f"Warning: {url} returned status {response.status}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    return html_content



async def link_search(target_string, url, num_clicks=0):
    # print(f"COUNT IS {num_clicks}, TARGET IS {target_string}")
    html_content = await get_html_from_link(url)

    # print(f"CONTENT LENGTH: {len(html_content)}")
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
    # print(f"NUMBER OF CHILD LINKS: {len(child_urls)}")
    return {
        "status": "continue",
        "result": child_urls
    }
    
async def perform_search(keyword, url):
    return await link_search(target_string=keyword, url=url)

def search_for_keyword(keyword, url):
    return asyncio.run(perform_search(keyword, url))
