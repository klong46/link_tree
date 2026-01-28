import db_config as config
from pymongo import MongoClient
import os

class DB:
    def __init__(self):
        try:
            client = MongoClient(f"mongodb://{os.environ.get('MONGO_HOST', 'mongo')}:{config.PORT}/")
            database = client.get_database(config.DB_NAME)
            self.collection = database.get_collection(config.COLLECTION_NAME)
        except Exception as e:
            raise Exception("Unable to connect to DB: ", e)

    def find_keyword(self, keyword):
        try:
            query = { "value": keyword }
            result = self.collection.find_one(query)

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

