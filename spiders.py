# -*- coding: utf-8 -*-
import threading
import requests
import re
from Queue import Queue
from lxml.etree import HTML
import logging

lock = threading.Lock()
logging.basicConfig(level=logging.WARN)


class Spider(object):
    def __init__(self, data, max_depth=5):
        self.data = data
        self.max_depth = max_depth
        self.session = requests.Session()

    def get(self, url, depth=0):
        logging.warning('[{}] Processing {} ({}).'.format(threading.current_thread().name, url, depth))
        rsp = self.session.get(url)
        rsp.encoding = 'GB2312'
        html = HTML(rsp.text)
        urls = html.xpath('//a/@href')
        urls = list(set(filter(lambda url: re.search(r'\.sina\.com', url), urls)))
        for url in urls:
            self.data.put((url, depth + 1))

    def crawl(self):
        lock.acquire()
        try:
            url, depth = self.data.get()
        finally:
            lock.release()
        if depth < self.max_depth:
            self.get(url, depth=depth)


class CrawlThread(threading.Thread):
    def __init__(self, data, name):
        self.data = data
        super(CrawlThread, self).__init__(name=name)

    def run(self):
        spider = Spider(data=self.data, max_depth=4)
        while True:
            spider.crawl()


class Pool(object):
    def __init__(self, n):
        self.data = Queue()
        self.pool = list()
        self._create(n)

    def _create(self, n):
        for i in xrange(n):
            crawl_thread = CrawlThread(data=self.data, name='Thread-{}'.format(i + 1))
            self.pool.append(crawl_thread)
        self.data.put(('http://www.sina.com.cn/', 0))

    def activate(self):
        for crawl_thread in self.pool:
            crawl_thread.start()

    def get_pool(self):
        return self.pool


if __name__ == '__main__':
    pool = Pool(4)
    pool.activate()
