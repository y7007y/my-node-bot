# 确保在 main.py 的开头导入了所需的库
import requests
import os
# ... 其他导入

# 检查环境变量是否读取成功（调试用）
token = os.environ.get("MY_GITHUB_TOKEN")
if not token:
    print("⚠️ 警告: 未找到 MY_GITHUB_TOKEN，搜索功能将受限")
import requests
import re
import os
import datetime
import base64
from concurrent.futures import ThreadPoolExecutor

# 配置
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")

# 1. 更加通用的搜索词（不再局限于 GitHub 语法）
UNIVERSAL_KEYWORDS = ["clash subscription", "clash config yaml", "节点更新", "free nodes"]
GITHUB_SPECIFIC_QUERIES = ["clash subscription extension:yaml", "clash nodes 2026 extension:yaml"]

# 2. 静态/第三方聚合源（可以手动添加已知的地址）
STATIC_SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2ray", # 示例静态源
]

def search_github(query):
    """GitHub 搜索逻辑"""
    url = f"https://api.github.com/search/code?q={query}&sort=indexed&order=desc"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        items = res.get('items', [])
        # 转换为原始文件链接
        return [item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") for item in items]
    except Exception as e:
        print(f"❌ GitHub 搜索异常: {e}")
        return []

def search_gitlab(query):
    """GitLab 公开代码片段搜索"""
    # GitLab 的 Snippets API 不需要 Token 即可搜索公开内容
    url = f"https://gitlab.com/api/v4/snippets/public?search={query}"
    try:
        res = requests.get(url, timeout=15).json()
        # GitLab API 直接返回 raw_url
        return [item.get('raw_url') for item in res if 'raw_url' in item]
    except Exception as e:
        print(f"❌ GitLab 搜索异常: {e}")
        return []

def search_telegram_web():
    """从公开的 Telegram 频道网页版嗅探链接"""
    channels = ["clash_nodes", "v2ray_free", "SSRSUB"] # 这里可以添加更多频道名
    urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    for channel in channels:
        try:
            r = requests.get(f"https://t.me/s/{channel}", timeout=10, headers=headers)
            # 使用正则提取网页中符合 URL 格式的文本
            found = re.findall(r'https?://[^\s<>"]+\.yaml', r.text)
            urls.extend(found)
        except:
            continue
    return urls

def verify(url):
    """深度验证：支持 YAML 特征识别和 Base64 解码检查"""
    if not url: return None
    headers = {
        'User-Agent': 'ClashforWindows/0.19.0', # 模拟 Clash 客户端，规避部分屏蔽
        'Accept': '*/*'
    }
    try:
        r = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
        if r.status_code == 200:
            text = r.text
            # 逻辑 A: YAML 特征
            if any(key in text for key in ["proxies:", "proxy-groups:", "Proxy Group:"]):
                return url
            # 逻辑 B: 尝试 Base64 解码检查 (很多订阅链接返回的是 Base64)
            try:
                decoded = base64.b64decode(text[:100]).decode('utf-8')
                if "proxies" in decoded or "node" in decoded:
                    return url
            except:
                pass
    except:
        pass
    return None

def main():
    raw_urls = []

    # --- 搜集阶段 ---
    print("🔎 正在从 GitHub 搜集...")
    for q in GITHUB_SPECIFIC_QUERIES:
        raw_urls.extend(search_github(q))

    print("🔎 正在从 GitLab 搜集...")
    for kw in UNIVERSAL_KEYWORDS:
        raw_urls.extend(search_gitlab(kw))

    print("🔎 正在从
