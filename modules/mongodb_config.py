import pymongo

client = pymongo.MongoClient("localhost", 27017)
db = client.twitter_db
collection = db.tweets
friends_collection = db.friends

#db_name = "twitter_db"
#collection_name = "tweets"
#mongodb_port = 27017

#db = client[db_name]
#total_records = db[collection_name].estimated_document_count()
