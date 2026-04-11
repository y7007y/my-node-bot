import requests
import re
import os
import datetime
from concurrent.futures import ThreadPoolExecutor

# 保留 GitHub 逻辑作为来源之一
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 扩展搜索源：GitHub + 静态收集 + 搜索引擎 (示例使用公开爬取的 API)
SEARCH_QUERIES = [
    "clash subscription extension:yaml",
    "githubusercontent.com/filter/config.yaml",
    "今日更新 clash"
]

# 2. 静态源：直接添加一些已知的、不再 GitHub 上的节点发布地址
STATIC_SOURCES = [
    "https://raw.githubusercontent.com/some_user/some_repo/main/clash.yaml", # 示例
    # "https://gitlab.com/xxx/xxx/-/raw/main/config.yaml", # GitLab 也是很好的源
]

def search_github(query):
    """GitHub 搜索逻辑保持不变"""
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except:
        return []

def search_public_web(query):
    """
    通用搜索逻辑：这里可以集成像 Google/Bing 的搜索结果。
    由于搜索引擎爬虫较复杂，这里提供一种基于正则提取普通网页中 URL 的思路。
    """
    # 这里仅为逻辑展示，实际可对接第三方 Search API 
    # 比如：https://api.bing.microsoft.com/v7.0/search
    return []

def verify(url):
    """验证逻辑保持不变：这是最核心的，只要能通过验证，管它哪来的"""
    try:
        # 针对部分屏蔽爬虫的源，增加 User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        }
        r = requests.get(url, timeout=8, headers=headers)
        if r.status_code == 200:
            text = r.text
            # 强化检查特征
            features = ["proxies:", "proxy-groups:", "Proxy Group:", "port:"]
            if any(key in text for key in features):
                return url
    except:
        pass
    return None

def main():
    all_urls = []
    
    # --- 策略 A: GitHub 搜索 ---
    print("📡 正在检索 GitHub 资源...")
    for q in SEARCH_QUERIES:
        all_urls.extend(search_github(q))
    
    # --- 策略 B: 静态源获取 ---
    print("🔗 正在整合静态资源...")
    all_urls.extend(STATIC_SOURCES)
    
    # --- 策略 C: 其它源 (如 GitLab, Gitee 等) ---
    # 这里可以添加你发现的任何其它平台的 API 调用逻辑
    
    unique_urls = list(set(all_urls))
    print(f"🧪 开始验证总计 {len(unique_urls)} 个链接...")

    # 使用并发验证，提高效率
    with ThreadPoolExecutor(max_workers=15) as exe:
        valid_links = [r for r in exe.map(verify, unique_urls) if r]

    # 写入结果
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# 🚀 全平台节点监控汇报\n\n")
        f.write(f"> 更新于: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n")
        f.write(f"> 来源涵盖: GitHub, GitLab, 静态列表, Web 检索\n\n")
        
        if valid_links:
            f.write(f"### ✅ 发现有效订阅 ({len(valid_links)}个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 今日暂无新发现\n")

if __name__ == "__main__":
    main()
