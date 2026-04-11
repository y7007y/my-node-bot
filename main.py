import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 分开定义关键词，不要混用
GH_QUERIES = ["clash subscription extension:yaml", "clash 2026 extension:yaml"]
GL_KEYWORDS = ["clash subscription", "clash config", "clash 订阅"]

def search_github(query):
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except Exception as e:
        print(f"❌ GitHub 报错: {e}")
        return []

def search_gitlab(kw):
    """GitLab 专项：移除 GitHub 后缀"""
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        # GitLab API 返回的是一个列表
        res = requests.get(url, timeout=15).json()
        links = [item.get('raw_url') for item in res if 'raw_url' in item]
        print(f"📡 GitLab [{kw}]: 抓取到 {len(links)} 条")
        return links
    except Exception as e:
        print(f"❌ GitLab 报错: {e}")
        return []

def search_telegram():
    """Telegram 专项：提取网页版预览链接"""
    channels = ["clash_nodes", "v2ray_free", "Clash_Node_Share", "clash_subscription_free"]
    links = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    for c in channels:
        try:
            r = requests.get(f"https://t.me/s/{c}", timeout=10, headers=headers)
            # 匹配包含 yaml, txt, conf 的 https 链接
            found = re.findall(r'https?://[^\s<>"]+\.(?:yaml|txt|conf|ini)', r.text)
            links.extend(found)
        except:
            continue
    print(f"📡 Telegram: 抓取到 {len(links)} 条候选链接")
    return links

def verify(url):
    """强化验证：识别 Base64"""
    if not url: return None
    try:
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        r = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
        if r.status_code == 200:
            text = r.text
            # 识别 YAML
            if any(k in text for k in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            # 识别 Base64
            try:
                decoded = base64.b64decode(text[:100]).decode('utf-8')
                if any(k in decoded for k in ["proxies", "node", "Proxy"]):
                    return url
            except: pass
    except: pass
    return None

def main():
    all_raw_urls = []
    
    # 1. GitHub 搜集
    print("🚀 启动 GitHub 引擎...")
    for q in GH_QUERIES:
        all_raw_urls.extend(search_github(q))
        
    # 2. GitLab 搜集
    print("🚀 启动 GitLab 引擎...")
    for kw in GL_KEYWORDS:
        all_raw_urls.extend(search_gitlab(kw))
        
    # 3. Telegram 搜集
    print("🚀 启动 Telegram 引擎...")
    all_raw_urls.extend(search_telegram())
    
    unique_urls = list(set(all_raw_urls))
    print(f"🧪 汇总池去重后总数: {len(unique_urls)}")
    
    # 4. 验证
    with ThreadPoolExecutor(max_workers=10) as exe:
        valid_links = [r for r in exe.map(verify, unique_urls) if r]
    
    print(f"✅ 最终有效链接: {len(valid_links)}")
    
    # 5. 写入 README.md
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# 🚀 全平台节点自动汇报\n\n")
        f.write(f"> 最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        if valid_links:
            f.write(f"### ✅ 本次发现 ({len(valid_links)}个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 今日暂无发现\n\n检查建议：尝试更换 Telegram 频道或 GitLab 关键词。")

if __name__ == "__main__":
    main()
