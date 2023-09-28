# encoding: utf-8
"""
@version: python3.10
@project: Crawler_KFC_Restaurant_Locations
@title: CrawlerKFC.py
@author: Seagull
@contact: 1945796325@qq.com
@software: PyCharm
@time: 2023/9/28 星期四 17:51
"""
import json
import os
import requests


def find_all_index(text: str, subtext: str, start: int, end: int) -> list[int]:
    # 本函数找到字符串 text 中所有 subtext 的位置, 返回列表
    index_list = []
    while (index := text.find(subtext, start, end)) != -1:
        index_list.append(index)
        start = index + 10
    return index_list


def get_page_info(text):
    # 本函数针对 http://www.kfc.com.cn/kfccda/storelist/index.aspx 网页源码
    left_info = '<ul class="shen_info">'
    right_info = '<!-- 省份 -->'
    left_id = text.find(left_info)
    right_id = text.find(right_info, left_id)

    province_start_info = '<strong>'
    province_end_info = '</strong>'
    city_start_info = '<a href="javascript:void(0);" '
    city_end_info = '</a>'

    # 找到源码中所有 省份 与 城市
    province_id_list = find_all_index(text, province_start_info, left_id, right_id)
    city_id_list = find_all_index(text, city_start_info, left_id, right_id)

    # 最终结果
    # {
    #   省份: [ {城市信息}, {城市信息}, ... ],
    #   省份: [ {城市信息}, {城市信息}, ... ],
    #   ...
    # }
    # {城市信息} 是 XML 字符串
    province_city_dict: dict[str, list[str]] = {}
    for province_id in province_id_list:
        province_id_l = province_id + len(province_start_info)
        province_id_r = text.find(province_end_info, province_id)
        province_name = text[province_id_l:province_id_r]
        province_city_dict[province_name] = []

    # 遍历在网页源码中找到的所有城市, append 入字典中 "key 所属省份" 对应的 "value: [{城市信息} ...]" 中
    province_id_pointer = 0
    for city_id in city_id_list:
        if province_id_pointer + 1 < len(province_id_list) and city_id >= province_id_list[province_id_pointer + 1]:
            province_id_pointer += 1

        province_id = province_id_list[province_id_pointer]
        province_id_l = province_id + len(province_start_info)
        province_id_r = text.find(province_end_info, province_id)
        province_name = text[province_id_l:province_id_r]

        city_id_l = city_id
        city_id_r = text.find(city_end_info, city_id)
        city_name = text[city_id_l:city_id_r]
        province_city_dict[province_name].append(city_name)

    # 去掉可变玩意
    province_city_dict_tuple: dict[str, tuple[str]] = {}
    for key in province_city_dict:
        province_city_dict_tuple[key] = tuple(province_city_dict[key])

    return province_city_dict_tuple


def get_city_name(city_string):
    sign = '\">'
    return city_string[city_string.find(sign) + len(sign):]


def log(name_1, name_2):
    print(f"---- {name_1} 省 {name_2} 市爬取完毕 ----")


if __name__ == '__main__':
    path = r"./爬虫"

    # 先抓取所有省份城市列表
    url_0 = "http://www.kfc.com.cn/kfccda/storelist/index.aspx"
    headers: dict[str, str] = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0.0.0 Safari/537.36 "
    }

    response = requests.get(url=url_0, headers=headers)
    page_text = response.text

    file_name = "KFC_index.html"
    file_path = os.path.join(path, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(page_text)

    file_name = "全国省份城市信息列表.json"
    file_path = os.path.join(path, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(page_info := get_page_info(page_text), fp=file, indent=4, ensure_ascii=False)

    # 再抓取所有 KFC 餐厅信息
    url = "http://www.kfc.com.cn/kfccda/ashx/GetStoreList.ashx?op=cname"

    city_KFC_dict = {}
    for province_name in page_info:
        city_KFC_dict[province_name] = {}

        city_tuple = page_info[province_name]
        for city_string in city_tuple:
            city_KFC_dict[province_name][city_name := get_city_name(city_string)] = {}

            params = {
                'cname': city_name,
                'pid': '',
                'pageIndex': '1',
                'pageSize': '10'
            }
            response = requests.post(url=url, params=params, headers=headers)
            city_KFC_dict[province_name][city_name] = response.json()

            # response 的结构
            # {
            #   Table: [{rowcount : KFC_number}],
            #   Table1:
            #       [
            #           {餐厅 01 信息},
            #           {餐厅 02 信息},
            #           ...
            #           {餐厅 KFC_number 信息}
            #       ]
            # }

            # 每一页 10 个结果, 分页读完
            KFC_number = int(city_KFC_dict[province_name][city_name]['Table'][0]["rowcount"])
            if KFC_number <= 10:
                log(province_name, city_name)
                continue
            KFC_pages = (KFC_number - 1) // 10 + 1
            for KFC_page in range(2, KFC_pages + 1):
                params = {
                    'cname': city_name,
                    'pid': '',
                    'pageIndex': str(KFC_page),
                    'pageSize': '10'
                }
                response = requests.post(url=url, params=params, headers=headers)
                dict_list_json = response.json()
                city_KFC_dict[province_name][city_name]['Table1'].append(dict_list_json)

            log(province_name, city_name)

    file_name = "全国 KFC 所有店铺信息.json"
    file_path = os.path.join(path, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(city_KFC_dict, fp=file, indent=4, ensure_ascii=False)

    log("All", "All")
