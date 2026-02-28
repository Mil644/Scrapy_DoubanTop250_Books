import scrapy
import re
from douban_top250_full.items import DoubanBookItem
from http.cookies import SimpleCookie

class Top250FullSpider(scrapy.Spider):
    name = "top250_full"
    allowed_domains = ["book.douban.com"]
    start_urls = ["https://book.douban.com/top250"]

    def parse_cookie_string(self, cookie_str):
        """
        将浏览器复制的 Cookie 字符串解析为字典格式
        """
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        # 遍历所有键值对，提取 cookie 名和值
        return {key: morsel.value for key, morsel in cookie.items()}

    def start_requests(self):
        """
        重写 start_requests 方法，为每个起始 URL 添加自定义 Cookie
        使用从浏览器获取的 Cookie 字符串模拟登录状态
        """
        # 从浏览器复制的 Cookie 字符串（示例）
        cookies_str = '复制的Cookie字符串'
        # 解析 Cookie 字符串为字典
        cookies_dict = self.parse_cookie_string(cookies_str)
        # 为每个起始 URL 生成带 Cookie 的请求
        for url in self.start_urls:
            yield scrapy.Request(url, cookies=cookies_dict, callback=self.parse)

    def parse(self, response):
        """
        解析 Top250 列表页，提取每本书的详情页 URL 和基本信息
        """
        # 定位每个书籍条目（每个条目在 <tr class="item"> 中）
        books = response.xpath('//tr[@class="item"]')
        for book in books:
            # 将当前页提取的数据暂存到 meta 中，传递给详情页回调
            meta = {}
            # 详情页 URL
            meta['detail_url'] = book.xpath('.//a[@title]/@href').get().strip()
            # 书名
            meta['title'] = book.xpath('.//a/@title').get().strip()
            # 短评（如果有）
            meta['quote'] = book.xpath('.//p[@class="quote"]/span/text()').get()
            if meta['quote']:
                meta['quote'] = meta['quote'].strip()
            else:
                meta['quote'] = 'None'
            # 评分
            meta['rating'] = book.xpath('.//span[@class="rating_nums"]/text()').get().strip()
            # 评价人数（包含在 <span class="pl"> 中，例如 (1245人评价)）
            meta['rating_num'] = book.xpath('.//span[@class="pl"]/text()').get()
            if meta['rating_num']:
                # 用正则提取数字部分
                match = re.findall('\d+', meta['rating_num'])
                if match:
                    meta['rating_num'] = f'{match[0]}人'
                else:
                    meta['rating_num'] = 'None'
            else:
                meta['rating_num'] = 'None'
            # 生成详情页请求，并将 meta 传递给 parse_detail
            yield scrapy.Request(meta['detail_url'], callback=self.parse_detail, meta=meta)

        # 处理分页：查找下一页的链接（<link rel="next">）
        next_page = response.xpath('//link[@rel="next"]/@href').get()
        if next_page:
            # 使用 response.follow 生成下一页请求，继续调用 parse
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        """
        解析图书详情页，提取详细的图书信息
        """
        item = DoubanBookItem()   # 创建 Item 对象，用于存储提取的数据

        # 书名（从列表页传递过来）
        item['title'] = response.meta['title']

        # ------------------- 作者信息 -------------------
        # 尝试匹配作者链接（多种页面结构）
        author_span = response.xpath('//div[@id="info"]/span/a')
        if author_span:
            if len(author_span) > 1:
                # 多个作者
                authors = []
                for span in author_span:
                    # 提取每个作者文本并去除首尾空白
                    authors.append(span.xpath('./text()').get().strip())
                author = ' / '.join(authors)
            elif len(author_span) == 1:
                # 单个作者（注意：先取列表中的第一个元素再调用 .xpath）
                author = author_span[0].xpath('./text()').get().strip()
            else:
                author = None
        else:
            # 如果上面的 XPath 未匹配，尝试另一种结构（直接取 <div id="info"> 下的第一个 <a> 标签）
            author = response.xpath('//div[@id="info"]/a[1]/text()').get()

        # 清洗作者文本：合并连续的空白字符（包括换行、空格）为单个空格
        author = re.sub(r'\s+', ' ', author).strip()
        item['author'] = author

        # 详情页 URL
        item['detail_url'] = response.url
        # 短评（从列表页传递过来）
        item['quote'] = response.meta['quote']
        # 评分（从列表页传递过来）
        item['rating'] = response.meta['rating']
        # 评价人数（从列表页传递过来）
        item['rating_num'] = response.meta['rating_num']

        # ------------------- 出版社 -------------------
        # 定位包含“出版社:”的 <span>，然后取紧随其后的第一个 <a> 标签的文本
        item['publisher'] = response.xpath('//div[@id="info"]/span[text()="出版社:"]/following-sibling::a[1]/text()').get()

        # ------------------- 出版年份 -------------------
        # 定位“出版年:”后的文本节点
        item['pub_date'] = response.xpath('//div[@id="info"]/span[text()="出版年:"]/following-sibling::text()').get().strip()

        # ------------------- 页数 -------------------
        # 定位“页数:”后的文本节点
        item['pages'] = response.xpath('//div[@id="info"]/span[text()="页数:"]/following-sibling::text()').get()

        # ------------------- 定价 -------------------
        price_node = response.xpath('//div[@id="info"]/span[text()="定价:"]/following-sibling::text()').get()
        if price_node:
            item['price'] = price_node.strip()
        else:
            item['price'] = 'None'

        # ------------------- ISBN 或统一书号 -------------------
        # 优先匹配“ISBN:”后的文本，如果没有则尝试“统一书号:”
        isbn_node = response.xpath('//div[@id="info"]/span[text()="ISBN:"]/following-sibling::text() | //div[@id="info"]/span[text()="统一书号:"]/following-sibling::text()').get()
        item['isbn'] = isbn_node.strip() if isbn_node else None

        # 生成 Item，供 pipeline 处理
        yield item
