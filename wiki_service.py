import headers
from link_node import LinkNode
import re
import asyncio
from asynciolimiter import Limiter
from aiohttp import ClientTimeout
import aiohttp
from bs4 import BeautifulSoup
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

start_url = "https://en.wikipedia.org/wiki/Main_Page" # make dynamic in POST body
http_link_regex = "^http"
subpage_link_regex = "^/.*"
link_check_limit = 4
RATE_LIMIT_PER_SECOND = 20
REQUEST_MAX_BURST = 10
REQUEST_TIMEOUT_IN_SECONDS = 10

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


def build_ui_links(urls):
    ui_links = []
    for url in urls:
        ui_links.append(f"<a href='{url}'>{url}<a>")
    
    return "<br>".join(ui_links)

def get_soup(html_content):
    start_time = time.time()
    soup = BeautifulSoup(html_content, 'lxml')

    end_time = time.time()
    elapsed_time = end_time-start_time
    print(f"TIME TO GET SOUP: {elapsed_time:.2f} seconds")
    return soup

def get_target_links(soup, target_string):
    start_time = time.time()
    target_link_regex = f"{http_link_regex}.*{target_string}"
    targets = soup.find_all("a", href=re.compile(target_link_regex, re.IGNORECASE))
    print(f"TARGETS RETRIEVED: {len(targets)}")

    end_time = time.time()
    elapsed_time = end_time-start_time
    print(f"TIME TO GET TARGET LINK: {elapsed_time:.2f} seconds")
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
    http_links = soup.find_all("a", href=re.compile(http_link_regex))
    subpage_links = soup.find_all("a", href=re.compile(subpage_link_regex))
    for link in http_links:
        if link['href']:
            child_urls.add(link['href'])

    end_time = time.time()
    elapsed_time = end_time-start_time
    print(f"TIME TO GET CHILD LINKS: {elapsed_time:.2f} seconds")
    return list(child_urls)

async def get_html_from_all_links(urls):
    start_time = time.time()
    results = ""
    completed_count = 0
    html_content = ""
    async with aiohttp.ClientSession(headers=headers.user_agent, timeout=timeout) as session:
        print("\n")
        tasks = [fetch_html(session, url) for url in urls]

        progress_bar = ProgressBar(len(urls), RATE_LIMIT_PER_SECOND)
        for future in asyncio.as_completed(tasks):
            result = await future
            completed_count += 1
            request_errors.print_num()
            progress_bar.print(completed_count)
            clear_lines(4)
            if result:
                results += result
        html_content = results
        end_time = time.time()
        elapsed_time = end_time-start_time
        print(f"TIME TO GET ALL HTML: {elapsed_time:.2f} seconds")
        # return results
        return html_content

async def recursive_link_search(target_string, urls, num_clicks=0, link_tree=None):
    print(f"COUNT IS {num_clicks}, TARGET IS {target_string}")
    num_clicks += 1
    html_content = await get_html_from_all_links(urls)

    if html_content:
        print(f"CONTENT LENGTH: {len(html_content)}")
        soup = get_soup(html_content)
        if not soup:
            return "Hit a dead end: no valid soup found."
        
        target_urls = get_target_links(soup, target_string)
        if target_urls:
            return f"{len(target_urls)} targets found in {num_clicks} clicks: <br> {build_ui_links(target_urls)}"

        if num_clicks >= link_check_limit:
            return f"Link check limit of {link_check_limit} reached. Checked these links: {[]}"
        
        child_urls = get_all_child_links(soup)
        for child in child_urls:
            if link_tree:
                link_tree.add_child(child)
        print(f"NUMBER OF CHILD LINKS: {len(child_urls)}")
        return await recursive_link_search(target_string=target_string, urls=child_urls, num_clicks=num_clicks)
    else:
        return "No content returned."

async def do_search(target_string):
    return await recursive_link_search(target_string=target_string, urls=[start_url], link_tree=LinkNode(start_url))

def get_shortest_path(target_string):
    return asyncio.run(do_search(target_string))