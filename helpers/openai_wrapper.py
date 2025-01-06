from typing import Dict, List
import openai
from config import API_KEY

openai.api_key = API_KEY


def get_chatgpt_response(prompt, model="gpt-3.5-turbo-16k", temperature=0.2, max_tokens=9000, n=1, seed: int = None):
    """
    Generates a response from ChatGPT based on the given prompt.

    Args:
        prompt (str): The input prompt to guide the ChatGPT response.
        model (str, optional): The model ID for ChatGPT. Defaults to "gpt-3.5-turbo-16k".
        temperature (float, optional): The randomness level in the response generation. 
                                       Higher values yield more random responses. Defaults to 0.2.
        max_tokens (int, optional): The maximum number of tokens to generate in the response. Defaults to 9000.
        n (int, optional): The number of responses to generate. Defaults to 1.

    Returns:
        str: The generated response from ChatGPT. Returns an empty string if no content is generated.
    """
    messages = [{"role": "system", "content": "You are a Senior Software architect..."}, {"role": "user", "content": prompt}]

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=n,
        stop=None,
        seed=seed,
    )
    generated_response = response['choices'][0]['message']['content'].strip()
    return generated_response if generated_response else ''


def call_openai(messages: List[Dict[str, str]], model="gpt-3.5-turbo-16k", temperature=0.2, n=1, *args, **kwargs) -> List[str]:
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        n=n,
        *args, 
        **kwargs, 
    )
    return [x['message']['content'].strip() for x in response['choices']]
