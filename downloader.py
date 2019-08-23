#coding: utf-8

import requests
import urllib.parse
import os
import time
import sys
import queue
import threading
from requests_html import HTMLSession
import re
import logging
logging.captureWarnings(True)

threadListSize = 50
queueSize = 96

dir = "D:\测试运行\\"
_exitFlag = 0
_ts_total = 0
_count = 0
_dir=''
_videoName=''
_queueLock = threading.Lock()
_workQueue = queue.Queue(queueSize)
_threadList=[]
for i in range(threadListSize):
    _threadList.append("Thread-"+str(i))

welcome_words = '''
            *************************************************
            *                                               *
            *              欢迎使用资源下载脚本                *
            *                                               *
            *                                               *
            *************************************************
                '''


session2 = HTMLSession()
search_url = "https://www.haiduomi.cc/search.html?wd={}"

class downloadThread (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
    def run(self):
        # print ("开启线程：" + self.name + '\n', end='')
        download_data(self.q)
        # print ("退出线程：" + self.name + '\n', end='')

# 下载数据
def download_data(q):
    while not _exitFlag:
        _queueLock.acquire()
        if not _workQueue.empty():
            data = q.get()
            _queueLock.release()
            # print ("%s 使用了 %s" % (threadName, data) + '\n', end='')
            url = data
            retry = 3
            while retry:
                try:
                    r = session.get(url, timeout=20, verify=False)
                    if r.ok:
                        file_name = url.split('/')[-1].split('?')[0]
                        # print(file_name)
                        with open(os.path.join(_dir, file_name), 'wb') as f:
                            f.write(r.content)
                        _queueLock.acquire()
                        global _count
                        _count = _count+1
                        show_progress(_count/_ts_total)
                        _queueLock.release()
                        break
                except Exception as e:
                    print(e)
                    retry -= 1
            if retry == 0 :
                print('[FAIL]%s' % url)
        else:
            _queueLock.release()


# 填充队列
def fillQueue(nameList):
    _queueLock.acquire()
    for word in nameList:
        _workQueue.put(word)
        nameList.remove(word)
        if _workQueue.full():
            break
    _queueLock.release()


def get_session( pool_connections, pool_maxsize, max_retries):
    '''构造session'''
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=pool_connections, pool_maxsize=pool_maxsize, max_retries=max_retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 展示进度条
def show_progress(percent):
    bar_length=50
    hashes = '#' * int(percent * bar_length)
    spaces = ' ' * (bar_length - len(hashes))
    sys.stdout.write("\rPercent: [%s] %.2f%%"%(hashes + spaces, percent*100))
    sys.stdout.flush()


def start(m3u8_url, dir, videoName):
    global _dir
    global _videoName
    global _ts_total
    if dir and not os.path.isdir(dir):
        os.makedirs(dir)
    _dir=dir
    _videoName=videoName
    r = session.get(m3u8_url, timeout=10, verify=False)
    if r.ok:
        body = r.content.decode()
        if body:
            ts_list=[]
            body_list=body.split('\n')
            for n in body_list:
                if n and not n.startswith("#"):
                    ts_list.append(urllib.parse.urljoin(m3u8_url, n.strip()))

            # 判断是否为真是url地址,并递归真实url
            if len(ts_list) == 1:
                # real_url = get_real_url(m3u8_url)
                return start(ts_list[0], _dir, _videoName)

            if ts_list:
                _ts_total = len(ts_list)
                print('ts的总数量为：'+str(_ts_total)+'个')
                # 下载ts文件
                print('开始下载文件')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                res=download(ts_list)
                # res=True
                print('')
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                if res:
                    # 整合ts文件
                    print('\n开始整合文件')
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                    merge_file(ts_list)
                    print('')
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                else:
                    print('下载失败')
    else:
        print(r.status_code)


def download(ts_list):
    threads = []
    threadID=1
    # 创建新线程
    for tName in _threadList:
        thread = downloadThread(threadID, tName, _workQueue)
        thread.start()
        threads.append(thread)
        threadID += 1
    ts_list_tem=ts_list.copy()
    fillQueue(ts_list_tem)
    # 等待队列清空
    while not _workQueue.empty():
        if _workQueue.full():
            pass
        else :
            fillQueue(ts_list_tem)
    # 通知线程是时候退出
    global _exitFlag
    _exitFlag = 1
    # 等待所有线程完成
    for t in threads:
        t.join()
    return True

# 将TS文件整合在一起
def merge_file(ts_list):
    index = 0
    outfile = ''
    global _dir
    while index < _ts_total:
        file_name = ts_list[index].split('/')[-1].split('?')[0]
        # print(file_name)
        percent = (index + 1) / _ts_total
        show_progress(percent)
        infile = open(os.path.join(_dir, file_name), 'rb')
        if not outfile:
            global _videoName
            if _videoName=='':
                videoName=file_name.split('.')[0]+'_all'
            outfile = open(os.path.join(_dir, _videoName+'.mp4'), 'wb')
        outfile.write(infile.read())
        infile.close()
        # 删除临时ts文件
        os.remove(os.path.join(_dir, file_name))
        index += 1
    if outfile:
        outfile.close()


def main(urllist, dir):

    print(urllist)
    for i in range(len(urllist)):
        index = str(i+1)
        print("开始下载第"+index+"个视频")
        url = urllist[i]
        global _exitFlag
        global _count
        _count = 0
        _exitFlag = 0
        start(url,dir,"第{0}集".format(index))


def get_result(kws):
    c = session2.get(search_url.format(urllib.parse.quote(kws)))

    title_xpath = [t.text for t in c.html.xpath('//h1')]
    actor_xpath = [a.text for a in c.html.xpath('//div[2]/dl/dd[1]/ul/li[1]')]
    year_xpath = [y.text for y in c.html.xpath('//dl/dd[1]/ul/li[5]')]
    area_xpath = [y.text for y in c.html.xpath('//dl/dd[1]/ul/li[4]')]
    category_xpath = [ca.text for ca in c.html.xpath('//dl/dd[1]/ul/li[3]')]
    url_xpath = ["https://www.haiduomi.cc"+u for u in c.html.xpath('//h1/a/@href')]



    result_list = zip(title_xpath, actor_xpath, year_xpath, area_xpath, category_xpath, url_xpath)

    temp = 1
    if title_xpath:
        for l in result_list:
            print("资源"+str(temp)+"名称："+l[0]+"\n"+l[1]+"\t"+l[2]+"\t"+l[3]+"\t"+l[4])
            print("\n"+"***********传说中的分割线*************")
            temp += 1
        return title_xpath, url_xpath
    else:
        print("没有找到你要的资源呢，要不换一个吧！\n")
        start2()



def getdetail(title, url):
    c = session2.get(url)

    href_xpath = ["https://www.haiduomi.cc"+href for href in c.html.xpath('//div[1]/ul[2]/li/a/@href')]
    if len(href_xpath) >= 1:
        links = []
        print(title + "共有" + str(len(href_xpath)) + "集")
        n = input("请选择你要下载的视频,给出视频的序数即可：")
        for i in list(n):
            if i != None:
                links.append(href_xpath[int(i)-1])
            else:
                continue
    else:
        print("好像没有资源呢")
    return title, links


def get_m3u8_files(title, urls):
    list = []
    for i in urls:
        c = session2.get(i)
        patter = 'ay=\"https.*?\.m3u8'
        l = re.findall(patter, c.text)
        list.append(l[0].strip("ay=\""))
    return title, list


def start2():
    print(welcome_words+"\r")
    kws = input("请输入电影名字：")
    titles, urls = get_result(kws)
    number = int(input("请输入要下载的资源序号(如1,2,3......)："))
    titles2, url2 = getdetail(titles[number-1], urls[number-1])
    titles3, url3 = get_m3u8_files(titles2, url2)
    main(url3, titles3)

if __name__ == '__main__':
    session = get_session(50, 50, 3)
    start2()


