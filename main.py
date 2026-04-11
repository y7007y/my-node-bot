import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 1. 关键词解耦：GitHub 用高级语法，其他平台用普通词
GITHUB_QUERIES = ["clash subscription extension:yaml", "nodes 2026 extension:yaml"]
GENERAL_KEYWORDS = ["clash 订阅", "clash config", "v2ray config"]

# 2. GitLab 搜索函数（确保不使用 GitHub 语法）
def search_gitlab(kw):
    # GitLab Snippets API 是获取“野外”节点的好地方
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        res = requests.get(url, timeout=10).json()
        # 提取 raw_url，这是直接可以下载的链接
        return [item.get('raw_url') for item in res if 'raw_url' in item]
    except:
        return []

# 3. Telegram 网页版探测（最快的更新源）
def search_telegram():
    # 爬取公开频道的网页预览，不需要登录，也不需要 API ID
    channels = ["clash_nodes", "v2ray_free", "Clash_Node_Share"]
    links = []
    for c in channels:
        try:
            r = requests.get(f"https://t.me/s/{c}", timeout=10)
            # 改进正则：抓取所有以 http 开头且看起来像配置文件的链接
            found = re.findall(r'https?://[^\s<>"]+\.(?:yaml|txt|conf)', r.text)
            links.extend(found)
        except:
            continue
    return links

# 4. 验证逻辑（必须包含 Base64 识别）
def verify(url):
    try:
        headers = {'User-Agent': 'ClashforWindows/0.19.0'} # 伪装成客户端
        r = requests.get(url, timeout=8, headers=headers)
        if r.status_code == 200:
            content = r.text
            # 情况 A：明文 YAML
            if any(k in content for k in ["proxies:", "proxy-groups:"]):
                return url
            # 情况 B：Base64 编码的订阅（非常多！）
            try:
                decoded = base64.b64decode(content[:100]).decode('utf-8')
                if "proxies" in decoded or "node" in decoded:
                    return url
            except:
                pass
    except:
        pass
    return None

def main():
    pool = []
    
    # --- GitHub 部分 ---
    for q in GITHUB_QUERIES:
        pool.extend(search_github(q)) # 沿用你之前的 search_github 函数
        
    # --- GitLab 部分 ---
    print("📡 正在扫描 GitLab...")
    for kw in GENERAL_KEYWORDS:
        pool.extend(search_gitlab(kw))
        
    # --- Telegram 部分 ---
    print("📡 正在扫描 Telegram 频道...")
    pool.extend(search_telegram())
    
    unique_pool = list(set(pool))
    print(f"🔍 汇总池总数: {len(unique_pool)}")

    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_pool) if r]

    # ... 写入 README.md 的逻辑保持不变 ...
