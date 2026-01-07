"""MongoDB storage helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from pymongo import MongoClient
from pymongo.collection import Collection


@dataclass
class MongoConfig:
    """Configuration for connecting to MongoDB.

    Attributes:
        uri: MongoDB connection string.
        db_name: Name of the database to use.
    """

    uri: str
    db_name: str


class MongoStorage:
    """Simple MongoDB storage wrapper."""

    def __init__(
        self, config: MongoConfig, client: Optional[MongoClient] = None
    ) -> None:
        """Initialize the storage with configuration.

        Args:
            config: Connection information.
            client: Optional pre-initialized ``MongoClient`` for testing.
        """

        self._client = client or MongoClient(config.uri)
        self._db = self._client[config.db_name]

    def get_collection(self, name: str) -> Collection:
        """Return a collection handle by name.

        Args:
            name: Target collection.

        Returns:
            Collection instance.
        """

        return self._db[name]

    def list_collections(self) -> list[str]:
        """Return all collection names in the database."""

        return list(self._db.list_collection_names())

    def create_collection(self, name: str) -> None:
        """Create a new collection."""

        self._db.create_collection(name)

    def drop_collection(self, name: str) -> None:
        """Drop a collection by name."""

        self.get_collection(name).drop()

    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a single document.

        Args:
            collection: Target collection.
            document: Document to insert.

        Returns:
            Stringified inserted document ID.
        """

        result = self.get_collection(collection).insert_one(document)
        return str(result.inserted_id)

    def find_one(
        self, collection: str, query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query.

        Args:
            collection: Target collection.
            query: MongoDB filter query.

        Returns:
            The first matching document or ``None``.
        """

        return self.get_collection(collection).find_one(query)

    def find(self, collection: str, query: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """Yield documents matching the query."""

        return self.get_collection(collection).find(query)

    def update_one(
        self, collection: str, query: Dict[str, Any], update: Dict[str, Any]
    ) -> int:
        """Update a single document.

        Args:
            collection: Target collection.
            query: Filter selecting the document to update.
            update: Update operations.

        Returns:
            Number of modified documents.
        """

        result = self.get_collection(collection).update_one(query, update)
        return result.modified_count

    def delete_one(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete a single document.

        Args:
            collection: Target collection.
            query: Filter selecting the document to delete.

        Returns:
            Number of documents deleted.
        """

        result = self.get_collection(collection).delete_one(query)
        return result.deleted_count

    def delete_many(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete many documents matching the query."""

        result = self.get_collection(collection).delete_many(query)
        return result.deleted_count
