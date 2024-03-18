import httpx
import asyncio
from db import check_token_in_db, write_token_to_db, add_user, check_user_in_db

# Базовые настройки для запросов
base_url = 'https://pay.fait.gl/'
auth_endpoint = '/auth/login.json'
get_own_goods_endpoint = '/api/v2/licenseSale/getOwnGoods'
save_order_endpoint = '/api/v2/licenseSale/saveOrder'
user_payment_page_endpoint = '/api/v2/licenseSale/userPaymentPage'
get_users_with_goods_endpoint = '/api/v2/licenseSale/getUsersWithGoods'


def auth(auth_data):
    response = httpx.post(base_url + auth_endpoint, json=auth_data)
    token = response.json().get('token')
    headers = {'auth-token': token}
    return headers


async def auth_and_check_goods(user_id, email, password):
    auth_data = {
        'userName': email,
        'userPassword': password
    }
    token = check_token_in_db(user_id)

    if not token:
        headers = auth(auth_data)
        token = headers.get('auth-token')
        write_token_to_db(user_id, token)
    else:
        headers = {'auth-token': token}

    user_exists = check_user_in_db(user_id)

    if not user_exists:
        add_user(user_id, email)

    response = httpx.post(base_url + get_own_goods_endpoint, headers=headers)
    return response.json()


