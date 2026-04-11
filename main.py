import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 调整策略：让搜索更模糊，抓取更激进
GH_QUERIES = ["clash 2026 extension:yaml", "subscription extension:yaml"]
GL_KEYWORDS = ["proxies:", "v2ray", "ss-config","node"] # 搜索内容特征而非标题
TG_CHANNELS = ["clash_nodes", "v2ray_free", "Clash_Node_Share", "clash_subscription_free"]

def search_github(query):
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except: return []

def search_gitlab(kw):
    # 尝试直接从 Snippets 的原始数据搜索
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        res = requests.get(url, timeout=15).json()
        return [item.get('raw_url') for item in res if 'raw_url' in item]
    except: return []

def search_telegram():
    links = []
    # 2026年更激进的正则：寻找类似订阅转换或节点的 URL
    pattern = r'https?://[^\s<>"]+/(?:sub|clash|config|download|api)[^\s<>"]*'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for c in TG_CHANNELS:
        try:
            # 加上时间戳参数尝试绕过 Telegram 缓存
            r = requests.get(f"https://t.me/s/{c}?{datetime.datetime.now().timestamp()}", timeout=15, headers=headers)
            found = re.findall(pattern, r.text)
            # 过滤掉干扰项
            links.extend([f for f in found if not any(x in f for x in ['t.me', 'tg://', 'google', 'apple'])])
        except: continue
    print(r.text[:500])
    return list(set(links))

def verify(url):
    if not url: return None
    try:
        # 伪装成真正的 Clash 客户端，非常重要！
        headers = {'User-Agent': 'ClashforWindows/0.19.0'}
        r = requests.get(url, timeout=20, headers=headers, verify=False) # 忽略SSL错误
        if r.status_code == 200:
            content = r.text.strip()
            # 1. 直接 YAML 判定
            if any(k in content for k in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            # 2. Base64 全文判定（改进）
            try:
                # 尝试解码并检查关键字段
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                if any(k in decoded for k in ["proxies", "node", "Proxy", "cipher", "type:"]):
                    return url
            except: pass
    except: pass
    return None

def main():
    pool = []
    
    # --- 阶段性汇总并打印日志，方便你在 Actions 日志查看 ---
    gh_res = []
    for q in GH_QUERIES: gh_res.extend(search_github(q))
    print(f"📡 GitHub 抓取到: {len(gh_res)}")
    pool.extend(gh_res)

    gl_res = []
    for kw in GL_KEYWORDS: gl_res.extend(search_gitlab(kw))
    print(f"📡 GitLab 抓取到: {len(gl_res)}")
    pool.extend(gl_res)

    tg_res = search_telegram()
    print(f"📡 Telegram 抓取到: {len(tg_res)}")
    pool.extend(tg_res)

    unique_pool = list(set(pool))
    print(f"🧪 总计候选池: {len(unique_pool)}")

    with ThreadPoolExecutor(max_workers=15) as exe:
        valid_links = [r for r in exe.map(verify, unique_pool) if r]

    print(f"✅ 验证通过总数: {len(valid_links)}")

    # 写入 README (确保冒号没丢)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 全平台节点自动汇报\n\n")
        f.write(f"> 最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        if valid_links:
            f.write(f"### ✅ 本次有效发现 ({len(valid_links)}个)\n\n")
            for link in valid_links:
                # 标记非 GitHub 的来源，方便观察
                source_tag = " [Web/TG]" if "github" not in link.lower() else ""
                f.write(f"- `{link}`{source_tag}\n")
        else:
            f.write("### 📭 今日暂无发现\n")

if __name__ == "__main__":
    main()
