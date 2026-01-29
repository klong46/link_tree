import link_service as link_service
from markupsafe import escape
from db import DB

DEFAULT_CLICK_LIMIT = 100

def search_for_keyword(keyword):
    db = DB()
    try:
        print("Created job.")
        print(f"Starting a keyword search for {keyword}")
        target_string = f"{escape(keyword)}"
        result = link_service.get_shortest_path(target_string, DEFAULT_CLICK_LIMIT)
        print("Keyword search finished.")

        print("Updating DB with result.")
        db.update_keyword_with_result(keyword, result)
        print("DB update complete.")
    finally:
        db.client.close()