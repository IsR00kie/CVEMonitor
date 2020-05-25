import requests
import re
import time
import urllib3
import threading

urllib3.disable_warnings()

# 参考下面操作申请机器人 TOKEN
# https://slowread.net/blog/%E4%BD%BF%E7%94%A8-telegram-%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%8F%91%E9%80%81%E6%B6%88%E6%81%AF/


API_TOKEN = ""  # 填写你创建机器人发送给你的TOKEN
CHAT_ID = []
API_SEND_MESSAGE = "http://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}&parse_mode=html&disable_web_page_preview=true"
API_GET_UPDATE = "https://api.telegram.org/bot{token}/GetUpdates"
CHECK_FILE = "check.txt"
CHAT_FILE = "chat_id.txt"


def getNews():
    items = []
    api = "https://api.github.com/search/repositories?q=CVE-2020&sort=updated"
    try:
        resp = requests.get(api)
    except Exception as e:
        print('网络请求异常: %s', e.args)
        return items

    if resp.status_code != 200:
        print('状态码异常: %d' % resp.status_code)
        return items

    for item in resp.json()['items']:
        size = item.get('size', 0)
        if size == 0:
            continue

        url = item.get('svn_url')
        name = item.get('name')
        description = item.get('description')
        if not description:
            description = '该CVE没有任何描述'

        items.append((name, description, url))
    return items


def send_news(check):
    while True:
        try:
            cve_items = getNews()
            for item in cve_items:
                if item[2] in check:
                    continue
                check.append(item[2])
                with open(CHECK_FILE, 'a') as fp:
                    fp.write(item[2] + '\n')
                text = "<a href=\"{url}\">CVE名称: {name}\nCVE描述: {des}</a>".format(
                    url=item[2], name=item[0], des=item[1])
                for i in CHAT_ID:
                    resp = requests.get(API_SEND_MESSAGE.format(
                        token=API_TOKEN, chat_id=i, text=text), verify=False)
                    if resp:
                        if resp.status_code == 200 and resp.json()['ok']:
                            print('推送成功: ' + text)
                        else:
                            print('推送失败: ' + text, resp.text)
                    else:
                        print('网络请求异常')
        except Exception as e:
            print('程序发生异常: %s' % e.args)
        time.sleep(180)


def update_chat_id():
    while True:
        if len(CHAT_ID) == 0:
            time.sleep(60)
            continue

        try:
            resp = requests.get(API_GET_UPDATE.format(
                token=API_TOKEN), verify=False)
            if resp is not None and resp.status_code == 200 and resp.json().get('ok', False) == True:
                for item in resp.json().get('result', []):
                    chat = item['message']['chat']
                    _id = str(chat['id'])
                    if _id in CHAT_ID:
                        continue

                    CHAT_ID.append(_id)
                    if chat['type'] == 'private':
                        print('新用户加入 ID: %s 名称: %s' %
                              (_id, chat['first_name']))
                    elif chat['type'] == 'supergroup':
                        print('新群组加入 ID: %s 名称: %s' % (_id, chat['title']))
                    else:
                        print(chat)

                    with open(CHAT_FILE, "a") as fp:
                        fp.write(_id + '\n')
        except Exception as e:
            print('获取chat id异常: %s' % e.args)

        time.sleep(180)


if __name__ == "__main__":
    if API_TOKEN == "":
        print('API_TOKEN 不能为空')
        exit(-1)

    with open(CHECK_FILE, 'a+') as fp:
        check = [i.strip() for i in fp.readlines()]

    with open(CHAT_FILE, 'a+') as fp:
        CHAT_ID = [i.strip() for i in fp.readlines()]

    threading.Thread(target=update_chat_id).start()
    t = threading.Thread(target=send_news, args=(check,))
    t.start()
    t.join()
