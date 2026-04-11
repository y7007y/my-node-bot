import requests
import re
import os
import datetime
import base64
import random
from concurrent.futures import ThreadPoolExecutor

# 配置
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 更加“狡猾”的搜索特征 (针对 GitLab)
GL_KEYWORDS = [
    "proxies:",          # YAML 核心特征
    "server: ",          # 节点服务器特征
    "cipher: ",          # 加密特征
    "type: vmess"        # 协议特征
]

# 2. Telegram 频道备选
TG_CHANNELS = ["clash_nodes", "v2ray_free", "Clash_Node_Share", "clashnode", "v2rayfree"]

# 3. 静态/第三方订阅源补丁 (当搜索引擎全部失效时的保底)
STATIC_PATCH = [
    "https://raw.githubusercontent.com/freefq/free/master/v2ray", 
    "https://gitlab.com/free99/free/-/raw/master/clash",
    # 你可以手动在此添加更多非 GitHub 的长期稳定链接
]

def search_github(query):
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except: return []

def search_gitlab(kw):
    """尝试通过 GitLab 的公开 API 进行代码检索"""
    # 模拟更随机的请求，避免被封
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return [item.get('raw_url') for item in r.json() if 'raw_url' in item]
    except: pass
    return []

def search_telegram():
    links = []
    # 2026 年最新 Headers 伪装
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache'
    }
    
    # 匹配规则：寻找一切可能是订阅链接的 URL
    pattern = r'https?://(?:[a-zA-Z0-9-]+\.)+[a-z]{2,6}/(?:sub|clash|config|v2ray|api|download)/[^\s<>"]+'
    
    for c in TG_CHANNELS:
        try:
            # 尝试通过随机参数绕过 Telegram 的 JS 校验
            url = f"https://t.me/s/{c}?v={random.randint(100, 999)}"
            r = requests.get(url, timeout=15, headers=headers)
            
            content = r.text
            # 暴力提取逻辑：不管有没有 JS 校验，强行搜寻页面中的 URL 字符串
            found = re.findall(pattern, content)
            # 过滤掉 Telegram 自身和已知的无效域名
            valid = [f for f in found if not any(x in f for x in ['t.me/', 'telegram.org', 'tg://', 'apple.com', 'google.com'])]
            links.extend(valid)
        except: continue
    return list(set(links))

def verify(url):
    if not url: return None
    try:
        # 伪装为 Clash 客户端，非常关键
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        # verify=False 解决 2026 年常见的 SSL 证书过期问题
        r = requests.get(url, timeout=20, headers=headers, verify=False, allow_redirects=True)
        if r.status_code == 200:
            text = r.text.strip()
            # YAML 特征识别
            if any(k in text for k in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            # Base64 识别 (全量检查)
            try:
                decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
                if any(k in decoded for k in ["proxies", "node", "Proxy", "cipher"]):
                    return url
            except: pass
    except: pass
    return None

def main():
    pool = []
    
    # 1. 抓取各路引擎
    gh = []
    for q in ["clash subscription extension:yaml", "clash 2026 extension:yaml"]:
        gh.extend(search_github(q))
    print(f"📡 GitHub 结果: {len(gh)}")
    pool.extend(gh)

    gl = []
    for kw in GL_KEYWORDS:
        gl.extend(search_gitlab(kw))
    print(f"📡 GitLab 结果: {len(gl)}")
    pool.extend(gl)

    tg = search_telegram()
    print(f"📡 Telegram 结果: {len(tg)}")
    pool.extend(tg)
    
    # 2. 加入静态补丁 (保底)
    print(f"📡 注入静态补丁: {len(STATIC_PATCH)}")
    pool.extend(STATIC_PATCH)

    # 3. 去重与验证
    unique_pool = list(set(pool))
    print(f"🧪 总候选池: {len(unique_pool)}")

    with ThreadPoolExecutor(max_workers=15) as exe:
        valid_links = [r for r in exe.map(verify, unique_pool) if r]

    print(f"✅ 最终有效结果: {len(valid_links)}")

    # 4. 写入报告
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 全平台节点自动化监控报告\n\n")
        f.write(f"> 最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n")
        f.write(f"> 来源: GitHub, GitLab (Snippets), Telegram (Web), Static Patch\n\n")
        
        if valid_links:
            f.write(f"### ✅ 发现有效订阅 ({len(valid_links)} 个)\n\n")
            for link in valid_links:
                # 标记来源类型
                tag = " [GitHub]" if "github" in link.lower() else " [External]"
                f.write(f"- `{link}`{tag}\n")
        else:
            f.write("### 📭 今日暂无发现\n")

if __name__ == "__main__":
    main()
