import logging
import os

import httpx
import openai

from custom_exceptions import ASRException

logger = logging.getLogger(__name__)


async def get_openai_completion(prompt: str) -> str:
    """
    Gets the completion from OpenAI based on the given prompt.

    :param prompt: The prompt to send to OpenAI.
    :return: The text completion.
    """
    try:
        chat_completion = await openai.ChatCompletion.acreate(
            deployment_id="deep-new",
            model="gpt-4",
            messages=[{"role": 'user', "content": prompt}]
        )
        return chat_completion["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenAI completion error: {e}")
        raise


async def send_request(path):
    from file_utils import read_file_content
    url = "https://deep-whisper.openai.azure.com/openai/deployments/whisper/audio/transcriptions?api-version=2023-05-20-preview"
    api_key = os.getenv('OPENAI_API_KEY_WHISPER',
                        'default_api_key')  # You can provide a default API key if that's acceptable
    if not api_key:
        raise ASRException("Environment variable OPENAI_API_KEY_WHISPER is not set!")

    headers = {
        'api-key': api_key,
    }

    # Read the audio file content
    file_content = await read_file_content(path)
    files = {
        'file': ('audio_file.mp3', file_content)
        # Ensure that the filename is set correctly, possibly based on the path
    }

    # Send the request and handle the response
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(url, headers=headers, files=files)
        response.raise_for_status()
        logger.info("Successfully received response from ASR service.")
        return response.json()["text"]
    except httpx.HTTPStatusError as exc:
        logger.error(f"Error response {exc.response.status_code} while sending request to ASR.")
        raise ASRException(f"Error response {exc.response.status_code}", status_code=exc.response.status_code) from exc
    except httpx.RequestError as exc:
        logger.error(f"An error occurred while requesting {exc.request.url!r}.")
        raise ASRException("Network-related error occurred") from exc
