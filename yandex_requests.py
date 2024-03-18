import asyncio
import os
import logging
import boto3
import httpx
from dotenv import load_dotenv

load_dotenv()

session = boto3.session.Session()
s3 = session.client(
    service_name='s3',
    endpoint_url=os.getenv('endpoint_url'),
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key')
)
logging.basicConfig(level=logging.INFO)


# boto3.set_stream_logger('botocore', level='DEBUG')
async def get_completion(prompt_text):
    prompt = {
        "modelUri": os.getenv('YANDEX_MODEL_LINK'),
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": "You are helful assistant"
            },
            {
                "role": "user",
                "text": prompt_text
            },
        ]
    }
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {os.getenv('YANDEX_API_KEY')}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=prompt)
    result = response.json()['result']['alternatives'][0]['message']['text']
    print(result)
    return result


def upload_file(file_path):
    s3.upload_file(file_path, 'sonnyroot', file_path)
    return file_path


async def delete_file(filename):
    url = f"https://storage.yandexcloud.net/sonnyroot/{filename}"
    api_key = os.getenv('YANDEX_API_KEY')
    headers = {
        "Authorization": f"Bearer  {api_key}",
    }
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
        print(response.status_code)
    return response.status_code


async def stt(file_path):
    url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    api_key = os.getenv('YANDEX_API_KEY_STT')
    headers = {
        "Authorization": f"Api-Key {api_key}",
    }
    body = {
        "config": {
            "specification": {
                "literature_text": True,
                "audioEncoding": "MP3",
            }
        },
        "audio": {
            "uri": f"https://storage.yandexcloud.net/sonnyroot/{file_path}"
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
    print(response.json())
    return response


async def check(response, interval):
    operation_id = response.json()['id']
    url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
    api_key = os.getenv('YANDEX_API_KEY_STT')
    headers = {
        "Authorization": f"Api-Key {api_key}",
    }
    max_attempts = 5

    attempts = 0
    while attempts < max_attempts:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            print(response.json())
        if response.json()['done']:
            data = response.json()['response']['chunks']
            final_text = ''
            for item in data:
                if item['alternatives']:
                    text = item['alternatives'][0]['text']
                    final_text += text + ' '
            return final_text.strip()

        attempts += 1
        await asyncio.sleep(interval)

    raise TimeoutError("Превышено максимальное количество попыток опроса API.")


async def get_text_from_audio(file_path):
    ...
    file_path = upload_file(file_path)
    response = await stt(file_path)
    text = await check(response, 5)
    print(text)
    return text
