import re
import uuid
import hashlib
import logging
import threading
import traceback
import multiprocessing
import concurrent.futures
from typing import (
    Any,
    List,
    Tuple,
    Literal,
    Callable,
    Iterable,
    NamedTuple,
    MutableMapping,
)

from fuzzywuzzy import process


def run_in_background(func, *args, **kwargs):
    """
    Run a function in the background.

    Args:
        func (function): The function to run in the background.
        *args: Variable number of arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
    """
    thread = threading.Thread(target=func, name=getattr(func, "__name__", None), args=args, kwargs=kwargs)
    thread.daemon = True  # Set as daemon so it exits when main thread exits
    thread.start()

def get_trace(e: Exception, n: int = 5):
    """Get the last n lines of the traceback for an exception"""
    return "".join(traceback.format_exception(e)[-n:])

def run_parallel_exec(exec_func: Callable, iterable: Iterable, *func_args, **kwargs):
    """
    Runs the `exec_func` function in parallel for each element in the `iterable` using a thread pool executor.
    
    Parameters:
        exec_func (Callable): The function to be executed for each element in the `iterable`.
        iterable (Iterable): The collection of elements for which the `exec_func` function will be executed.
        *func_args: Additional positional arguments to be passed to the `exec_func` function.
        **kwargs: Additional keyword arguments to customize the behavior of the function.
            - max_workers (int): The maximum number of worker threads in the thread pool executor. Default is 100.
            - quiet (bool): If True, suppresses the traceback logging for exceptions. Default is False.
    
    Returns:
        list[tuple]: A list of tuples where each tuple contains the element from the `iterable` and the result of executing the `exec_func` function on that element.

    Example:
        >>> from app.utils.helpers import run_parallel_exec
        >>> run_parallel_exec(lambda x: str(x), [1, 2, 3])
        [(1, '1'), (2, '2'), (3, '3')]
    """
    func_name = f"{exec_func.__name__} | parallel_exec | " if hasattr(exec_func, "__name__") else "unknown | parallel_exec | "
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=kwargs.pop("max_workers", 100), thread_name_prefix=func_name
    ) as executor:
        # Start the load operations and mark each future with each element
        future_element_map = {
            executor.submit(exec_func, element, *func_args): element
            for element in iterable
        }
        result: list[tuple] = []
        for future in concurrent.futures.as_completed(future_element_map):
            element = future_element_map[future]
            try:
                result.append((element, future.result()))
            except Exception as exc:
                log_trace = exc if kwargs.pop("quiet", False) else get_trace(exc, 3)
                logging.error(f"Got error while running parallel_exec: {element}: \n{log_trace}")
                result.append((element, exc))
        return result

def run_parallel_exec_but_return_in_order(exec_func: Callable, iterable: Iterable, *func_args, **kwargs):
    """
    Runs the `exec_func` function in parallel for each element in the `iterable` using a thread pool executor.
    Returns the result in the same order as the `iterable`.
    """
    # note this is usable only when iterable has types that are hashable
    result = run_parallel_exec(exec_func, iterable:=list(iterable), *func_args, **kwargs)

    # sort the result in the same order as the iterable
    result.sort(key=lambda x: iterable.index(x[0]))

    return [x[-1] for x in result]


def run_functions_in_parallel(
    functions: List[Callable],
    max_workers: int = 100,
    parallelism: Literal["thread", "process"] = "thread",
    prefix: str = "unknown",
    quiet: bool = False,
):
    """
    Runs a list of functions in parallel using ThreadPoolExecutor.

    Args:
        functions (List[Callable]): A list of functions to run concurrently.
        max_workers (int, optional): The maximum number of worker threads in the thread pool executor. Defaults to 100.
        parallelism ("thread", "process"): The type of parallelism to use. Defaults to "thread".
        prefix (str, optional): The prefix to use for the thread name. Defaults to "unknown". Only used if parallelism is "thread".
        quiet (bool, optional): If True, suppresses the traceback logging for exceptions. Defaults to False.

    Returns:
        List[Tuple[str, Any]]: A list of tuples containing the function name and the result of the function.
    """
    results: List[Tuple[str, Any]] = []
    max_workers = min(max_workers, len(functions))
    def pool_executor():
        if parallelism == "process":
            return concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        elif parallelism == "thread":
            return concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix=f"{prefix} | parallel_func | "
            )
    with pool_executor() as executor:
        # Map the functions to the executor and run them in parallel
        futures = {executor.submit(func): getattr(func, "__name__", None) for func in functions}
        for future in concurrent.futures.as_completed(futures):
            func_name = futures[future]
            try:
                results.append((func_name, future.result()))
            except Exception as exc:
                log_trace = exc if quiet else get_trace(exc, 3)
                logging.error(f"Got error while running parallel_exec: {func_name}: \n{log_trace}")
                results.append((func_name, exc))
    return results

def _execute_function(func: Callable, quiet: bool = False) -> Tuple[str, Any]:
    """Helper function to execute a function and capture its output or error."""
    fname = getattr(func, "__name__", None)
    try:
        result = func()
        return (fname, result)
    except Exception as exc:
        log_trace = exc if quiet else get_trace(exc, 3)
        logging.error(f"Got error while running parallel_exec: {fname}: \n{log_trace}")
        return (fname, exc)

def run_functions_in_parallel_process(functions: List[Callable], max_workers: int = 10, quiet: bool = False, **kwargs):
    """Runs a list of functions in parallel using multiprocessing."""
    max_workers = min(max_workers, len(functions))

    with multiprocessing.Pool(processes=max_workers) as pool:
        results = pool.map(_execute_function, functions)
    return results


def remove_backticks(text: str) -> str:
    return re.sub(r"```\w+\n(.*)\n```", r"\1", text, flags=re.DOTALL)

def remove_comments(text: str) -> str:
    return re.sub(r'\s+//\s+.*', '', text)

def clean_json_str(text: str) -> str:
    cleaned_text = remove_backticks(text)
    cleaned_text = remove_comments(cleaned_text)
    return cleaned_text

def clean_yaml_str(text: str) -> str:
    cleaned_text = remove_backticks(text)
    return cleaned_text

class Match(NamedTuple):
    text: str
    """The text that matched"""
    score: float
    """The score of the match. 100 is a perfect match"""
    
    def as_tuple(self) -> tuple[str, float]:
        return self.text, self.score

def find_best_match(query: str, options: list[str], cutoff: int = 0):
    """Find the best match from a list of options"""
    if not options:
        return Match(None, 0)
    return Match(*(process.extractOne(query, options, score_cutoff=cutoff) or (None, 0)))

def recursive_string_operator(
    data, fn: Callable[[str], str], skip_keys: list[str] = [], max_workers=4
):
    """
    Recursively applies the given function to the input data, handling strings, lists, tuples, sets, dictionaries, and BaseModel objects.

    Args:
        data: The input data to be processed.
        fn: The function to be applied to the data.
        skip_keys: A list of keys to be skipped when processing dictionaries.
        max_workers: The maximum number of workers for parallel execution. Defaults to 4.

    Returns:
        The processed data in the same format as the input.
        
    Note:
        The `fn` function should take a single argument (a string) and return a string. 
        Also, any Exceptions raised by the `fn` function should be caught and handled appropriately.
        
        The `skip_keys` parameter works only when the input data is a dictionary or a BaseModel object. 
    
    Example:
        >>> data = "Hello, World!"
        >>> fn = lambda x: x.upper()
        >>> recursive_string_operator(data, fn)
        'HELLO, WORLD!'
        >>> data = {"a": 1, "b": [2, "hello", ["world"]], "c": {"d": "hi", "e": "hello"}, "f": "world", "g": fn}
        >>> recursive_string_operator(data, fn, skip_keys=["d", "f"])
        {'a': 1, 'b': [2, 'HELLO', ['WORLD']], 'c': {'d': 'hi', "e": "HELLO"}, "f": "world", "g": <function __main__.<lambda>(x)>}
    """
    if isinstance(data, str):
        # Directly apply function to string data
        return fn(data)

    # Define a base function to recursively apply on each element
    base_parallel_func = lambda _data: recursive_string_operator(
        data=_data, fn=fn, skip_keys=skip_keys or [], max_workers=max_workers
    )

    if isinstance(data, (list, tuple, set)):
        # Check if all elements in the collection are strings
        are_all_strings = all([isinstance(x, str) for x in data])
        if are_all_strings:
            _combined = "||".join(data)
            if len(_combined) < 1000:  # Optimize by processing combined strings if not too large
                _operated = fn(_combined).split("||")
                if len(_operated) == len(data):  # Ensure length remains consistent
                    return _operated
        
        # Apply function to each element in parallel
        return [
            x
            for x in run_parallel_exec_but_return_in_order(
                base_parallel_func, data, max_workers=max_workers
            )
        ]

    if isinstance(data, dict):
        # Process non-skipped dictionary values in parallel
        v_return_tuples = run_parallel_exec(
            base_parallel_func,
            [v for k, v in data.items() if k not in skip_keys],
            max_workers=max_workers,
        )
        # Sort results to maintain order
        v_return_tuples.sort(
            key=lambda x: [v for k, v in data.items() if k not in skip_keys].index(x[0])
        )
        # Construct result dictionary
        return {
            k: (
                ([y for x, y in v_return_tuples if x == v] or [v])[0]
                if k not in skip_keys
                else v
            )
            for k, v in data.items()
        }

    # Return data unchanged for unsupported types
    return data

def recursive_dict_operator(d: dict, fn: Callable[[dict], MutableMapping]):
    """
    Recursively applies a given function to all dictionaries within the given dictionary.

    Concept:
        - This function traverses the input dictionary, applying the specified function to each sub-dictionary it encounters.
        - It works by recursively calling itself on each nested dictionary, ensuring that the function is applied at every level.
        - The base case occurs when the dictionary has no sub-dictionaries, at which point the function is applied directly.

    Args:
        d (dict): The dictionary to be processed.
        fn (Callable[[dict], MutableMapping]): The function to apply to each dictionary within the given dictionary.

    Returns:
        dict: The processed dictionary.

    Example:
        >>> def upkeys(x):
        ...     return {k.upper(): v for k, v in x.items()}
        >>> data = {"a": 1, "b": {"c": "hello", "d": "world"}}
        >>> result = recursive_dict_operator(data, upkeys)
        >>> result
        {'A': 1, 'B': {'C': 'hello', 'D': 'world'}}
    """
    has_dict = any(isinstance(v, dict) for _, v in d.items())
    if has_dict:
        # If the dictionary has any sub-dictionaries, process them recursively
        return fn(
            {
                k: recursive_dict_operator(v, fn) if isinstance(v, dict) else v
                for k, v in d.items()
            }
        )
    else:
        # If the dictionary has no sub-dictionaries, apply the function directly
        return fn(d)

def get_file_hash(file_path: str, hash_algorithm='sha256'):
    """
    Computes the hash of the given file.

    Parameters
    ----------
    file_path: str
        The path to the file to be hashed.
    hash_algorithm: str, optional
        The hash algorithm to use. Defaults to 'sha256' and must be one of the
        algorithms supported by hashlib.new() (e.g. 'md5', 'sha1', 'sha256', etc.).

    Returns
    -------
    str
        The hexadecimal representation of the hash.
    """
    hash_obj = hashlib.new(hash_algorithm)
    
    # Read the file in binary mode and update the hash object
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            hash_obj.update(chunk)
    
    # Return the hexadecimal representation of the hash
    return hash_obj.hexdigest()

def hash_uuid(text: str, base_uuid: uuid.UUID | None = None):
    """
    Generates a hash-based UUID using the given text and an optional base UUID.

    Args:
        text (str): The text to be used for generating the hash-based UUID.
        base_uuid (uuid.UUID | None, optional): The optional base UUID to use for hashing. Defaults to None.

    Returns:
        uuid.UUID: The hash-based UUID generated from the input text and base UUID.
    """
    if not isinstance(base_uuid, uuid.UUID):
        base_uuid = uuid.NAMESPACE_DNS
    return uuid.uuid3(base_uuid, text)

def recursively_remove_keys_from_dict(data: dict, keys: list[str]) -> dict:
    """
    Recursively removes specified keys from a dictionary and its nested dictionaries.

    Concept:
        - This function works by recursively traversing the input dictionary and its nested dictionaries.
        - For each key-value pair, it checks if the key is in the list of keys to be removed.
        - If it is, the key-value pair is skipped.
        - If the value is a dictionary, the function is called recursively on that dictionary.
        - If the value is a list, the function is applied to each item in the list.
        - Finally, a new dictionary is returned with the specified keys removed.

    Args:
        data (dict): The dictionary from which keys should be removed.
        keys (list[str]): A list of keys to remove.

    Returns:
        dict: A new dictionary with the specified keys removed.
    """
    if not isinstance(data, dict):
        return data

    # Create a new dictionary to avoid modifying the original
    cleaned_dict = {}

    for key, value in data.items():
        if key not in keys:
            if isinstance(value, dict):
                # Recursively remove keys from nested dictionary
                cleaned_dict[key] = recursively_remove_keys_from_dict(value, keys)
            elif isinstance(value, list):
                # If the value is a list, recursively apply the function to its items
                cleaned_dict[key] = [
                    recursively_remove_keys_from_dict(item, keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned_dict[key] = value

    return cleaned_dict

def get_range(rng: str|list[int]):
    """
    Parse a string containing ranges and individual integers, or directly process a list of integers, to return a sorted list of integers.

    If a string is provided, it should contain numbers and ranges in the format:
    "start1-end1,start2-end2,...,startN-endN" or individual numbers separated by commas.
    The function processes this string to produce a sorted list of integers within the specified ranges or individual integers.

    If a list of integers is provided, it simply returns a sorted version of that list.

    Args:
        rng (str or list[int]): The input which can either be a string representing ranges and individual numbers,
                              or a list of integers.

    Returns:
        list[int]: A sorted list of integers derived from the input string or list.

    Examples:
        >>> get_range("6-8,10-12")
        [6, 7, 8, 10, 11, 12]

        >>> get_range([5, 3, 2])
        [2, 3, 5]
    """
    # If the input is a string, it should contain numbers and ranges
    # separated by commas. Process this string to produce a sorted list
    # of integers within the specified ranges or individual integers.
    all_ids = [] if isinstance(rng, str) else rng
    if not all_ids:
        rng = rng.replace(" ", "")
        for x in rng.split(","):
            # Split the input string into individual numbers and ranges.
            # If the input string contains a range, split it into its start
            # and end values.
            low_high = x.split("-")
            if not x.replace("-", "").isdigit():
                # If the input string is not a valid number or range, skip it.
                continue
            if len(low_high) == 2:
                # If the input string contains a range, generate a list of
                # numbers within that range (inclusive).
                ids = range(int(low_high[0]), int(low_high[1])+1)
                all_ids.extend(ids)
            elif len(low_high) == 1:
                # If the input string contains an individual number, add it
                # to the list of IDs.
                all_ids.extend([int(x)])
    # Return a sorted list of integers derived from the input string or list.
    return sorted(all_ids)

def list_to_range(lst: list[int]) -> str:
    """
    Converts a sorted list of integers into a string representing ranges and individual numbers.

    This function takes a sorted list of integers and generates a string that represents
    the list in a condensed form. If the list contains consecutive numbers, they will be
    represented as a range (e.g. 1-3). Individual numbers will be represented as a single
    number (e.g. 5).

    Args:
        lst (list[int]): A sorted list of integers.

    Returns:
        str: A string representing ranges and individual numbers.

    Examples:
        >>> list_to_range([2, 3, 5])
        '2-3,5'

        >>> list_to_range([6, 7, 8, 10, 11, 12])
        '6-8,10-12'
    """
    if not lst:
        # If the list is empty, return an empty string.
        return ""
    
    ranges = []
    start = lst[0]
    end = lst[0]
    
    for num in lst[1:]:
        # If the current number is consecutive with the previous one, update 'end'.
        if num == end + 1:
            end = num
        else:
            # If not, generate the range string for the current range.
            if start == end:
                # If the range only contains one number, just add it to the list.
                ranges.append(str(start))
            else:
                # If the range contains multiple numbers, add the range string to the list.
                ranges.append(f"{start}-{end}")
            # Update 'start' and 'end' to the current number.
            start = num
            end = num
    
    # Generate the range string for the last range.
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    # Join the ranges with commas and return the result.
    return ",".join(ranges)
