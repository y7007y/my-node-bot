import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 配置
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")
SEARCH_QUERIES = [
    "clash subscription extension:yaml",
    "proxies: name extension:yaml"
]

def search_github(query):
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            items = res.json().get('items', [])
            return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except: pass
    return []

def verify_and_score(url):
    """验证并优选：返回 (URL, 节点数)"""
    try:
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        r = requests.get(url, timeout=12, headers=headers, verify=False)
        if r.status_code == 200 and len(r.content) > 1024: # 优选：文件必须大于 1KB
            content = r.text
            
            # 如果是 Base64，先解码再判断
            if not "proxies:" in content:
                try:
                    content = base64.b64decode(content).decode('utf-8', errors='ignore')
                except: pass
            
            # 优选核心逻辑：计算节点关键字 'name:' 出现的次数
            node_count = content.count('name:')
            if node_count >= 5: # 优选：节点数大于等于 5 个才要
                return (url, node_count)
    except: pass
    return None

def main():
    print(f"🚀 精选模式启动...")
    
    raw_pool = []
    for q in SEARCH_QUERIES:
        raw_pool.extend(search_github(q))
    
    unique_pool = list(set(raw_pool))
    print(f"🧪 原始候选: {len(unique_pool)} 个，开始深度优选...")

    # 并行验证与打分
    results = []
    with ThreadPoolExecutor(max_workers=10) as exe:
        results = [r for r in exe.map(verify_and_score, unique_pool) if r]

    # 按节点数量从大到小排序
    results.sort(key=lambda x: x[1], reverse=True)
    
    # 只取前 20 个最肥的源
    final_list = results[:20]

    print(f"✅ 优选完成，筛选出 {len(final_list)} 个高质量源")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 💎 Clash 高质量节点优选报告\n\n")
        f.write(f"> **更新时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n")
        f.write(f"> **筛选标准**: 文件 > 1KB 且 节点数 ≥ 5\n\n")
        
        if final_list:
            f.write("| 排名 | 订阅链接 | 节点估算 | \n")
            f.write("| :--- | :--- | :--- | \n")
            for i, (link, count) in enumerate(final_list, 1):
                f.write(f"| {i} | `{link}` | {count} 个 |\n")
        else:
            f.write("### 📭 今日暂无高质量发现\n")

    print("🎉 优选报告已生成")

if __name__ == "__main__":
    main()
