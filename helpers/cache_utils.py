import logging
from typing import Any, Dict, Union
from datetime import datetime, timedelta, timezone

from db import getDB
from helpers.time_utils import format_time_delta


def load(key: str, collection: str, get_expired: bool = False) -> Union[Dict[str, Any], None]:
    """
    Load data from cache by key.

    Args:
        key (str): The key to load from cache.
        collection (str): The name of the collection to load from.
        get_expired (bool, optional): Whether to get expired objects. Defaults to False.

    Returns:
        The loaded data or None if not found in cache.
    """
    data = getDB(collection).get(key=key)
    d = data.get("data")
    if not isinstance(d, dict):
        return
    
    if get_expired or data.get("expires_at") is None:
        return d
    
    expires_at = datetime.fromisoformat(data.get("expires_at", "1970-01-01T00:00:00+00:00"))
    current_ts = datetime.now(timezone.utc)

    left_to_expire = expires_at - current_ts
    if left_to_expire.total_seconds() < 0:
        logging.warning(f"Cache entry in {collection!r} EXPIRED for key {key!r}")
        return
    logging.info(
        f"Cache entry FOUND in {collection!r} for key {key!r}. Expires in {format_time_delta(left_to_expire)}"
    )
    return d

def save(key: str, collection: str, data: Dict[str, Any], expire_after_seconds: int | None = 3600 * 24 * 7):
    """
    Save data to cache by key.

    Args:
        key (str): The key to save to cache.
        expire_after_seconds (int, optional): The expiry time in seconds since cached time. Defaults to 3600 * 24 * 7 (1 week).
            If None, the object will never expire.
        collection (str, optional): The name of the collection to save to.
            Defaults to the name of the class.
    """
    if expire_after_seconds is None:
        expires_at = None
    else:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expire_after_seconds)).isoformat()
    
    value = {"data": data, "expires_at": expires_at}
    getDB(collection).upsert(key=key, value=value)
    logging.info(
        f"Cache entry SAVED in {collection!r} for key {key!r}. "
        + ("Never expires!" if expire_after_seconds is None else f"Expires in {format_time_delta(timedelta(seconds=expire_after_seconds))}")
    )

def delete(key: str, collection: str):
    """
    Delete data from cache by key.

    Args:
        key (str): The key to delete from cache.
        collection (str, optional): The name of the collection to delete from.
            Defaults to the name of the class.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    _bool = getDB(collection).delete(key=key)
    if _bool:
        logging.info(f"Cache entry DELETED in {collection!r} for key {key!r}")
    else:
        logging.warning(f"Cache entry NOT FOUND in {collection!r} for key {key!r}. Could NOT DELETE.")
    return _bool

def query(query: dict, collection: str):
    """
    Query the cache for the given query dict and return a list data.

    Args:
        query (dict): The query dict to search the cache with.
        collection (str, optional): The name of the collection to query.
            Defaults to the name of the class.

    Returns:
        List[Dict[str, Any]]: A list of data that match the query.
    """
    query = {
        (f"data.{k}" if isinstance(k, str) else k): v 
        for k, v in query.items()
    }
    documents = getDB(collection).query(query=query)
    if documents:
        logging.info(f"Cache query returned {len(documents)} results for query {query} in {collection!r}.")
    else:
        logging.warning(f"Cache query returned no results for query {query} in {collection!r}.")
    return [x["data"] for x in documents]
