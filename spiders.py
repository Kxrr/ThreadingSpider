# -*- coding: utf-8 -*-
import logging
import re
import threading
import time
from Queue import Queue
from collections import Counter, OrderedDict
from optparse import OptionParser
from urlparse import urlparse

import requests
from lxml.etree import HTML

parser = OptionParser()
lock = threading.Lock()
logging.basicConfig(level=logging.ERROR)
counter = Counter()
counter_processed = Counter()

parser.add_option('-u', dest='start_url', default='http://www.sina.com.cn/')
parser.add_option('-d', dest='max_depth', type='int', default=5)
parser.add_option('--thread', dest='thread_num', type='int', default=10)

opt, _ = parser.parse_args()
start_url = opt.start_url
assert 'http://' in start_url or 'https://' in start_url


def show_progress():
    while True:
        c = OrderedDict(counter)
        cp = OrderedDict(counter_processed)
        print('{:-^30}'.format('Status'))
        print('{:<11}'.format('depth')),
        for titile in c.keys():
            print('{:<6}'.format(titile)),
        print('{:<12}'.format('\nprocessed')),
        for done in cp.values():
            print('{:<6}'.format(done)),
        print('{:<12}'.format('\nall')),
        for all in c.values():
            print('{:<6}'.format(all)),
        print('\n')
        time.sleep(10)


class Spider(object):
    def __init__(self, data, max_depth=opt.max_depth):
        self.data = data
        self.max_depth = max_depth
        self.session = requests.Session()
        self.url_loc = urlparse(start_url).netloc.replace('www.', '')

    def get(self, url, depth=1):
        counter_processed.update((depth, ))
        logging.info('[{}] Processing {} ({}).'.format(threading.current_thread().name, url, depth))
        rsp = self.session.get(url)
        rsp.encoding = 'GB2312'
        html = HTML(rsp.text)
        urls = html.xpath('//a/@href')
        urls = list(set(filter(lambda url: re.search(self.url_loc, url), urls)))
        for url in urls:
            self.data.put((url, depth + 1))
        counter.update([depth + 1] * len(urls))

    def crawl(self):
        lock.acquire()
        try:
            url, depth = self.data.get()
        finally:
            lock.release()
        if depth <= self.max_depth:
            self.get(url, depth=depth)


class CrawlThread(threading.Thread):
    def __init__(self, data, name):
        self.data = data
        super(CrawlThread, self).__init__(name=name)

    def run(self):
        spider = Spider(data=self.data)
        while True:
            spider.crawl()


class Pool(object):
    def __init__(self, n=opt.thread_num):
        self.data = Queue()
        self.threads = list()
        self._create(n)

    def _create(self, n):
        for i in xrange(n):
            crawl_thread = CrawlThread(data=self.data, name='Thread-{}'.format(i + 1))
            self.threads.append(crawl_thread)
        progress_thread = threading.Thread(target=show_progress)
        self.threads.append(progress_thread)
        self.data.put((start_url, 1))
        counter.update((1, ))

    def activate(self):
        for thread in self.threads:
            thread.start()


if __name__ == '__main__':
    pool = Pool()
    pool.activate()
