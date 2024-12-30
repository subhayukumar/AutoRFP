import re
import logging
from typing import Any, Callable, Dict, List


def clean_text(text: str):
    """
    Cleans the input text by removing unwanted characters and normalizing spaces.

    This function performs the following operations on the input text:
    - Strips leading and trailing whitespace.
    - Removes bullet points and special characters, keeping only alphanumeric
      characters, spaces, '@', and '.'.
    - Eliminates emojis and other pictographic symbols using a predefined regex pattern.
    - Collapses multiple newlines into a single newline.
    - Replaces multiple spaces with a single space.

    Args:
        text (str): The text to be cleaned.

    Returns:
        str: The cleaned text, free of unwanted characters and normalized for consistent spacing.
    """
    # Remove leading and trailing whitespace
    text = text.strip()

    # Remove bullet points and special characters
    text = re.sub(r"•", "", text)  # Replace bullet points with an empty string
    text = re.sub(
        r"[^\w\s@.-]", "", text
    )  # Remove non-alphanumeric characters except @ and .

    # Remove emojis using regex (you may need to expand this list)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emojis
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
        "\U0001F700-\U0001F77F"  # Alchemical Symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2"  # Enclosed Alphanumeric Supplement
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(r"", text)
    # text = text.lower()

    # Testing cleanup
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_replacement_keys(text: str) -> List[str]:
    """
    Get all the keys that can be replaced in a string

    Args:
        text (str): The string to search for keys

    Example:
        >>> text = "Hello, {name1}!\nMy name is {name2}!"
        >>> get_replacement_keys(text)
        ['name1', 'name2']
    """
    return re.findall(r"\{(\w+?)\}", text)


def text_replacer(text: str, replacements: dict[str, Any], curly_braces: bool = True):
    """
    Replace all keys in a string with their corresponding values

    Args:
        text (str): The string to replace the keys
        replacements (dict[str, Any]): The replacements
        curly_braces (bool, optional): Whether to use curly braces or not

    Example:
        >>> replacements = {
        ...     "name1": "John",
        ...     "name2": "Smith"
        }

        >>> text = "Hello, {name1}! My name is {name2}!"
        >>> text_replacer(text, replacements)
        "Hello, John! My name is Smith!"

        >>> text = "Hello, name1! My name is name2!"
        >>> text_replacer(text, replacements, curly_braces=False)
        "Hello, John! My name is Smith!"
    """
    replacement_keys = set(get_replacement_keys(text))
    if replacement_keys - set(replacements):
        logging.warning(f"Keys not found in replacement: {replacement_keys - set(replacements)}")
    for key, value in replacements.items():
        if curly_braces:
            key = f"{{{key}}}"
        text = text.replace(key, str(value))
    return text


def file_read_and_replacer(
    file_path: str, replacements: dict[str, Any], curly_braces: bool = True
):
    """
    Read a file and replace all keys in it with their corresponding values

    Args:
        file_path (str): The file path
        replacements (dict[str, Any]): The replacements
        curly_braces (bool, optional): Whether to use curly braces or not
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text: str = f.read()
    return text_replacer(text, replacements, curly_braces)


def read_prompt(
    prompt_name: str,
    replacements: dict[str, Any] = {},
    directory: str = "prompts",
    extension: str = ".txt",
) -> str:
    """
    Reads a prompt file, applies replacements, and returns the modified content as a string.

    This function reads a text file based on the provided prompt name and directory,
    applies any specified replacements to placeholders within the file, and returns
    the resulting text. It is useful for dynamically generating content from templates.

    Args:
        prompt_name (str): The name of the prompt file (without extension) to read.
        replacements (dict[str, Any], optional): A dictionary of replacements to apply
            to placeholders in the prompt file. Defaults to an empty dictionary.
        directory (str, optional): The directory where the prompt files are located.
            Defaults to "prompts".
        extension (str, optional): The file extension of the prompt files. Defaults to ".txt".

    Returns:
        str: The content of the prompt file with the specified replacements applied.
    """
    return file_read_and_replacer(f"{directory}/{prompt_name}{extension}", replacements)


def the_words_intersect(text1: str, text2: str):
    """
    Determine if there are common words between two strings.

    This function converts both input strings to lowercase and splits them 
    into words using non-word characters as delimiters. It then creates sets 
    of words from these strings and checks for any intersection between the 
    two sets, indicating shared words.

    Args:
        text1 (str): The first input string.
        text2 (str): The second input string.

    Returns:
        bool: True if there is at least one common word, otherwise False.
    """
    words_set1 = set(re.split(r"\W+", text1.lower()))
    words_set2 = set(re.split(r"\W+", text2.lower()))
    return bool(words_set1.intersection(words_set2))

def remove_unnecessary_text(text: str, unnecessary_texts: List[str]) -> str:
    """
    Remove specified unnecessary substrings from the input text.

    This function iterates over a list of substrings and removes each 
    occurrence from the input text, returning the cleaned text.

    Args:
        text (str): The original text to clean.
        unnecessary_texts (List[str]): A list of substrings to remove from the text.

    Returns:
        str: The text with all specified unnecessary substrings removed.
    """
    for text_to_remove in unnecessary_texts:
        text = text.replace(text_to_remove, "")
    return text

def filter_by_keywords(texts: List[str], keywords: List[str]) -> List[str]:
    """
    Filters a collection of text entries to find those containing any of the specified keywords.

    This function performs a case-insensitive search using regular expressions to match 
    the keywords within the text entries. The keywords can be complex patterns, allowing 
    for flexible filtering criteria.

    Args:
        texts (List[str]): A list of text strings to be filtered.
        keywords (List[str]): A list of keywords or regular expression patterns to match.

    Returns:
        List[str]: A list of text entries that contain any of the specified keywords.
    """
    pattern = re.compile(f'(.*(?:{"|".join(keywords)}).*)', re.IGNORECASE)
    return pattern.findall('\n'.join(texts))

def snake_to_title(snake_str: str) -> str:
    """
    Converts a snake_case string to title case.

    Example:
        >>> snake_str = "hello_world"
        >>> snake_to_title(snake_str)
        "Hello World"
    """
    # Replace underscores with spaces
    spaced_str = snake_str.replace('_', ' ')
    # Capitalize each word
    title_str = spaced_str.title()
    return title_str


def dict_to_context(
    dict: Dict[str, str],
    key_prefix: str = "### ",
    key_converter: Callable[[str], str] = snake_to_title,
) -> str:
    """
    Converts a dictionary to a string in a context format, with each key-value pair separated by two newlines.
    The key is prefixed with the given key_prefix and converted to title case by default.
    The value is surrounded by triple backticks to create a code block.

    Args:
        dict (Dict[str, str]): The dictionary to be converted.
        key_prefix (str, optional): The prefix to be added to each key. Defaults to "### ".
        key_converter (Callable[[str], str], optional): The function to be used to convert each key. Defaults to snake_to_title.

    Returns:
        str: The string representation of the dictionary in context format.
    """
    return "\n\n".join(
        f"{key_prefix}{key_converter(key)}\n```\n{value}\n```"
        for key, value in dict.items()
    )

def slugify(text: str, replace_specials_with: str = "_", replace_spaces_with: str = "-") -> str:
    return re.sub(r'[^\w\s-]+', replace_specials_with, text).strip().lower().replace(' ', '-')
