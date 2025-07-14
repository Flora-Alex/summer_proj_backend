from django.test import TestCase

# Create your tests here.
import requests

def test_website(url):
    try:
        response = requests.get(url)
        # 检查响应状态码
        if response.status_code == 200:
            print(f"网站 {url} 可用，状态码: {response.status_code}")
        else:
            print(f"网站 {url} 不可用，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"访问网站 {url} 时发生错误: {e}")

if __name__ == "__main__":
    # 替换为你的Django网站的URL
    test_website("127.0.0.1:8000/")
