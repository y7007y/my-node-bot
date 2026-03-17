import requests
import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor

# 配置区
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")
# 这里的关键词去掉了日期，日期会在下面代码中动态生成
BASE_KEYWORDS = ["clash订阅"]

def get_dates():
    """获取今天和昨天的日期，增加命中率"""
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    return [today.strftime("%m月%d日"), yesterday.strftime("%m月%d日"), today.strftime("%Y-%m-%d")]

def search_github(keyword, date_str):
    """搜索特定日期和关键词"""
    query = f"{date_str} {keyword} extension:yaml"
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            items = data.get('items', [])
            print(f"🔍 搜索 [{date_str} {keyword}]: 发现 {len(items)} 个潜在结果")
            return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
        else:
            print(f"❌ 搜索出错 [{keyword}]: {res.status_code} - {res.text}")
            return []
    except Exception as e:
        print(f"⚠️ 网络请求失败: {e}")
        return []

def verify(url):
    """验证链接是否有效"""
    try:
        # 增加 headers 模拟浏览器，防止被某些服务器拒绝
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200 and ("proxies:" in r.text or "proxy-groups:" in r.text):
            return url
    except:
        pass
    return None

def main():
    all_raw_urls = []
    dates = get_dates()
    
    print(f"🚀 开始任务，尝试日期范围: {dates}")
    
    for d in dates:
        for kw in BASE_KEYWORDS:
            links = search_github(kw, d)
            all_raw_urls.extend(links)
            time.sleep(1) # 稍微停顿，避免触发速率限制
    
    unique_links = list(set(all_raw_urls))
    print(f"📡 正在验证 {len(unique_links)} 个唯一链接的有效性...")
    
    valid_links = []
    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_links) if r]
    
    # 写入结果
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# 📅 自动搜寻节点汇报\n\n")
        f.write(f"> 最后更新时间 (UTC): {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if valid_links:
            f.write(f"### ✅ 今日找到的有效订阅 ({len(valid_links)}个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### ❌ 今日暂未搜索到有效新链接\n\n")
            f.write("原因可能是：\n1. GitHub 今日尚未索引到包含关键词的新代码。\n2. 搜索到的链接均已失效 (404/无法连接)。\n")

if __name__ == "__main__":
    main()
