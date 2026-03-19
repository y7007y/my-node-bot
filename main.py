import requests
import re
import os
import datetime
from concurrent.futures import ThreadPoolExecutor

GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 更加宽泛的搜索词，去掉具体的日期限制
SEARCH_QUERIES = [
    "clash subscription extension:yaml",
    "clash nodes 2026 extension:yaml",
    "githubusercontent.com/filter/config.yaml",
    "今日更新 clash"
]

def search_github(query):
    # sort=indexed & order=desc 确保拿到的是最新被 GitHub 收录的内容
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        print(f"🔎 搜索 [{query}]: 找到 {len(items)} 条候选")
        # 转换为原始文件下载链接
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except:
        return []

def verify(url):
    """深度验证：不仅看状态码，还要看内容是否真是 Clash 配置"""
    try:
        r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            text = r.text
            # 检查特征字段
            if any(key in text for key in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
    except:
        pass
    return None

def main():
    all_urls = []
    for q in SEARCH_QUERIES:
        all_urls.extend(search_github(q))
    
    unique_urls = list(set(all_urls))
    print(f"🧪 开始验证 {len(unique_urls)} 个链接...")

    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_urls) if r]

    # 写入结果
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# 🚀 自动化节点监控汇报\n\n")
        f.write(f"> 更新于: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        if valid_links:
            f.write(f"### ✅ 发现有效订阅 ({len(valid_links)}个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 今日暂无新发现\n\n可能原因：API 索引延迟，建议尝试手动触发或增加搜索关键词。")

if __name__ == "__main__":
    main()
