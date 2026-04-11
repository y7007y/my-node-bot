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
    # 改用更底层的特征词，避开平台敏感词检测
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        # 增加随机延时防止被秒封
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            return [item.get('raw_url') for item in data if 'raw_url' in item]
    except: pass
    return []

def search_telegram():
    links = []
    # 2026年更强的 UA 和参数模拟
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://google.com'
    }
    
    # 增加几个备用频道
    channels = ["clash_nodes", "v2ray_free", "Clash_Node_Share", "clash_subscription_free", "clashnode"]
    
    # 匹配模式：寻找各种可能的订阅地址特征
    pattern = r'https?://(?:[a-zA-Z0-9-]+\.)+[a-z]{2,6}/(?:sub|clash|config|api|v2ray)/[^\s<>"]+'
    
    for c in channels:
        try:
            # 加上 /s/ 并强制添加一个随机参数绕过缓存
            url = f"https://t.me/s/{c}?before={datetime.datetime.now().microsecond}"
            r = requests.get(url, timeout=15, headers=headers)
            
            # 如果返回的内容太短，说明被屏蔽了，尝试匹配正文
            content = r.text
            if "web_app_open_tg_link" in content:
                print(f"⚠️ Telegram {c} 触发了 JS 校验，尝试暴力提取...")
                
            found = re.findall(pattern, content)
            # 过滤掉 Telegram 自身的链接
            valid_found = [f for f in found if not any(x in f for x in ['t.me/', 'telegram.org', 'tg://'])]
            links.extend(valid_found)
        except: continue
    
    print(f"📡 Telegram 引擎最终发现候选: {len(links)}")
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
