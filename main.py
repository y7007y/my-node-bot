def search_gitlab(query):
    # GitLab 的搜索接口
    url = f"https://gitlab.com/api/v4/snippets/public?search={query}"
    try:
        res = requests.get(url, timeout=15).json()
        urls = []
        for item in res:
            # 寻找原始文件链接
            raw_url = item.get('raw_url')
            if raw_url: urls.append(raw_url)
        return urls
    except:
        return []
