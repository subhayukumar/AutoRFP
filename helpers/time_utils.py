import re
import random
from copy import deepcopy
from typing import List, Union
from datetime import date, datetime, timedelta, timezone


def humanize_datetime(dt: datetime) -> str:
    """
    Convert a datetime object to a human-readable string format.

    Args:
        dt (datetime): The datetime object to be converted.

    Returns:
        str: A string representing the date and time in the format 
        'Month Day, Year at Hour:Minute AM/PM (Timezone)', with an 
        empty timezone omitted.
    
    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2023, 6, 1, 12, 34, 56, tzinfo=timezone(timedelta(hours=-5)))
        >>> humanize_datetime(dt)
        'June 1, 2023 at 12:34 PM (CST)'
    """
    return dt.strftime('%B %d, %Y at %I:%M %p (%Z)').replace(" ()", "")

def humanize_date(dt: Union[datetime, date]):
    """
    Convert a datetime or date object to a human-readable string format.

    Args:
        dt (datetime or date): The datetime or date object to be converted.

    Returns:
        str: A string representing the date in the format 'Month Day, Year'.
    
    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2023, 6, 1)
        >>> humanize_date(dt)
        'June 1, 2023'
    """
    return dt.strftime('%B %d, %Y')

def get_timestamp_uid(make_uuid=True):
    """
    Get a unique id for a timestamp. If `make_uuid` is True, an UUID will be generated from the timestamp.
    
    Explanation:
        - Generated using the current timestamp down to the microsecond.
        - The first 20 characters represent the timestamp.
        - A 12-digit random number is appended to ensure uniqueness.
        - This ID format can be used as a sort key since it maintains chronological order.
        
    Probability of Conflict:
        - The 12-digit random number has 1 trillion (10^12) possible combinations.
        - The probability of two keys generated at the exact same microsecond having the same random number is 1 in 1 trillion (0.000000000001).
        - This makes the likelihood of a conflicting key extremely low.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    uid: str = re.sub(r'[:\.\-\+TZ\s]', '', timestamp)
    if make_uuid:
        rndm = str(random.randrange(10 ** 11, 10 ** 12))
        uid = f'{uid[:8]}-{uid[8:12]}-{uid[12:16]}-{uid[16:20]}-{rndm}'
    return uid

def get_delta_day_hr_min_sec(td: timedelta):
    """
    Break down a timedelta into its constituent days, hours, minutes, and seconds.
    
    Args:
        td (timedelta): The timedelta to be broken down.
    
    Returns:
        tuple: A tuple of four integers, representing the number of days, hours, minutes, and seconds in the timedelta.
    """
    minutes, seconds = divmod(td.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return days, hours, minutes, seconds

def format_time_delta(td: timedelta = timedelta(seconds=0), pre: str = '', post: str = ''):
    """
    Format a timedelta into a string showing the most relevant parts.

    Args:
        td (timedelta): The timedelta to be formatted.
        pre (str): A string to be prepended to the formatted string.
        post (str): A string to be appended to the formatted string.

    Returns:
        str: A string representing the timedelta in a human-readable format.
            Two of the most relevant parts are shown in the following order: days, hours, minutes, seconds.

    Examples:
        >>> from datetime import timedelta
        >>> td = timedelta(days=1, hours=2, minutes=3, seconds=4)
        >>> format_time_delta(td)
        "1 day, 2 hours"
        >>> format_time_delta(timedelta(seconds=0))
        "0 seconds"
    """
    day, hr, min, sec = get_delta_day_hr_min_sec(td)
    
    def _make_str(n: int, _type: str):
        """
        Construct a string from a number and a unit type.

        Args:
            n (int): The number to be used in the string.
            _type (str): The type of unit, as a single character.
                Possible values: 'd' for day, 'h' for hour, 'm' for minute, 's' for second.

        Returns:
            str: A string in the format "<n> <unit>{s}", where <n> is the given number,
                <unit> is the unit name based on `_type`, and {s} is the plural form suffix
                if the number is not 1.
        """
        _map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        return f"{int(n)} {_map[_type]}{(('', 's')[n!=1])}"
    
    messages: List[str] = []
    
    if day:
        messages.append(_make_str(day, "d"))
    if hr:
        messages.append(_make_str(hr, "h"))
    if min and not day:
        messages.append(_make_str(min, "m"))
    if not day and not hr:
        messages.append(_make_str(sec, "s"))

    return f"{pre}{', '.join(messages)}{post}"

def format_dmy_in_list_of_dicts(
    data: list[dict],
    field_name: str,
    dmy_key: str,
    format_to_delta: bool = False,
    delta_date: str | date = None,
    day_key: str = "day",
    month_key: str = "month",
    year_key: str = "year",
) -> list[dict]:
    """
    Format date fields in a list of dictionaries.

    This function processes a list within a dictionary, converting date components 
    (year, month, day) into a formatted date string. If `format_to_delta` is True, 
    the date is formatted as a time delta from the `delta_date`.

    Args:
        data (list[dict]): The source data containing lists of dictionaries.
        field_name (str): The key for the list within `data`.
        dmy_key (str): The key in the dictionary containing the date components.
        format_to_delta (bool, optional): Whether to format as a time delta. Defaults to False.
        delta_date (str | date, optional): The reference date for delta calculation. Defaults to None.
        day_key (str, optional): The key for the day component. Defaults to "day".
        month_key (str, optional): The key for the month component. Defaults to "month".
        year_key (str, optional): The key for the year component. Defaults to "year".

    Returns:
        list[dict]: The modified data with formatted date strings.
    """
    # Create a deep copy to avoid mutating the original data
    data = deepcopy(data)
    lst = data[field_name]
    
    for d in lst:
        dv = d[dmy_key]
        if not isinstance(dv, dict):
            # Skip if the date value is not a dictionary
            continue
        
        # Construct a date object from the year, month, and day components
        dt = date(
            year=int(dv[year_key]), month=int(dv[month_key]), day=int(dv[day_key])
        )
        
        if format_to_delta:
            # Determine the reference date for delta calculation
            delta_date = date.today() if delta_date is None else (
                delta_date if isinstance(delta_date, date) else date.fromisoformat(delta_date)
            )
            
            # Calculate the timedelta between the reference date and the constructed date
            td = delta_date - dt
            
            # Format the timedelta as a human-readable string
            if td.days > 0:
                d[dmy_key] = format_time_delta(abs(td), post=" ago")
            else:
                d[dmy_key] = format_time_delta(td, pre="in ")
        else:
            # Format the date as an ISO8601 string
            d[dmy_key] = dt.isoformat()

    return data
