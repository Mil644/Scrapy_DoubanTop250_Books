# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DoubanBookItem(scrapy.Item):
    title = scrapy.Field()
    author = scrapy.Field()
    quote = scrapy.Field()
    rating = scrapy.Field()
    rating_num = scrapy.Field()
    publisher = scrapy.Field()
    pub_date = scrapy.Field()
    pages = scrapy.Field()
    price = scrapy.Field()
    series = scrapy.Field()
    isbn = scrapy.Field()
    detail_url = scrapy.Field()

    pass
