def search_web_general():
    """从一些公共聚合页面或搜索引擎抓取"""
    urls = []
    # 策略：抓取一些已知的订阅转换后端或节点分享页的特征
    search_sites = [
        "https://google.com/search?q=clash+subscription+yaml+2026", # 需处理反爬
        "https://bing.com/search?q=clash+config+yaml",
    ]
    # 实际上，直接抓取 Telegram 频道的网页版预览更有效
    tg_channels = [
        "https://t.me/s/clash_nodes", 
        "https://t.me/s/v2ray_free"
    ]
    # 使用正则匹配这些页面里的 https 链接
    return urls
