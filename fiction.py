# coding=utf-8
import re

import requests, time, os
from bs4 import BeautifulSoup
from pip._vendor.distlib.compat import raw_input
import threading

path = r'/Users/jhy/Desktop/小说/'  # 本地存放小说的路径

slice = 20  # 分段下载 小于1 就不分段下载 会很慢
want_book = ''
data = []
indexs = []


class SaveThread(object):
    size = 0
    content_data = []

    def __init__(self):
        self.session = requests.session()

    def count(self):
        return SaveThread.size

    def setSize(self, size):
        SaveThread.size = size

    def append(self, content):
        self.content_data.append(content)

    def bubbleSort(self, arr):
        for i in range(1, len(arr)):
            for j in range(0, len(arr) - i):
                if arr[j]['index'] > arr[j + 1]['index']:
                    arr[j]['index'], arr[j + 1]['index'] = arr[j + 1]['index'], arr[j]['index']
                    arr[j]['content'], arr[j + 1]['content'] = arr[j + 1]['content'], arr[j]['content']
        return arr

    def appendWithIndex(self, index, appendInfo):
        for info in self.content_data:
            if info['index'] == index:
                info['content'] = info['content'] + appendInfo

    def getData(self):
        resultInfo = ''
        bull = self.bubbleSort(self.content_data)
        # for data in bull:
        #     print(data)
        for info in bull:
            resultInfo = resultInfo + info['content']
        return resultInfo


pool = SaveThread()


def get_books(url, pageIndex):
    webdata = requests.get(url, timeout=60)
    soup = BeautifulSoup(webdata.text, 'html.parser')
    pages = soup.select('div.search-result-page-main > a')
    books = soup.select('div.result-list > div')

    for index, info in enumerate(books):
        book = info.select('div.result-game-item-detail > h3 > a')[0]
        bookid = book.get('href')  # 小说ID作为下一个请求ur中的参数
        bookname = book.select('span')[0]  # 小说名称
        auth = info.select('div.result-game-item-detail > div > p > span')[1]
        print("page:{} 序号:{} 书名: {}  作者: {} bookId:{}".format(
            pageIndex,
            len(data),
            str(bookname).replace("<span>", '').replace('</span>', ''),
            str(auth).replace("<span>", '').replace('</span>', ''),
            bookid))
        data.append({'index': len(data), 'bookname': str(bookname).replace("<span>", '').replace('</span>', ''),
                     "bookId": bookid})
        indexs.append(len(data) - 1)
    # print(pages)
    # print('pageIndex {} length={}'.format(pageIndex, len(pages)))
    if pageIndex > 1:
        if len(pages) > 1 and pageIndex < len(pages) - 1:
            pageIndex = pageIndex + 1
            get_books('http://www.biquge.com.cn/search.php?q={}&p={}'.format(want_book, pageIndex), pageIndex)
        else:
            check_input(indexs, data)
    else:
        if len(pages) > 1 and pageIndex < len(pages):
            pageIndex = pageIndex + 1
            get_books('http://www.biquge.com.cn/search.php?q={}&p={}'.format(want_book, pageIndex), pageIndex)
        else:
            if len(indexs) == 0:
                print("没有可以下载的书本")
                return
            check_input(indexs, data)


def check_input(indexs, data):
    str = raw_input("请输入想下载的序号:")
    # 判断是否为数字
    if is_number(str):
        if int(str) in indexs:
            start_downLoad(data[int(str)]['bookname'], data[int(str)]['bookId'])
        else:
            print("您选择的序号不在列表中,请重新选择")
            check_input(indexs, data)
    else:
        print("输入的不是数字，请重新输入")
        check_input(indexs, data)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


class MyThread(threading.Thread):  # 继承父类threading.Thread
    def __init__(self, threadName, bookname, titles, startTitle, endTitle, poolIndex):
        threading.Thread.__init__(self)
        self.threadName = threadName
        self.bookname = bookname
        self.titles = titles
        self.startTitle = startTitle
        self.endTitle = endTitle
        self.poolIndex = poolIndex

    def run(self):  # 把要执行的代码写到run函数里面 线程在创建后会直接运行run函数
        # print("{} start".format(self.threadName))
        pool.setSize(pool.count() + 1)
        download_range(self.bookname, self.titles, self.startTitle, self.endTitle, self.poolIndex)
        # print("{} finish".format(self.threadName))
        pool.setSize(pool.count() - 1)
        if pool.count() == 0:
            print('=====================准备写入=====================')
            f = open(path + '{}.txt'.format(self.bookname), 'a+')  # 章节名称写到txt文本
            f.write(pool.getData())
            f.close()
            print('=====================下载完成=====================')


def start_downLoad(bookname, bookid):
    print('=====================正在下载【' + bookname + '】=====================')
    url = 'http://www.biquge.com.cn{}'.format(bookid)
    print("下载地址:{}".format(url))
    titles = BeautifulSoup(requests.get(url, timeout=60).text, 'html.parser').select('div.box_con > div > dl > dd > a')
    if not os.path.exists(path):
        os.makedirs(path)

    # 这里可以分成多个部分 一起下载然后拼起来
    size = int(len(titles) / slice)

    # print('总体长度 {} 分片{} 每片{}'.format(len(titles), slice, size))

    if slice < 1:
        MyThread("thread {}".format('single'), bookname, titles, 0, len(titles), 0).start()
        return

    for num in range(0, slice):
        start = int(num * size)
        end = int((num + 1) * size)
        # print('index {} from {} to {}'.format(num, start, end))
        MyThread("thread {}".format(num), bookname, titles, start, end, num).start()
        if num is slice - 1:
            print('index {} from {} to {}'.format(slice, end, len(titles)))
            MyThread("thread-{}".format(num), bookname, titles, end, len(titles), slice).start()


def download_range(bookname, titles, start, end, index):
    isFirst = True
    for title in titles[start:end]:
        titleurl = 'http://www.biquge.com.cn' + title.get('href')  # 章节url地址
        titlename = title.text  # 章节名称
        # print("章节名称:{} 下载地址:{}".format(titlename, titleurl))
        try:
            # f = open(path + '{}{}.txt'.format(bookname, index), 'a+')  # 章节名称写到txt文本
            # f.write('\n' * 2 + titlename + '\n')
            # f.close()
            if isFirst:
                pool.append({"index": index, "content": '\n' * 2 + titlename + ' title ' + '\n'})
                isFirst = False
            else:
                pool.appendWithIndex(index, '\n' * 2 + titlename + ' title ' + '\n')
        except:
            pass

        contents = BeautifulSoup(requests.get(titleurl, timeout=60).text, 'html.parser').select(
            'div#content')
        for content in contents:
            content = str(content).replace('<br>', '\n') \
                .replace('</br>', '') \
                .replace('<br/>', '\n') \
                .replace('<div id="content">', '') \
                .replace('</div>', '')
            try:
                # f = open(path + '{}{}.txt'.format(bookname, index), 'a+')  # 正文内容卸载txt文本，紧接在章节名称的下面
                # f.write(content)
                # f.close()
                pool.appendWithIndex(index, titlename + content + "\n")
                # pool.appendWithIndex(index, titlename + " content\n")
            except:
                pass
        print(titlename + '[已下载]')


if __name__ == "__main__":
    data = []
    indexs = []

    pool.setSize(0)
    want_book = raw_input("请输入想下载的小说名称：")
    # want_book = "斗罗大陆"
    url = 'http://www.biquge.com.cn/search.php?q={}&p={}'.format(want_book, 1)
    get_books(url, 1)

    # pool.append({"index": 2, "content": "22222222222222\n"})
    # pool.appendWithIndex(2,'magasdasdfasdf\n')
    # pool.append({"index": 1, "content": "11111111111111\n"})
    # pool.append({"index": 3, "content": "333333333333\n"})
    # print('结果\n{}'.format(pool.test()))
