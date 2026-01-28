import services.link as link_service
from markupsafe import escape
from db import DB

db = DB()

DEFAULT_CLICK_LIMIT = 5

def search_for_keyword(keyword):
    print("Creating running job.")
    db.create_keyword(keyword)
    target_string = f"{escape(keyword)}"
    print(f"Starting a keyword search for {keyword}")
    result = link_service.get_shortest_path(target_string, DEFAULT_CLICK_LIMIT)
    print("Keyword search finished, updating DB with result.")
    db.update_keyword_with_result(keyword, result)
    db.client.close()
    print("DB update complete.")