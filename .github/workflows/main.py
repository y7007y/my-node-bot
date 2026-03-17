import requests
import datetime
import os
from concurrent.futures import ThreadPoolExecutor

# 配置区
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN") # 从环境变量读取Token，安全第一
KEYWORDS = ["今日高速节点", "Clash 订阅", "高速 M/S"]

def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def search_github(keyword):
    today_str = datetime.datetime.now().strftime("%m月%d日")
    query = f"{today_str} {keyword} extension:yaml"
    url = f"https://api.github.com/search/code?q={query}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in res.get('items', [])]
    except:
        return []

def verify(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and "proxies:" in r.text:
            return url
    except:
        pass
    return None

def main():
    all_links = []
    for kw in KEYWORDS:
        all_links.extend(search_github(kw))
    
    unique_links = list(set(all_links))
    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_links) if r]
    
    # 写入结果到 README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# 📅 今日有效节点汇总 ({get_today()})\n\n")
        f.write("> 自动更新时间：北京时间每天上午\n\n")
        if valid_links:
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("今日暂未搜索到有效新链接。")

if __name__ == "__main__":
    main()
