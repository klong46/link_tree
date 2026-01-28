from pymongo import MongoClient
import os

DB_NAME = "link_tree"
COLLECTION_NAME = "keywords"
SERVER_SELECTION_TIMEOUT = 5000

class DB:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI is not set")

        self.client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT
        )
        self.collection = self.client[COLLECTION_NAME][DB_NAME]

    def find_keyword(self, keyword):
        try:
            query = { "value": keyword }
            print(query)
            result = self.collection.find_one(query)
            print(result)

            return result

        except Exception as e:
            raise Exception("Unable to find the keyword due to the following error: ", e)
        
    def create_keyword(self, keyword):
        try:
            new_keyword = {"value": keyword, "status": "running", "result": None}
            self.collection.insert_one(new_keyword)
        except Exception as e:
            raise Exception("Unable to create the keyword due to the following error: ", e)
        
    def update_keyword_with_result(self, keyword, result):
        try:
            query = {"value": keyword}
            new_result = {"$set": {"status": "complete", "result": result}}
            self.collection.update_one(query, new_result)
        except Exception as e:
            raise Exception("Unable to update the keyword due to the following error: ", e)

