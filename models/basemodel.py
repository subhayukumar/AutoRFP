"""
BaseModel: An abstract base class for all models in the app.

This module provides the `BaseModel` class, which serves as an abstract base class for all models in the app. It provides common functionality for all models, such as loading from JSON or YAML, saving to JSON or YAML, and equality comparison.

Methods:
    `from_json(data: str, fuzzy=False, cutoff: float = 0.0) -> BaseModel:`
        Creates a BaseModel object from a JSON string.

    `from_yaml(data: str, fuzzy=False, cutoff: float = 0.0) -> BaseModel:`
        Creates a BaseModel object from a YAML string.

    `to_json(include=None, exclude=None, by_alias=False, skip_defaults=False, exclude_unset=False, exclude_defaults=False, exclude_none=False, encoder=None, use_enum_values=False, encoder_options=None, json_dumps_params=None) -> str:`
        Saves the BaseModel object to a JSON string.

    `to_yaml(include=None, exclude=None, by_alias=False, exclude_unset=False, exclude_defaults=False, exclude_none=False, encoder=None, use_enum_values=False, encoder_options=None, yaml_dumps_params=None) -> str:`
        Saves the BaseModel object to a YAML string.

    `to_file(path: Union[str, Path], include=None, exclude=None, by_alias=False, skip_defaults=False, exclude_unset=False, exclude_defaults=False, exclude_none=False, round_trip=False, warnings=True, serialize_as_any=False) -> None:`
        Saves the BaseModel object to a file. (Can be `yaml` or `json`)
        
    `save_to_cache(key: str, collection: str = None)`
        Saves the BaseModel object to the cache.

    `load_from_cache(key: str, expiry_seconds: int = 3600 * 24, collection: str = None)`
        Loads the BaseModel object from the cache. Expires after 24 hours by default.
    
    `delete_from_cache(key: str, collection: str = None)`
        Deletes the BaseModel object from the cache.

    `__hash__(self) -> int:`
        Returns the hash of the BaseModel object.

    `__eq__(self, other: "BaseModel") -> bool:`
        Compares the BaseModel object for equality with another BaseModel object.

Usage Examples:
    # Creating a BaseModel object from JSON
    data = '{"name": "John", "age": 30}'
    person = BaseModel.from_json(data)

    # Creating a BaseModel object from YAML
    data = 'name: John\nage: 30'
    person = BaseModel.from_yaml(data)

    # Saving a BaseModel object to JSON
    person = BaseModel(name="John", age=30)
    json_data = person.to_json()

    # Saving a BaseModel object to YAML
    person = BaseModel(name="John", age=30)
    yaml_data = person.to_yaml()

    # Comparing two BaseModel objects for equality
    person1 = BaseModel(name="John", age=30)
    person2 = BaseModel(name="John", age=30)
    is_equal = person1 == person2

    # Saving a BaseModel object to a file
    person = BaseModel(name="John", age=30)
    person.save("person.yaml")
"""

import json
import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic.main import IncEx
from pydantic import BaseModel as PydanticBaseModel

from helpers import cache_utils as cas
from helpers.utils import clean_yaml_str, clean_json_str, find_best_match, run_in_background


PathLike = str | Path


class DoubleQuotedDumper(yaml.SafeDumper):
    def represent_str(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(str, DoubleQuotedDumper.represent_str)


class BaseModel(PydanticBaseModel):
    def __str__(self):
        return str(self.to_dict())

    # def __repr__(self):
    #     return str(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, float|int|str], fuzzy=True, cutoff: float = 0.0):
        """
        Creates a BaseModel object from a dictionary.

        Args:
            data: A dictionary containing the data to create the BaseModel object.
            fuzzy: A boolean indicating whether to perform fuzzy matching.
            cutoff: A float indicating the cutoff score for fuzzy matching. Must be a float between 0 and 1.

        Returns:
            BaseModel: The created BaseModel object.
        """
        if not fuzzy:
            return cls(**data)
        if not isinstance(cutoff, float) or cutoff > 1 or cutoff < 0:
            cutoff = 0.0
        field_col_map = {
            field: find_best_match(field, list(data)).as_tuple()
            for field in cls.model_fields
        }
        data = {
            field: data[col] 
            for field, (col, score) in field_col_map.items() 
            if score >= cutoff
        }
        return cls(**data)

    @classmethod
    def from_json(cls, data: str, fuzzy=False, cutoff: float = 0.0):
        """
        Creates a BaseModel object from a JSON string.

        Args:
            data: A JSON string containing the data to create the BaseModel object.
            fuzzy: A boolean indicating whether to perform fuzzy matching.
            cutoff: A float indicating the cutoff score for fuzzy matching. Must be a float between 0 and 1.

        Returns:
            BaseModel: The created BaseModel object.
        """
        data = clean_json_str(data)
        data = json.loads(data)
        return cls.from_dict(data, fuzzy, cutoff)

    @classmethod
    def from_yaml(cls, data: str, fuzzy=False, cutoff: float = 0.0):
        """
        Creates a BaseModel object from a YAML string.

        Args:
            data: A YAML string containing the data to create the BaseModel object.
            fuzzy: A boolean indicating whether to perform fuzzy matching.
            cutoff: A float indicating the cutoff score for fuzzy matching. Must be a float between 0 and 1.

        Returns:
            BaseModel: The created BaseModel object.
        """
        data = clean_yaml_str(data)
        data = yaml.safe_load(data)
        return cls.from_dict(data, fuzzy, cutoff)
    
    @classmethod
    def from_file(cls, path: PathLike, fuzzy=False, cutoff: float = 0.0):
        """
        Creates a BaseModel object from a file.

        Args:
            path: A path to the file containing the data to create the BaseModel object.
            fuzzy: A boolean indicating whether to perform fuzzy matching.
            cutoff: A float indicating the cutoff score for fuzzy matching. Must be a float between 0 and 1.

        Returns:
            BaseModel: The created BaseModel object.
        """
        path = Path(path)
        data = path.read_text(encoding="utf-8")

        if path.suffix == ".json":
            return cls.from_json(data, fuzzy, cutoff) 
        elif path.suffix in [".yml", ".yaml"]:
            return cls.from_yaml(data, fuzzy, cutoff)
        else:
            raise ValueError("Invalid file format. Must be .json or .yaml.")

    def to_dict(
        self,
        mode: Literal['json', 'python'] = 'json',
        include: IncEx = None,
        exclude: IncEx = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False
    ):
        """
        Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        Args:
            mode: The mode in which `to_python` should run.
                If mode is 'json', the output will only contain JSON serializable types.
                If mode is 'python', the output may contain non-JSON-serializable Python objects.
            include: A set of fields to include in the output.
            exclude: A set of fields to exclude from the output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to use the field's alias in the dictionary key if defined.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

        Returns:
            A dictionary representation of the model.
        """
        return self.model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def to_json(
        self, 
        indent=4, 
        sort_keys=False,
        include: IncEx = None,
        exclude: IncEx = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False
    ):
        """
        Generate a JSON representation of the model, optionally specifying which fields to include or exclude.

        Args:
            indent: The indentation level to use when serializing the model.
            sort_keys: Whether to sort the keys in the output.
            include: A set of fields to include in the output.
            exclude: A set of fields to exclude from the output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to use the field's alias in the dictionary key if defined.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

        Returns:
            A JSON representation of the model in string format.
        """
        d = self.to_dict(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )
        return json.dumps(d, indent=indent, sort_keys=sort_keys)

    def to_yaml(
        self,
        indent=4, 
        width=1000,
        sort_keys=False,
        allow_unicode=True,
        include: IncEx = None,
        exclude: IncEx = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False
    ):
        """
        Generate a YAML representation of the model, optionally specifying which fields to include or exclude.

        Args:
            indent: The indentation level to use when serializing the model.
            width: The maximum line width to use when serializing the model to YAML.
            sort_keys: Whether to sort the keys in the output.
            allow_unicode: Whether to allow unicode characters in the output.
            include: A set of fields to include in the output.
            exclude: A set of fields to exclude from the output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to use the field's alias in the dictionary key if defined.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

        Returns:
            A YAML representation of the model in string format.
        """
        d = self.to_dict(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )
        return yaml.dump(
            d,
            allow_unicode=allow_unicode,
            sort_keys=sort_keys,
            indent=indent,
            width=width,
        )

    def to_file(
        self, 
        path: PathLike, 
        indent=4, 
        sort_keys=False, 
        include: IncEx = None,
        exclude: IncEx = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        serialize_as_any: bool = False
    ):
        """
        Save the model to a file (in JSON or YAML), inferring the format from the file extension.

        Args:
            path: The path to the file to save the model.
            indent: The indentation level to use when serializing the model.
            sort_keys: Whether to sort the keys in the output.
            include: A set of fields to include in the output.
            exclude: A set of fields to exclude from the output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to use the field's alias in the dictionary key if defined.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
        """
        common_params = dict(
            indent=indent,
            sort_keys=sort_keys,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )
        path = Path(path)
        if path.suffix == ".json":
            path.write_text(self.to_json(**common_params), encoding="utf-8")
        elif path.suffix in [".yml", ".yaml"]:
            path.write_text(self.to_yaml(**common_params), encoding="utf-8")
        else:
            raise ValueError("Invalid file format. Must be .json or .yaml.")

    def __hash__(self) -> int:
        return hash(self.to_yaml())

    def __eq__(self, other: "BaseModel") -> bool:
        if not isinstance(other, BaseModel):
            return False
        return self.to_yaml() == other.to_yaml()

    @classmethod
    def load_from_cache(cls, key: str, collection: str = None, get_expired: bool = False, return_as_dict: bool = False):
        """
        Load a model from cache by key.

        Args:
            key (str): The key to load from cache.
            collection (str, optional): The name of the collection to load from. Defaults to the name of the class.
            get_expired (bool, optional): Whether to get expired objects. Defaults to False.
            return_as_dict (bool, optional): Whether to return the loaded model as a dictionary. Defaults to False.

        Returns:
            The loaded model or None if not found in cache.
        """
        collection = collection or cls.__name__
        data = cas.load(key, collection, get_expired=get_expired)
        if data is None:
            return None
        if return_as_dict:
            return data
        try:
            obj = cls(**data)
        except Exception as e:
            logging.error(f"Failed to load {collection!r} for class {cls.__name__} from cache for key {key!r}: {e}")
            return None
        obj.__is_cached__ = True
        return obj
    
    def save_to_cache(self, key: str, expire_after_seconds: int | None = 3600 * 24 * 90, collection: str = None, background: bool = False):
        """
        Save a model to cache by key.

        Args:
            key (str): The key to save to cache.
            expire_after_seconds (int, optional): The expiry time in seconds since cached time. Defaults to 3600 * 24 * 90 (90 days).
                If None, the object will never expire.
            collection (str, optional): The name of the collection to save to.
                Defaults to the name of the class.
            background (bool, optional): Whether to save in the background. Defaults to False.
                If background is True, the save will be run in a separate thread and not block the main thread. **This might not give errors.**
        """
        collection = collection or self.__class__.__name__
        if background:
            run_in_background(cas.save, key, collection, self.to_dict(), expire_after_seconds=expire_after_seconds)
        else:
            cas.save(key, collection, self.to_dict(), expire_after_seconds=expire_after_seconds)

    @classmethod
    def delete_from_cache(cls, key: str, collection: str = None):
        """
        Delete a model from cache by key.

        Args:
            key (str): The key to delete from cache.
            collection (str, optional): The name of the collection to delete from.
                Defaults to the name of the class.
                
        Returns:
            bool: True if the key was deleted, False otherwise.
        """
        collection = collection or cls.__name__
        return cas.delete(key, collection)

    @classmethod
    def query_from_cache(cls, query: dict, collection: str = None):
        """
        Query the cache for the given query dict and return a list of objects
        of this class.

        Args:
            query (dict): The query dict to search the cache with.
            collection (str, optional): The name of the collection to query.
                Defaults to the name of the class.

        Returns:
            List[BaseModel]: A list of objects of this class that match the query.
        """
        collection = collection or cls.__name__
        return [cls(**d) for d in cas.query(query, collection)]
