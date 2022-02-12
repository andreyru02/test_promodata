import sys
from time import sleep, time
from slugify import slugify
import requests
import json
import csv
from datetime import datetime
from pprint import pprint


def save_data_to_csv(data):
    with open('data.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, delimiter=';', fieldnames=data['items'][0].keys())
        writer.writeheader()
        writer.writerows(data['items'])

    return 'Данные сохранены в "data.csv"'


class SimpleWine:
    url = 'https://simplewine.ru/api/'

    def __init__(self, version, shop_id, available, address, category, save_data_to_file=False):
        self.version = version
        self.shop_id = shop_id
        self.available = available
        self.address = address
        self.category = category
        self.save_data_to_file = save_data_to_file
        self.params = {
            'v': self.version
        }

    def get_list_region_shop(self):
        """
        Получить список регионов и магазинов.
        Для каждого магазина уникальный id, регион и адрес.
        :return: {'id': 1, 'region': Москва, 'address': 'Адрес'}
        """
        print('[INFO] Сбор регионов и магазинов')
        stores_url = f'{self.url}{self.version}/stores'
        info_shops = {'items': []}

        resp = requests.get(stores_url).json()

        if 'error' in resp.get('status'):
            code = resp.get('code')
            sys.exit(f'Error. Code: {code}')

        for data in resp.get('data'):
            save_data = {}
            save_data['id'] = data.get('code')
            save_data['name'] = data.get('name')
            city = self.find_cities_by_id(data.get('city'))
            save_data['region'] = city
            save_data['address'] = data.get('address')

            info_shops['items'].append(save_data)

        # Сохранение в saved_data/info_shops.json
        if self.save_data_to_file:
            with open('saved_data/info_shops.json', 'w') as f:
                json.dump(info_shops, f, ensure_ascii=False, indent=2)

        print('[INFO] Регионы и мазагины собраны.')

        return info_shops

    def find_cities_by_id(self, city_id=None, get_slug=None):
        """
        Получает словарь регионов и их ID
        :return: название города
        :return: короткое название
        """
        find_cities_url = f'{self.url}{self.version}/cities'
        cities = requests.get(find_cities_url).json()

        if 'error' in cities.get('status'):
            code = cities.get('code')
            sys.exit(f'Error. Code: {code}')

        # Сохранение в saved_data/cities_id.json
        if self.save_data_to_file:
            with open('saved_data/cities_id.json', 'w') as f:
                json.dump(cities, f, ensure_ascii=False, indent=2)

        # Получить название города
        if city_id:
            for city in cities.get('data'):
                if city.get('id') == city_id:
                    city_name = city.get('name')

                    return city_name

        # Получить короткое название
        if get_slug:
            for city in cities.get('data'):
                if city.get('name') == get_slug:
                    city_short = city.get('short')

                    return city_short

    def get_categories(self):
        """
        Получает список категорий товаров
        :return: {'category_id': 1, 'name': Вино}
        """
        print('[INFO] Сбор категорий.')

        categories_url = f'{self.url}{self.version}/categories'
        info_categories = {'items': []}

        resp = requests.get(categories_url).json()

        if 'error' in resp.get('status'):
            code = resp.get('code')
            sys.exit(f'Error. Code: {code}')

        for data in resp.get('data'):
            save_data = {}
            save_data['category_id'] = data.get('category_id')
            save_data['name'] = data.get('name').replace('\n', ' ')

            info_categories['items'].append(save_data)

        # Сохранение в saved_data/info_categories.json
        if self.save_data_to_file:
            with open('saved_data/info_categories.json', 'w') as f:
                json.dump(info_categories, f, ensure_ascii=False, indent=2)

        print('[INFO] Категории собраны.')

        if self.category:
            for c in info_categories['items']:
                if self.category == c.get('name'):
                    category = {'items': [{'category_id': c.get('category_id'), 'name': c.get('name')}]}

                    return category
        else:
            return info_categories

    def get_items_in_stock(self):
        """
        Список товаров в наличии по конкретному адресу магазина
        """
        product_url = 'https://simplewine.ru/api/v3/product/'  # Использует API V3
        get_categories = self.get_categories()
        short_city_name = self.find_cities_by_id(get_slug=self.address.split(',')[0].split()[0])
        get_slug_shop_name = self.get_list_region_shop()

        name_shop = ''
        for data in get_slug_shop_name.get('items'):
            if self.address in data.get('address'):
                name_shop = data.get('name')

        slug_name = slugify(name_shop, separator='_')

        items_stock = {'items': []}
        items_id = []

        old_time = time()

        headers = {
            'host': 'simplewine.ru',
            'x-device-code': 'yPIuMiKrIXkNm0eqFrO8Mg',  # эмулятор
            'x-city-code': short_city_name,
            'x-develop-device': 'Android',
            'x-develop-protocol': '30',
            'x-develop-version': '161',
            'x-mindbox-uid': '593d56cd-64da-427e-9614-c7937ecf8163',
            'accept-encoding': 'gzip',
            'user-agent': 'okhttp/3.14.7'
        }

        categories = get_categories.get('items')

        for data in categories:
            category_id = data['category_id']
            print(f'[INFO] Обрабатывается категория: {data["name"]}')
            products_url = f'https://simplewine.ru/api/v3/products/{category_id}/'  # смена категории

            page_param = {'page': 1}
            params = {
                'limit': 100,
                'show_filter': 'Y',
                'sort': 'our_choice',
                'filter': f'[store][0]{slug_name}'
            }

            resp = requests.get(products_url, headers=headers, params={**page_param, **params}).json()
            total_pages = resp.get('data').get('total_pages')  # все страницы

            # Проходим по всем страницам и собираем ID
            print('[INFO] Сбор ID')

            for page in range(1, total_pages + 1):
                page_param['page'] = page
                resp = requests.get(products_url, headers=headers, params={**page_param, **params}).json()

                if 'error' in resp.get('status'):
                    code = resp.get('code')
                    sys.exit(f'Error. Code: {code}')

                # Собираем ID товара
                if self.available:  # Только в наличии
                    print('[INFO] Сбор id только в наличии.')
                    for item in resp.get('data').get('items'):
                        if item['available']:
                            items_id.append(item['bitrix_id'])
                else:  # Все
                    print('Сбор всех id.')
                    for item in resp.get('data').get('items'):
                        for key, value in item.items():
                            if key == 'bitrix_id':
                                items_id.append(value)

                print(f'[INFO] Страниц собрано {page} из {total_pages}.')

                sleep(0.33)

        set_items_id = set(items_id)  # Удаляем дубликаты ID товаров
        print(f'[INFO] Затраченное время на сбор items_id: {time() - old_time}.\n'
              f' Собрано - {len(items_id)}, дубликатов - {len(items_id) - len(set_items_id)}. Уникальных - {len(set_items_id)}')

        # Собираем данные
        print('[INFO] Сбор данных.')
        pars_time = time()
        for item_id in set_items_id:
            url = product_url + str(item_id)
            resp_product = requests.get(url, headers=headers).json()

            if 'error' in resp_product.get('status'):
                code = resp_product.get('code')
                sys.exit(f'Error. Code: {code}')

            data = resp_product.get('data')

            save_data = {}
            save_data['name_store'] = name_shop
            save_data['city_store'] = self.address.split(',')[0].split()[0]
            save_data['address_store'] = ''.join(self.address.split()[1::])
            save_data['timestamp'] = datetime.now()
            save_data['article'] = data.get('article')
            save_data['barcode'] = ''  # Штрихкод
            save_data['name'] = data.get('name')
            save_data['drink_type'] = data.get('drink_type')
            save_data['price'] = data.get('price')
            save_data['old_price'] = data.get('old_price')
            save_data['date_discount'] = ''  # Дата начала/окончания скидки
            save_data['available'] = data.get('available')
            save_data['weight'] = ''  # Вес
            save_data['strenght'] = data.get('strenght')
            save_data['fatness'] = ''  # Жирность
            save_data['pack'] = data.get('pack')
            save_data['country'] = data.get('country').get('name')
            save_data['brand'] = data.get('manufacturer')
            save_data['manufacturer'] = data.get('manufacturer')
            save_data['url'] = data.get('url')
            save_data['url_img'] = 'https://simplewine.ru' + data.get('image')[0]

            items_stock['items'].append(save_data)
            sleep(0.33)

        print(f'[INFO] Затраченное время на сбор данных: {time() - pars_time}')
        print(save_data_to_csv(items_stock))


if __name__ == '__main__':
    parser = SimpleWine(version='v2',  # (в некоторых запросах используется v3)
                        shop_id=None,
                        available=True,  # Сбор товарор только в наличии
                        address='Обнинск, пр-кт. Ленина, дом 137, корп. 4, пом.7.',  # адресс магазина "Город, адрес"
                        category='Крепкие напитки',
                        save_data_to_file=False)  # Сохранить список регионов, категорий и городов?
    parser.get_items_in_stock()
