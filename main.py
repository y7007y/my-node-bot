import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 配置 GitHub Token
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 搜集策略配置
# GitHub 专用语法
GH_QUERIES = ["clash subscription extension:yaml", "clash 2026 extension:yaml"]
# GitLab 通用特征词 (寻找 YAML 内部关键字比寻找标题更准)
GL_KEYWORDS = ["proxies: name", "proxy-groups", "clash subscription"]
# Telegram 公开频道列表
TG_CHANNELS = ["clash_nodes", "v2ray_free", "Clash_Node_Share", "clash_subscription_free"]

def search_github(query):
    """GitHub 代码搜索"""
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except Exception as e:
        print(f"❌ GitHub 引擎故障: {e}")
        return []

def search_gitlab(kw):
    """GitLab Snippets 搜索"""
    url = f"https://gitlab.com/api/v4/snippets/public?search={kw}"
    try:
        res = requests.get(url, timeout=15).json()
        # GitLab API 返回的是 snippet 列表，直接提取 raw_url
        links = [item.get('raw_url') for item in res if 'raw_url' in item]
        if links:
            print(f"📡 GitLab [{kw}]: 发现 {len(links)} 个候选")
        return links
    except:
        return []

def search_telegram():
    """Telegram 网页版预览嗅探"""
    links = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    # 匹配通用的订阅 URL 模式
    pattern = r'https?://[^\s<>"]+/(?:sub|cl|config|data)[^\s<>"]*'
    
    for c in TG_CHANNELS:
        try:
            r = requests.get(f"https://t.me/s/{c}", timeout=10, headers=headers)
            # 提取所有疑似链接
            found = re.findall(pattern, r.text)
            # 过滤掉一些明显的非配置文件链接
            found = [f for f in found if not any(x in f for x in ['tg://', 't.me', 'google.com', 'github.com'])]
            links.extend(found)
        except:
            continue
    print(f"📡 Telegram 频道: 搜集到 {len(links)} 个候选")
    return links

def verify(url):
    """深度验证：支持 YAML 和 Base64"""
    if not url: return None
    try:
        # 模拟真实客户端，防止被反爬
        headers = {
            'User-Agent': 'ClashforWindows/0.19.0',
            'Accept': '*/*'
        }
        r = requests.get(url, timeout=10, headers=headers, allow_redirects=True, verify=False)
        if r.status_code == 200:
            text = r.text
            # 判定 A: 包含 YAML 特征
            if any(k in text for k in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            
            # 判定 B: 尝试 Base64 解码检查内容
            try:
                # 剔除可能的空格换行再尝试解码
                raw_content = text.strip()
                decoded = base64.b64decode(raw_content[:200]).decode('utf-8', errors='ignore')
                if any(k in decoded for k in ["proxies", "node", "Proxy", "cipher"]):
                    return url
            except:
                pass
    except:
        pass
    return None

def main():
    start_time = datetime.datetime.now()
    all_raw_urls = []
    
    print(f"🚀 任务启动于: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # --- 阶段 1: GitHub 引擎 ---
    print("🔎 正在检索 GitHub...")
    for q in GH_QUERIES:
        all_raw_urls.extend(search_github(q))
        
    # --- 阶段 2: GitLab 引擎 ---
    print("🔎 正在检索 GitLab...")
    for kw in GL_KEYWORDS:
        all_raw_urls.extend(search_gitlab(kw))
        
    # --- 阶段 3: Telegram 引擎 ---
    print("🔎 正在从 Telegram 频道预览提取...")
    all_raw_urls.extend(search_telegram())
    
    # 汇总去重
    unique_urls = list(set(all_raw_urls))
    print(f"🧪 初始去重池共计: {len(unique_urls)} 个，开始并行验证...")
    
    # --- 阶段 4: 并发验证 ---
    with ThreadPoolExecutor(max_workers=15) as exe:
        valid_links = [r for r in exe.map(verify, unique_urls) if r]
    
    print(f"✅ 验证通过: {len(valid_links)} 个")
    
    # --- 阶段 5: 写入报告 ---
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 全平台节点自动汇报 (2026 版)\n\n")
        f.write(f"> **最近更新**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n")
        f.write(f"> **数据源**: GitHub, GitLab, Telegram\n\n")
        
        # 注意这里：末尾必须有冒号 :
        if valid_links:
            f.write(f"### ✅ 本次发现有效订阅 ({len(valid_links)} 个)\n\n")
            for link in valid_links:
                f.write(f"- `{link}`\n")
        else:
            f.write("### 📭 今日暂无新发现\n")
