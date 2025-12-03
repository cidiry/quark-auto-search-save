import requests
import time
import random
import json

# API Constants
SEARCH_API = 'https://so.252035.xyz/api/search'
QUARK_API_BASE = 'https://drive-m.quark.cn/1/clouddrive/share/sharepage'
QUARK_USER_API = 'https://pan.quark.cn/account/info'


def format_cookie(cookie_str):
    """Clean up cookie string"""
    if not cookie_str:
        return ""
    return cookie_str.replace("Cookie:", "").replace("cookie:", "").strip()


def get_headers(cookie):
    """Generate headers with cookie"""
    return {
        "Cookie": format_cookie(cookie),
        "Content-Type": "application/json",
        "Referer": "https://pan.quark.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


def check_user(cookie):
    """
    Verify cookie validity
    Returns: (bool, user_info_dict or error_message)
    """
    url = f"{QUARK_USER_API}?fr=pc&platform=pc"
    try:
        response = requests.get(url, headers=get_headers(cookie))
        data = response.json()

        # Check if nickname exists to confirm validity
        if data.get("success") and data.get("data", {}).get("nickname"):
            return True, data["data"]
        else:
            return False, "Cookie 无效或已过期"
    except Exception as e:
        return False, str(e)


def search_resources(keyword):
    """
    Search for resources
    Returns: list of resources
    """
    url = f"{SEARCH_API}?kw={keyword}&cloud_types=quark"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("merged_by_type", {}).get("quark", [])
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []


def extract_pwd_id(url):
    """Extract pwd_id from quark url"""
    try:
        if "/s/" in url:
            return url.split("/s/")[1].split("?")[0]
        return None
    except:
        return None


def check_resource_validity(pwd_id, cookie, passcode=""):
    """
    Step 1: Check if resource is valid and get stoken
    Returns: (bool, stoken or error_message)
    """
    url = f"{QUARK_API_BASE}/token?pr=ucpro&fr=h5"
    payload = {
        "pwd_id": pwd_id,
        "passcode": passcode
    }

    try:
        response = requests.post(url, json=payload, headers=get_headers(cookie))
        data = response.json()

        if data.get("status") == 200 and data.get("data", {}).get("stoken"):
            return True, data["data"]["stoken"]
        else:
            return False, data.get("message", "Resource Invalid")
    except Exception as e:
        return False, str(e)


def save_resource(pwd_id, stoken, cookie):
    """
    Step 2: Save resource to drive
    Returns: (bool, message)
    """
    dt = int(random.uniform(1, 5) * 60 * 1000)
    t = time.time()
    url = f"{QUARK_API_BASE}/save?pr=ucpro&fr=pc&uc_param_str=&__dt={dt}&__t={t}"

    payload = {
        "pdir_fid": "0",  # Root directory
        "pdir_save_all": True,
        "pwd_id": pwd_id,
        "scene": "link",
        "stoken": stoken,
        "to_pdir_fid": "0"
    }

    try:
        response = requests.post(url, json=payload, headers=get_headers(cookie))
        data = response.json()

        if data.get("status") == 200:
            return True, "Success"
        else:
            return False, data.get("message", "Save Failed")
    except Exception as e:
        return False, str(e)
