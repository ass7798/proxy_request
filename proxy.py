#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""wish no bug"""
__author__ = "zhangyang"
import requests
import random
import time


class Ip_Proxy(object):
    """获取ip地址和header"""

    def __init__(self, header_list=None, ip_list=None):
        """
        :param header_list: 可以是file(str)，也可以是list
        :param ip_list: 可以是file(str)，也可以是list，如['52.54.161.233:80']
        self.ip 为list
        self.ip_dict 为词典，储存了ip的响应信息
        """

        if type(header_list) is str:
            # 路径形式下，给header赋值
            f = open(header_list)
            header_list = []
            for line in f:
                header_list.append(line.strip())
            f.close()
        if type(header_list) is list:
            # list形式下，header赋值
            self.header = header_list

        self.ip = []  # 表示代理ip池
        self.ip_dict = {}  # 表示代理ip池的统计信息
        self.header_index = -1  # 用来记录返回的header的次序
        self.ip_index = -1  # 用来记录返回的header的次序
        self.test_url = ["http://httpbin.org/ip",
                         "http://www.baidu.com",
                         "http://www.sohu.com",
                         "http://www.sina.com"]  # 用来记录用来测速的test_url
        self.res = -1
        self.status = -1  # 表示限制返回ip的status
        self.use_ratio_ip = {}  # 表示统计ip的使用率的情况,key是ip，value是一个列表
        self.limit_return = {}  # 表示限制条件
        self.limit_return['last_interval_time'] = 3  # 上次响应时间 s
        self.limit_return['last_use_time'] = 300  # 上次使用时间间隔 s
        self.limit_return['avg_success_ratio'] = 0.6  # 使用60%以上成功率的 ip
        self.limit_return['avg_interval_time'] = 3  # 平均响应时间 3秒以内
        self.limit_return['last_use_status'] = -1  # 上次响应状态
        self.limit_return['all_use_count'] = 10  # 使用指定次数，再进行筛选
        self.load_ip(ip_list)

    def load_ip(self, ip_list, clear=0):
        """
        :param file: 表示文件路径, 或者是ip列表['52.54.161.233:80']
        :param clear:clear = 1 表示把之前存储的ip池信息都清除了
        :return:失败0,成功1
        """
        if clear:
            self.ip_dict = {}
            self.ip = []
        if ip_list is None:
            return 0
        self.ip_index = -1
        if type(ip_list) is str:
            # 路径形式下，给ip赋值
            f = open(ip_list)
            ip_list = []
            for line in f:
                ip_list.append(line.strip())
            f.close()
        if type(ip_list) is list:
            for ip_temp in ip_list:
                if not self.ip_dict.get("http://" + ip_temp, 0):
                    # 表示之前存储过的ip，不对其进行操作
                    dict_tmp = {'success_count': 0,  # 连接成功数
                                'fail_count': 0,  # 连接失败数
                                'last_interval_time': 0,  # 上次响应时间
                                'last_use_time': 0,  # 使用使用时间
                                'last_use_status': 0,  # 上次使用状态
                                'avg_success_ratio': 0.0,  # 平均成功率
                                'avg_interval_time': 0,  # 平均响应时间
                                }
                    self.ip_dict["http://" + ip_temp] = dict_tmp
        self.ip = self.ip_dict.keys()
        return 1

    def get_header(self):
        """
        返回一个header,队列形式，先进先出，保证短时间不重复
        """
        length = len(self.header)
        self.header_index += 1
        self.header_index %= length
        return {'User-Agent': self.header[self.header_index]}

    def get_ip(self):
        """
        返回一个ip
        limit_return_time 表示限制最低响应时间
        """
        length = len(self.ip)
        if length == 0:
            # 表示代理池没有ip
            return None
        while 1:
            self.ip_index += 1
            self.ip_index %= length
            return_ip = self.ip[self.ip_index]
            limit_return = self.limit_return
            if self.ip_dict[return_ip]['last_use_status'] is 0:
                # 说明第一次取这个ip,不需要进行筛选
                return return_ip
            if (self.ip_dict[return_ip]['success_count'] +
                    self.ip_dict[return_ip]['fail_count']) > limit_return['all_use_count']:
                # 大于一定的使用次数再进行筛选
                return return_ip
            if self.ip_dict[return_ip]['last_interval_time'] > limit_return['last_interval_time']:
                # 说明ip响应时间大于限制时间
                continue
            if self.ip_dict[return_ip]['last_use_status'] < limit_return['last_use_status']:
                # 说明只取ip响应成功 或者 没有采用的过ip
                continue
            if self.ip_dict[return_ip]['avg_success_ratio'] < limit_return['avg_success_ratio']:
                # 在10次内，ip成功率大于指定ip成功率才能返回结果
                continue
            if self.ip_dict[return_ip]['last_use_time'] > time.time() - limit_return[
                'last_use_time']:
                # 小于一定时间间隔的ip不再取
                continue
            return return_ip

    def get_url(self, url, headers=None, proxies=None, timeout=3):
        """
        在requests.get的基础上进行代理访问，如果proxies/headers = -1表示不加任何代理，头部信息
        :param url:要访问的url 'http://36.84.12.212:80'
        :param proxies:格式
        :return: status表示是否请求成功, res 为requests对象
        """

        if headers is None:
            headers = self.get_header()
        if headers is -1:
            headers = None
        if proxies is None:  # 表示采用库中的默认代理
            proxies = self.get_ip()
        if proxies is -1:  # 表示不用任何代理
            proxies = None
        begin_time = time.time()
        try:
            res = requests.get(url, headers=headers, proxies={'http': proxies}, timeout=timeout)
            if res.ok:
                status = 1
            else:
                status = -1
        except Exception, e:
            # print e
            status = -1
        end_time = time.time()
        interval_time = end_time - begin_time
        if proxies:
            dict_tmp = {'success_count': 0,  # 连接成功数
                        'fail_count': 0,  # 连接失败数
                        'last_interval_time': 0,  # 上次响应时间
                        'last_use_time': 0,  # 使用使用时间
                        'last_use_status': 0,  # 上次使用状态
                        'avg_success_ratio': 0.0,  # 平均成功率
                        'avg_interval_time': 0,  # 平均响应时间
                        }
            dict_use = self.ip_dict.get(proxies, dict_tmp)
            dict_use['last_use_time'] = begin_time
            dict_use['last_interval_time'] = interval_time
            dict_use['last_use_status'] = status
            if status is 1:
                dict_use['success_count'] += 1
                dict_use['avg_interval_time'] = ((dict_use['success_count'] * dict_use[
                    'avg_interval_time']) + dict_use['last_interval_time']) / dict_use[
                                                    'success_count']
            if status is -1:
                dict_use['fail_count'] += 1
            dict_use['avg_success_ratio'] = float(dict_use['success_count']) / (
                dict_use['success_count'] + dict_use['fail_count'])
            if self.ip_dict.get(proxies, 0):
                # 说明之前存在这个ip
                self.ip_dict[proxies] = dict_use
            else:
                # 说明之前不存在这个ip
                self.ip_dict[proxies] = dict_use
                self.ip = self.ip_dict.keys()
        if status is 1:
            # 连接成功
            self.res = res
        return status

    def test_ip(self):
        """
        测试ip的是否能连通以及响应时间

        """
        length_url = len(self.test_url)
        for i in range(len(self.ip)):
            time.sleep(0.1)
            self.get_url(url=self.test_url[i % length_url], proxies=self.get_ip())

    def crawl_ip(self, clear=0, url=None):
        """
        从网络获取ip
        :return:1,成功.0,失败
        """
        if not url:
            url = "None"
        try:
            res = requests.get(url=url)
        except:
            return 0
        ip_list = []
        for ip_temp in res.content.split():
            ip_list.append(ip_temp.strip())
        self.load_ip(ip_list=ip_list, clear=clear)

    def clear_ip(self, status=1):
        """
        清除ip池的信息,默认清除未连接的ip或者连接失败的ip
        :return:
        """
        pass

    def statistic(self, limit_use_time=300):
        """
        统计ip池的各种信息，如ip总量，5分钟内ip的使用率，ip的可用率(status)，ip的平均请求时间，IP的总请求成功率等
        :param limit_use_time: 用来限制的统计的时间
        :return: dict
        """
        ip_dict = self.ip_dict
        all_use_time = 0
        success_count = 0
        fail_count = 0
        now_time = time.time()
        limit_use_ip_count = 0  # 限定时间内的使用次数，譬如300秒以内的
        all_ip = len(self.ip)
        for k, v in ip_dict.items():
            success_count += v['success_count']
            fail_count += v['fail_count']
            all_use_time += v['avg_interval_time'] * v['success_count']
            if v['last_use_time'] > (now_time - limit_use_time):
                limit_use_ip_count += 1

        result_dict = {'all_success_count': success_count,  # 连接成功数
                       'all_fail_count': fail_count,  # 连接失败数
                       'all_avg_success_ratio': float(success_count) / (fail_count + success_count),
                       # 平均成功率
                       'all_avg_interval_time': float(all_use_time) / success_count,  # 平均响应时间
                       'all_ip': all_ip,  # 总体的ip数目
                       'limit_use_ip_count': limit_use_ip_count,  # 在限定的时间内使用过的ip的数目
                       'limit_use_ratio': float(limit_use_ip_count) / (all_ip + 1),  # 在限定的时间内ip的使用率
                       }
        return result_dict

    def connect_pool(self):
        """连接到服务器的ip池子"""
        pass


if __name__ == "__main__":
    test_1 = Ip_Proxy('header', 'ip')
    print test_1.get_ip()
    test_1.test_ip()
    print test_1.ip
    print test_1.ip_dict
    print test_1.get_url(url='http://httpbin.org/ip')
    print test_1.ip_dict
    # test_1 = Ip_Proxy('header', ['52.54.161.233:80'])
    # print test_1.header
    # print test_1.ip
    # print test_1.get_ip()
    while test_1.get_url(url='http://httpbin.org/ip') is -1:
        print 1
    print test_1.res.content
    print test_1.ip_dict
    test_1.crawl_ip(clear=1)
    print test_1.ip
    print len(test_1.ip)
    test_1.test_ip()
    print test_1.ip_dict
    print test_1.statistic()
