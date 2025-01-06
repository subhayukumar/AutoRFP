from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Self, Union


KEY_FIELD = "__key__"
TIMESTAMP_FIELD = "timestamp"


class AbstractDB(ABC):
    """
    Abstract class for database operations.

    All methods are abstract, meaning that they must be implemented by any subclass of this class.

    The main methodology is to provide a standard interface for all database operations, regardless of the
    underlying database technology. This allows for easy switching between different databases, such as
    MongoDB, JSONDB, or any other.

    All methods take the necessary parameters and return the result of the operation. The result is usually
    a boolean indicating whether the operation was successful or not.

    The class also provides a few helper methods, such as `_remove_key_field` and `_add_timestamp`, which
    can be used to remove the key field or add a timestamp to a list of dictionaries, respectively.
    """
    @abstractmethod
    def __init__(self, *args: Any, **kwds: Any) -> None:
        """
        Initialize the database instance.

        This method must be overridden by the subclasses to initialize
        the database instance.

        Parameters:
            *args: Any
                The arguments to be passed to the database instance.
            **kwds: Any
                The keyword arguments to be passed to the database instance.

        Returns:
            None
        """
        pass
    
    @abstractmethod
    def __call__(self, *args: Any, **kwds: Any) -> Self:
        """
        Initialize the database instance with the given arguments.

        This method must be overridden by the subclasses to initialize
        the database instance with the given arguments.

        Parameters:
            *args: Any
                The arguments to be passed to the database instance.
            **kwds: Any
                The keyword arguments to be passed to the database instance.

        Returns:
            Self
        """
        pass
    
    @staticmethod
    def _remove_key_field(objs: list[Dict[str, Any]]):
        """
        Remove the key field from the list of dictionaries.

        Parameters:
            objs: list[Dict[str, Any]]
                The list of dictionaries to remove the key field from.

        Returns:
            list[Dict[str, Any]]
        """
        [obj.pop(KEY_FIELD, None) for obj in objs if isinstance(obj, dict)]
        return objs
    
    @staticmethod
    def _add_timestamp(objs: list[Dict[str, Any]]):
        """
        Add the timestamp field to the list of dictionaries.

        Parameters:
            objs: list[Dict[str, Any]]
                The list of dictionaries to add the timestamp field to.

        Returns:
            list[Dict[str, Any]]
        """
        ts = datetime.now(timezone.utc).isoformat()
        for obj in objs:
            obj[TIMESTAMP_FIELD] = ts
        return objs
    
    @abstractmethod
    def _get(self, key: str) -> Dict[str, Any]:
        """
        Get a document from the database.

        This method must be overridden by the subclasses to retrieve a document.

        Parameters:
            key: str
                The key of the document to retrieve.

        Returns:
            Dict[str, Any]
        """
        pass

    def get(self, key: str) -> Union[Dict[str, Any]]:
        """
        Get a document from the database and remove the key field.

        Parameters:
            key: str
                The key of the document to retrieve.

        Returns:
            Dict[str, Any]
        """
        res = self._get(key)
        return self._remove_key_field([res])[0]
    
    @abstractmethod
    def _get_many(self, key: str) -> List[Dict[str, Any]]:
        """
        Get multiple documents from the database.

        This method must be overridden by the subclasses to retrieve multiple documents.

        Parameters:
            key: str
                The key of the documents to retrieve.

        Returns:
            List[Dict[str, Any]]
        """
        pass

    def get_many(self, key: str) -> List[Dict[str, Any]]:
        """
        Get multiple documents from the database and remove the key field.

        Parameters:
            key: str
                The key of the documents to retrieve.

        Returns:
            List[Dict[str, Any]]
        """
        res = self._get_many(key)
        return self._remove_key_field(res)
    
    @abstractmethod
    def _get_all(self) -> List[Dict[str, Any]]:
        """
        Get all documents from the database.

        This method must be overridden by the subclasses to retrieve all documents.

        Returns:
            List[Dict[str, Any]]
        """
        pass

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all documents from the database and remove the key field.

        Returns:
            List[Dict[str, Any]]
        """
        res = self._get_all()
        return self._remove_key_field(res)
    
    @abstractmethod
    def _query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query the database with the given query.

        This method must be overridden by the subclasses to perform a query.

        Parameters:
            query: Dict[str, Any]
                The query to be executed.

        Returns:
            List[Dict[str, Any]]
        """
        pass

    def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query the database with the given query and remove the key field.

        Parameters:
            query: Dict[str, Any]
                The query to be executed.

        Returns:
            List[Dict[str, Any]]
        """
        res = self._query(query)
        return self._remove_key_field(res)

    @abstractmethod
    def _insert(self, value: Dict[str, Any], key: str) -> bool:
        """
        Insert a document into the database.

        This method must be overridden by the subclasses to insert a document.

        Parameters:
            value: Dict[str, Any]
                The document to be inserted.
            key: str
                The key of the document to be inserted.

        Returns:
            bool
        """
        pass

    def insert(self, value: Dict[str, Any], key: str) -> bool:
        """
        Insert a document into the database with the given key.

        Parameters:
            value: Dict[str, Any]
                The document to be inserted.
            key: str
                The key of the document to be inserted.

        Returns:
            bool
        """
        value[KEY_FIELD] = key
        value = self._add_timestamp([value])[0]
        return self._insert(value, key)

    @abstractmethod
    def _insert_many(self, values: List[Dict[str, Any]], keys: List[str]) -> bool:
        """
        Insert multiple documents into the database.

        This method must be overridden by the subclasses to insert multiple documents.

        Parameters:
            values: List[Dict[str, Any]]
                The documents to be inserted.
            keys: List[str]
                The keys of the documents to be inserted.

        Returns:
            bool
        """
        pass

    def insert_many(self, values: List[Dict[str, Any]], keys: List[str]) -> bool:
        """
        Insert multiple documents into the database with the given keys.

        Parameters:
            values: List[Dict[str, Any]]
                The documents to be inserted.
            keys: List[str]
                The keys of the documents to be inserted.

        Returns:
            bool
        """
        for key, value in zip(keys, values):
            value[KEY_FIELD] = key
        values = self._add_timestamp(values)
        return self._insert_many(values, keys)

    @abstractmethod
    def _update(self, value: Dict[str, Any], key: str) -> bool:
        """
        Update a document in the database.

        This method must be overridden by the subclasses to update a document.

        Parameters:
            value: Dict[str, Any]
                The document to be updated.
            key: str
                The key of the document to be updated.

        Returns:
            bool
        """
        pass

    def update(self, value: Dict[str, Any], key: str) -> bool:
        """
        Update a document in the database with the given key.

        Parameters:
            value: Dict[str, Any]
                The document to be updated.
            key: str
                The key of the document to be updated.

        Returns:
            bool
        """
        value = self._add_timestamp([value])[0]
        return self._update(value, key)

    @abstractmethod
    def _upsert(self, value: Dict[str, Any], key: str) -> bool:
        """
        Upsert a document in the database.

        This method must be overridden by the subclasses to upsert a document.

        Parameters:
            value: Dict[str, Any]
                The document to be upserted.
            key: str
                The key of the document to be upserted.

        Returns:
            bool
        """
        pass

    def upsert(self, value: Dict[str, Any], key: str) -> bool:
        """
        Upsert a document in the database with the given key.

        Parameters:
            value: Dict[str, Any]
                The document to be upserted.
            key: str
                The key of the document to be upserted.

        Returns:
            bool
        """
        value = self._add_timestamp([value])[0]
        value[KEY_FIELD] = key
        return self._upsert(value, key)

    @abstractmethod
    def _delete(self, key: str) -> bool:
        """
        Delete a document from the database.

        This method must be overridden by the subclasses to delete a document.

        Parameters:
            key: str
                The key of the document to be deleted.

        Returns:
            bool
        """
        pass

    def delete(self, key: str) -> bool:
        """
        Delete a document from the database.

        Parameters:
            key: str
                The key of the document to be deleted.

        Returns:
            bool
        """
        return self._delete(key)

    @abstractmethod
    def _delete_many(self, keys: List[str]) -> List[bool]:
        """
        Delete multiple documents from the database.

        This method must be overridden by the subclasses to delete multiple documents.

        Parameters:
            keys: List[str]
                The keys of the documents to be deleted.

        Returns:
            List[bool]
        """
        pass

    def delete_many(self, keys: List[str]) -> List[bool]:
        """
        Delete multiple documents from the database.

        Parameters:
            keys: List[str]
                The keys of the documents to be deleted.

        Returns:
            List[bool]
        """
        return self._delete_many(keys)
