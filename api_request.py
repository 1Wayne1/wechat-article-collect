import requests
import dotenv
import os

dotenv.load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

def get_account_info(keyword):
    url = "https://exporter.wxdown.online/api/v1/account"

    headers = {
        "Authorization": API_TOKEN,  # 常见格式
        "Content-Type": "application/json"
    }

    params = {"keyword": keyword}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


def get_articles(account_fake_id, begin, size):
    url = "https://exporter.wxdown.online/api/v1/article"

    headers = {
        "Authorization": API_TOKEN,  # 常见格式
        "Content-Type": "application/json"
    }

    params = {"fakeid": account_fake_id, "begin": begin, "size": size}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None


if __name__ == "__main__":
    # result = get_account_info()
    result = get_articles("MzIxMTExMTcxNQ==")
    if result:
        print(result)
