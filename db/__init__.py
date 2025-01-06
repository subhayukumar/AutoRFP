"""
This module initializes the database interface for the application, providing a seamless
integration with different types of database backends. It currently supports MongoDB as
the primary database system, with JSON-based storage available as an alternative.

Main Methodology:
- The module is designed to abstract database operations, allowing the application to
  interact with different database systems using a unified interface.
- By default, it initializes a `MongoDB` instance, which is a powerful NoSQL database
  system, ideal for handling large volumes of data with high availability and scalability.
- The design enables easy switching or extension to other database systems by modifying
  or adding to the imports and instantiation logic.

Important Notes:
- MongoDB is set as the default database backend through the `getDB` object. This provides
  a preconfigured MongoDB instance ready for use throughout the application.
- The use of an abstract database class ensures that all database operations adhere to a
  predefined structure, promoting consistency and reducing the risk of errors.
- Developers can extend the database capabilities by importing additional database classes
  and modifying the initialization logic within this module.
- The module's flexibility allows for future enhancements, such as the integration of
  additional database systems or advanced configurations, without requiring significant
  changes to the application codebase.

Usage:
- Import the `getDB` object from this module to access the default database instance.
- For specific database operations or configurations, refer to the documentation of the
  respective database classes in `jsondb.py` and `mongodb.py`.

This module plays a crucial role in the application architecture, ensuring that database
interactions are efficient, reliable, and adaptable to varying requirements.
"""
from db.mongodb import MongoDB

getDB = MongoDB()
"""
Returns a AbstractDB instance for the given collection name

Args:
    collection (str): The name of the collection to get the DB for
    
Returns:
    AbstractDB: The AbstractDB instance
"""


__all__ = ["getDB"]
