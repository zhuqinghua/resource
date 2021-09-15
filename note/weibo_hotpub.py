# 获取热搜源码
import json
import re
from time import time
from queue import Queue
from threading import Thread

import requests as requests

weibo_url = 'https://s.weibo.com'
today_url = 'https://tophub.today'
today_div_regex = re.compile(
    r'<div class="cc-cd-is">\s+<a href="(.*?)">\s+<div class="cc-cd-lb"><img.*>(.*?)</div>\s+</a>\s+</div>\s+<div '
    r'class="cc-cd-sb">\s+<div class="cc-cd-sb-ss cc-cd-sb-ss-ia">\s+<span class="cc-cd-sb-st">('
    r'.*?)</span>\s+</div>\s+</div>\s+</div>\s+<div class="cc-cd-cb nano">([\S\s]+?)</div>\s+</div>['
    r'\S\s]+?homepage="(\S+)" hashid="(\S+)"')
today_div_top_regex = re.compile(
    r'<a href="(.*?)" target="_blank" rel="nofollow" itemid="\S+">\s+<div class="cc-cd-cb-ll">\s+'
    r'<span class="[s h]+">(\d+)</span>\s+<span class="t">(.*?)</span>\s+<span class="e">(.*?)</span>')
weibo_regex = re.compile(
    r'<tr class="">\s+<td class="td-01 ranktop">(\d+)</td>\s+<td class="td-02">\s+<a href="(\S+)" target="_blank">('
    r'.*?)</a>\s+<span>(.*?)</span>\s+</td>\s+<td class="td-03">.*</td>\s+</tr>')
request_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
              ',application/signed-exchange;v=b3',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Cookie': '',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36'
}


def weibo():
    json_list = []
    lists = weibo_regex.findall(get_html(weibo_url + '/top/summary'))
    for vo in lists:
        json_list.append(dict(num=vo[0], url=weibo_url + vo[1], key=vo[2], hotNum=vo[3].strip()))
    print(json.dumps(json_list, indent=2, ensure_ascii=False))


def get_html(url):
    try:
        response = requests.get(url, headers=request_headers)
        return response.text
    except IOError as e:
        print(e)
        return None


def top_hub_today():
    start = time()
    all_list = []
    # 获取分类
    regex = re.compile(r'href="(\S+)"><div class="gb-c">(\S+)</div>')
    hh = get_html(today_url)
    title = []
    lists = regex.findall(hh)
    for vo in lists:
        if vo[0] != '/':
            title.append(dict(title=vo[1], url=vo[0]))

    queue = Queue()
    result_queue = Queue()

    # 根据分类获取数据
    for sub in title:
        queue.put(sub)

    for index in range(10):
        t = Thread(target=task_handler, args=(queue, result_queue,))
        t.daemon = True
        t.start()

    queue.join()

    while not result_queue.empty():
        all_list.append(result_queue.get())

    # print(json.dumps(all_list, indent=4, ensure_ascii=False))
    save_data(all_list)
    end = time()
    print('保存数据完成, 花费时间=%d' % (end - start))


def task_handler(in_q, out_q):
    while in_q.empty() is not True:
        page = 1
        subs = []
        sub = in_q.get()
        url = sub['url']
        title = sub['title']
        while True:
            query_url = today_url + url + '?p=' + str(page)
            print("--->[%s] url=[%s], 页数=[%d]" % (title, query_url, page))
            sub_html = get_html(query_url)
            div_list = today_div_regex.findall(sub_html)
            if div_list:
                page += 1
                for div in div_list:
                    # 解析排行榜
                    try:
                        top_list = []
                        tops = today_div_top_regex.findall(div[3])
                        [top_list.append(dict(url=vo[0], indx=vo[1], key=vo[2], hotNum=vo[3])) for vo in tops]
                        subs.append(
                            dict(app=div[1].strip(), app_url=div[4], url=div[0], hash_id=div[5], top_list=top_list))
                    except IOError as e:
                        print(e)
            else:
                break
        out_q.put(dict(name=title, url=today_url + url, sub=subs))
        in_q.task_done()


def save_data(data):
    try:
        with open('/Users/zhang/Desktop/hot.json', 'w', encoding='utf-8') as fs:
            json.dump(data, fs, indent=4, ensure_ascii=False)
    except IOError as e:
        print(e)


if __name__ == '__main__':
    weibo()
    top_hub_today()
