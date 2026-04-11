import requests
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 配置
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 通用搜索词（去掉 GitHub 专用语法，增加兼容性）
KEYWORDS = ["clash subscription", "clash config yaml", "节点更新"]

def search_github(query):
    # 仅在 GitHub 搜索时保留专用后缀
    github_q = f"{query} extension:yaml"
    url = f"https://api.github.com/search/code?q={github_q}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") 
                for item in res.get('items', [])]
    except Exception as e:
        print(f"❌ GitHub 搜索出错: {e}")
        return []

def search_gitlab(query):
    # GitLab Snippets 搜索（无需 Token 即可获取公开内容）
    url = f"https://gitlab.com/api/v4/snippets/public?search={query}"
    try:
        res = requests.get(url, timeout=10).json()
        return [item.get('raw_url') for item in res if 'raw_url' in item]
    except:
        return []

def verify(url):
    """深度验证逻辑"""
    if not url: return None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
        if r.status_code == 200:
            content = r.text
            # 兼容：纯 YAML 特征 或 Base64 编码特征
            if any(k in content for k in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            # 尝试 Base64 解码检查
            try:
                decoded = base64.b64decode(content[:100]).decode('utf-8')
                if "proxies" in decoded or "node" in decoded:
                    return url
            except: pass
    except: pass
    return None

def main():
    source_pool = []
    
    print("🚀 开始多源搜集...")
    for kw in KEYWORDS:
        # 汇总 GitHub 结果
        gh_results = search_github(kw)
        source_pool.extend(gh_results)
        
        # 汇总 GitLab 结果
        gl_results = search_gitlab(kw)
        source_pool.extend(gl_results)

    # 去重
    unique_sources = list(set(source_pool))
    print(f"🔍 原始抓取总数: {len(unique_sources)}，开始验证...")

    # 并发验证
    with ThreadPoolExecutor(max_workers=15) as exe:
        valid_links = [r for r in exe.map(verify, unique_sources) if r]

    # --- 关键：确保写入过程 ---
    print(f"📊 验证完成，有效链接: {len(valid_links)} 个")
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 全平台节点自动汇报\n\n")
        f.write(f"> **最后更新**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        
        if valid_links:
            f.write(f"### ✅ 本次发现 ({len(valid_links)} 个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 今日暂无新发现\n\n检查建议：\n1. 增加更多关键词\n2. 检查各平台 API 连通性\n")
            
    print("✅ README.md 写入完成")

if __name__ == "__main__":
    main()
