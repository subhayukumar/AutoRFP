from datetime import datetime
from typing import List, Dict, Any

from pymongo.server_api import ServerApi
from pymongo.mongo_client import MongoClient

from db.abstractdb import AbstractDB
from config import MONGO_CLUSTER_URI, MONGO_DATABASE

TIMESTAMP_KEY = "timestamp"
KEY_FIELD = "__key__"
INBUILD_ID_FIELD = "_id"


class MongoDB(AbstractDB):
    """
    MongoDB is an implementation of AbstractDB tailored for MongoDB interactions.

    This class provides methods for basic CRUD operations and querying MongoDB collections.
    It leverages pymongo for database interactions and ensures that each document includes
    a key and timestamp for tracking purposes.

    Main Methodology:
    - Utilizes a MongoClient to connect to the MongoDB cluster specified by the URI.
    - Each collection is accessed via the __call__ method, which sets the active collection.
    - CRUD operations are implemented with MongoDB's native methods, ensuring efficient data handling.
    - The class supports querying with custom filters, projections, sorting, and limiting the number of results.

    Important Notes:
    - Includes exception handling for database operations to ensure robustness.
    - The INBUILD_ID_FIELD is excluded from all projections by default for data consistency.
    - Supports upserting, which inserts a document if it doesn't exist or updates it if it does.
    - Provides logging for database operation failures, aiding in debugging and monitoring.
    """

    def __init__(self, uri: str = MONGO_CLUSTER_URI, database: str = MONGO_DATABASE) -> None:
        """
        Initialize the MongoDB instance with a URI and database name.

        Parameters:
            uri (str): The MongoDB cluster URI to connect to. Defaults to MONGO_CLUSTER_URI.
            database (str): The name of the database to interact with. Defaults to MONGO_DATABASE.

        Returns:
            None

        Notes:
            - Utilizes the 1st generation of the MongoDB Server API for improved performance.
            - Sets the heartbeat frequency to 30 seconds to ensure efficient connection maintenance.
        """
        super().__init__()
        self.client = MongoClient(
            uri, 
            server_api=ServerApi('1'), 
            heartbeatFrequencyMS=30000, 
        )
        self.db = self.client.get_database(name=database)
        
    def __call__(self, collection: str):
        """
        Set the active MongoDB collection for subsequent operations.

        Parameters:
            collection (str): The name of the collection to interact with.

        Returns:
            Self: The MongoDB instance with the specified collection set.

        Notes:
            This method configures the MongoDB instance to point to the given collection,
            allowing for CRUD operations on that specific collection.
        """
        self.collection = self.db.get_collection(name=collection)
        return self
    
    def _get(self, key: str) -> Dict[str, Any]:
        return self.collection.find_one(filter={KEY_FIELD: key}, projection={INBUILD_ID_FIELD: False}) or {}

    def _get_many(self, key: str) -> List[Dict[str, Any]]:
        return list(self.collection.find(filter={KEY_FIELD: key}, projection={INBUILD_ID_FIELD: False}))

    def _get_all(self) -> List[Dict[str, Any]]:
        return list(self.collection.find(projection={INBUILD_ID_FIELD: False}))

    def _insert(self, value: Dict[str, Any], key: str) -> bool:
        try:
            self.collection.insert_one({KEY_FIELD: key, TIMESTAMP_KEY: datetime.now(), **value})
            return True
        except Exception as e:
            print(f"Insert failed: {e}")
            return False

    def _insert_many(self, values: List[Dict[str, Any]], keys: List[str]) -> bool:
        try:
            self.collection.insert_many(values)
            return True
        except Exception as e:
            print(f"Insert many failed: {e}")
            return False

    def _update(self, value: Dict[str, Any], key: str) -> bool:
        try:
            result = self.collection.update_one({KEY_FIELD: key}, {"$set": value})
            return result.modified_count > 0
        except Exception as e:
            print(f"Update failed: {e}")
            return False

    def _upsert(self, value: Dict[str, Any], key: str) -> bool:
        try:
            self.collection.update_one({KEY_FIELD: key}, {"$set": value}, upsert=True)
            return True
        except Exception as e:
            print(f"Upsert failed: {e}")
            return False

    def _delete(self, key: str) -> bool:
        try:
            result = self.collection.delete_one({KEY_FIELD: key})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Delete failed: {e}")
            return False

    def _delete_many(self, keys: List[str]) -> List[bool]:
        results = []
        for key in keys:
            results.append(self._delete(key))
        return results

    def _query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(self.collection.find(filter=query, projection={INBUILD_ID_FIELD: False}))
    
    def search(
        self, 
        custom_query: Dict[str, Any] = {}, 
        projection: Dict[str, Any] = {INBUILD_ID_FIELD: False}, 
        limit: int = 0, 
        sort: Dict[str, int] = {}, 
    ) -> List[Dict[str, Any]]:
        """
        Perform a search on the MongoDB collection with the given parameters.

        This method allows for flexible querying of the MongoDB collection by
        providing options for filtering, projecting specific fields, limiting
        the number of returned documents, and sorting the results.

        Parameters:
            custom_query: Dict[str, Any]
                A dictionary representing the MongoDB query filter. Defaults to
                an empty dictionary, which matches all documents.
            projection: Dict[str, Any]
                A dictionary specifying the fields to include or exclude in the
                returned documents. By default, the internal ID field is excluded.
            limit: int
                The maximum number of documents to return. A value of 0 means no
                limit.
            sort: Dict[str, int]
                A dictionary defining the sort order of the results. The keys are
                field names and the values are 1 for ascending or -1 for descending order.

        Returns:
            List[Dict[str, Any]]:
                A list of documents matching the query criteria, with the specified
                fields projected, up to the specified limit, and sorted as requested.

        Important Notes:
        - Ensure the collection is set before calling this method, as it operates
          on the active collection of the MongoDB instance.
        - Be cautious with large result sets; consider using a sensible limit to
          avoid performance issues.
        """
        return list(self.collection.find(
            filter=custom_query, projection=projection, limit=limit, sort=list(sort.items())
        ))

