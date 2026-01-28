import services.keyword as keyword_service


def enqueue_keyword_search(queue, keyword):
    result = queue.enqueue(keyword_service.search_for_keyword, keyword)
    return result