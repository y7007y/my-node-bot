import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 配置：从 GitHub Secrets 获取令牌
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 精选搜索词：只选出货率最高的
SEARCH_QUERIES = [
    "clash subscription extension:yaml",
    "clash 2026 extension:yaml",
    "proxies: name extension:yaml"
]

def search_github(query):
    """利用 GitHub API 搜索代码"""
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            items = res.json().get('items', [])
            # 将 HTML 链接转换为 Raw 原始文件链接
            return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except:
        pass
    return []

def verify(url):
    """验证链接是否有效"""
    try:
        # 伪装成 Clash 客户端
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        r = requests.get(url, timeout=15, headers=headers, verify=False)
        if r.status_code == 200:
            content = r.text
            # 只要包含 proxies 关键字就认为是一个有效的配置
            if "proxies:" in content or "proxy-groups:" in content:
                return url
            # 兼容 Base64 格式
            try:
                decoded = base64.b64decode(content[:500]).decode('utf-8', errors='ignore')
                if "proxies" in decoded or "node" in decoded:
                    return url
            except:
                pass
    except:
        pass
    return None

def main():
    print(f"🚀 任务启动: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 搜集候选
    raw_pool = []
    for q in SEARCH_QUERIES:
        found = search_github(q)
        print(f"🔎 搜索 [{q}] 发现: {len(found)} 个候选")
        raw_pool.extend(found)
    
    # 2. 去重
    unique_pool = list(set(raw_pool))
    print(f"🧪 汇总去重后共: {len(unique_pool)} 个链接，开始验证...")

    # 3. 多线程验证 (提升速度)
    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_pool) if r]

    print(f"✅ 最终有效链接: {len(valid_links)} 个")

    # 4. 写入 README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 📡 Clash 节点自动化监控 (GitHub 专版)\n\n")
        f.write(f"> **最近更新**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        f.write("此列表由 GitHub Actions 自动搜索并验证生成。仅供技术交流，请勿用于非法用途。\n\n")
        
        if valid_links:
            f.write(f"### ✅ 当前有效订阅 ({len(valid_links)} 个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 暂无发现\n\n请检查 API 配额或尝试更换搜索词。")

    print("🎉 同步完成！")

if __name__ == "__main__":
    main()
