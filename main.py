import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 放弃不可靠的直接搜索，改用“聚合站”嗅探
EXTERNAL_AGGREGATORS = [
    "https://raw.githubusercontent.com/freefq/free/master/v2ray", # 这是一个中转大池
    "https://gitlab.com/free99/free/-/raw/master/clash",         # 跨平台稳定源
    "https://v2cross.com/archives/1834",                         # 典型的非 GitHub 博客源
]

def search_github(query):
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in res.get('items', [])]
    except: return []

def search_external_web():
    """从已知的聚合博客或公共页面嗅探链接"""
    links = []
    # 模拟高仿真浏览器环境
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    
    # 我们不仅搜 YAML，还搜那些可能是转换器的地址
    pattern = r'https?://[^\s<>"]+/(?:sub|clash|config|download)[^\s<>"]+'
    
    for url in EXTERNAL_AGGREGATORS:
        try:
            r = requests.get(url, timeout=20, headers=headers, verify=False)
            if r.status_code == 200:
                found = re.findall(pattern, r.text)
                # 排除 GitHub 链接，确保抓到的是“外面”的
                links.extend([f for f in found if "github" not in f.lower()])
        except: continue
    return list(set(links))

def verify(url):
    try:
        # 强制使用 Clash 客户端头，有些源会拦截普通浏览器
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        r = requests.get(url, timeout=25, headers=headers, verify=False, allow_redirects=True)
        if r.status_code == 200:
            text = r.text
            # YAML 或 Base64 判定
            if any(k in text for k in ["proxies:", "proxy-groups:"]):
                return url
            try:
                decoded = base64.b64decode(text[:500]).decode('utf-8', errors='ignore')
                if any(k in decoded for k in ["proxies", "node", "Proxy"]):
                    return url
            except: pass
    except: pass
    return None

def main():
    pool = []
    
    # 阶段 A: GitHub
    gh = search_github("clash 2026 extension:yaml")
    print(f"📡 GitHub 引擎: {len(gh)}")
    pool.extend(gh)
    
    # 阶段 B: 外部聚合嗅探 (取代失败的 TG/GL 搜索)
    ext = search_external_web()
    print(f"📡 外部嗅探 (非 GitHub): {len(ext)}")
    pool.extend(ext)
    
    unique_pool = list(set(pool))
    print(f"🧪 混合候选池: {len(unique_pool)}")

    with ThreadPoolExecutor(max_workers=20) as exe:
        valid_links = [r for r in exe.map(verify, unique_pool) if r]

    print(f"✅ 最终有效: {len(valid_links)}")

    # 写入 README
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 全平台节点监控报告\n\n")
        f.write(f"### ✅ 发现有效订阅 ({len(valid_links)} 个)\n\n")
        for link in valid_links:
            # 标记身份，让你一眼看出有没有非 GitHub 的
            mark = " 🔥 [外部源]" if "github" not in link.lower() else ""
            f.write(f"- `{link}`{mark}\n")

if __name__ == "__main__":
    main()
