import io
from lxml import etree
import re
from urllib.parse import urljoin

from parsers.common import num_stars_to_rating_mapping

class XPathParser:
    def __init__(self):
        self._parser = etree.HTMLParser()

    def _get_text_content(self, root, xpath, regex=None):
        result = root.xpath(xpath)
        if not result:
            return None
        result = ''.join(result)
        if not regex:
            return result.strip()
        match = re.search(regex, result)
        if match:
            return match.group().strip()
        return None

    def _parse_product_page(self, tree):
        result = {}
        result['title'] = self._get_text_content(tree, '//title/text()')
        result['description'] = self._get_text_content(tree, '//meta[@name="description"]/@content')
        result['genre'] = self._get_text_content(tree, '//*[contains(@class, "breadcrumb")]/li[3]/a/text()')
        product_main = tree.xpath('//div[contains(@class, "product_main")]')
        if not product_main:
            raise RuntimeError('Bad page, no product_main result')
        product_main = product_main[0]
        price_text = self._get_text_content(product_main, './/p[contains(@class, "price_color")]/text()', regex='[0-9\.]+')
        if price_text is None:
            raise RuntimeError('Failed to parse price')
        result['price'] = float(price_text)
        available_stock_text = self._get_text_content(product_main, './/p[contains(@class, "instock") and contains(@class, "availability")]/text()', regex='\d+')
        if available_stock_text is None:
            raise RuntimeError('Failed to parse available_stock')
        result['available_stock'] = int(available_stock_text)
        num_stars = product_main.xpath('.//*[contains(@class, "star-rating")]/@class')
        class_arr = num_stars and num_stars[0].split()
        num_stars_text = class_arr[1] if len(class_arr) >= 2 else None
        if num_stars_text is None:
            raise RuntimeError('Failed to parse rating')
        result['rating'] = num_stars_to_rating_mapping.get(num_stars_text)
        return result

    def _get_next_links(self, tree, cur_page_url):
        next = []
        # ссылки на товары
        for elem in tree.xpath('//*[contains(@class, "product_pod")]/*/a[@title]/@href'):
            next.append(urljoin(cur_page_url, elem))
        # след. страница
        next_page = tree.xpath('//li[@class="next"]/a/@href')
        if next_page:
            next.append(urljoin(cur_page_url, next_page[0]))
        return next

    def parse(self, content, cur_page_url):
        tree = etree.parse(io.BytesIO(content), self._parser)
        product_page_root = tree.xpath('//article[contains(@class, "product_page")]')
        result = None
        if product_page_root:
            result = self._parse_product_page(tree)
            return result, []
        next = self._get_next_links(tree, cur_page_url)
        return None, next
