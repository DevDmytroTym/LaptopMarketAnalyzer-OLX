import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
import random
import logging
from fake_headers import Headers
from rapidfuzz import process, fuzz
from concurrent.futures import ThreadPoolExecutor
from config_manager import ConfigManager
from LaptopBase import LaptopItem
from itertools import repeat


config = ConfigManager()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

selectors = config.data["selectors"]
target_models = list(map(lambda x: x.lower(),config.data['models']))
black_list = list(map(lambda x: x.lower(), config.data['blacklist']))
headers = [str(Headers()) for x in range(15)]

#функція для отримання html сторінки з оголошенням 
def fetch_html(url: str, headers: list) -> tuple[str, str]:

    """
    Виконує безпечний HTTP-запит до сайту з імітацією користувача.

    Args:
        url (str): Посилання на сторінку.
        headers (list): Список User-Agent заголовків.

    Returns:
        tuple[str, str]: Повертає (html_text, actual_url). 
                         Якщо помилка - повертає (None, None).
    """

    try:         
        header = {'User-Agents': random.choice(headers)} 
        time.sleep(random.randint(1,5))

        response = requests.get(url, headers = header, timeout=10)

        if response.status_code == 403:
            logging.warning(f"Доступ заборонено (403) для {url}. Можливо, IP заблоковано.")
            return None, None
        elif response.status_code == 429:
            logging.warning(f"Занадто багато запитів (429). Треба збільшити паузу!")
            return None, None
        
        response.raise_for_status()
        return response.text,response.url

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP помилка для {url}: {e}")
    except requests.exceptions.ConnectionError:
        logging.error(f"Помилка з'єднання з мережею при спробі відкрити {url}")
    except requests.exceptions.Timeout:
        logging.error(f"Таймаут (10 сек) при завантаженні {url}")
    except Exception as e:
        logging.error(f"Непередбачена помилка: {e}", exc_info=True)
        
    return None, None

#функція для витягування ід з посилання на оголошення
def extract_advertisement_id(url: str) -> str:

    """
    Витягує унікальний ID оголошення з URL.
    
    Args:
        url (str): Посилання на оголошення.
    
    Returns:
        str: ID оголошення або None, якщо не знайдено.
    """

    if not isinstance(url, str):
        logging.error(f"Критична помилка типу: очікувався str, отримано {type(url)} (значення: {url})",exc_info=True)
        return None

    try:

        match = re.search(r'-ID([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        logging.warning(f"ID не знайдено у посиланні: {url}")
        return None

    except Exception as e:
        logging.error(f"Непередбачена помилка при регулярному виразі: {e}",exc_info=True)
        return None

#функція для парсингу сторінки оголошень OLX 
def parse_and_save(html: str, selectors: dict) -> list[LaptopItem]:

    """
    Парсить HTML сторінку каталогу і створює список об'єктів LaptopItem.
    """

    items_list = []

    try:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', attrs=selectors.get("ad_card",{}))
        
        if not cards:
            logging.warning("На сторінці не знайдено жодної картки товару.")
            return []
        
    except Exception as e:
        logging.error(f"Критична помилка при ініціалізації BeautifulSoup: {e}", exc_info=True)
        return []

    for card in cards:
        try:

            #Витягуємо посилання на товар
            link_tag = card.find("a")
            if not link_tag:
                continue
            
            link = "https://www.olx.pl" + link_tag.get('href', '')
                
            #Отримуємо ід товару з посилання 
            id = extract_advertisement_id(link)
            
            #Витягуємо заголовок об'яви і чистимо її від зайвих символів
            title_tag = card.find('h4')

            if not title_tag:
                logging.warning(f"Не знайдено заголовок для картки {link}")
                title = "Без назви"
            else:    
                title = title_tag.get_text(strip=True) 

            

            price_tag = card.find('p', attrs=selectors.get('price',{}))
            if not price_tag:
                logging.warning(f"Не знайдено ціни для товару {link}")
                price = 0
            else:    
                price = price_tag.get_text(strip=True) 

            laptop = LaptopItem(id=id, offer_title=title,link=link,price=price)

            items_list.append(laptop)
            
        except AttributeError as e:
            logging.warning(f"Пропущено картку через відсутність атрибута: {e}")
            continue

        except Exception as e:
            logging.error(f"Непередбачена помилка при обробці картки: {e}", exc_info=True)
    
    return items_list

#функція отримання цільових оголошень з OLX
def target_scrap_OLX(url: str, headers: list, targets: list, selectors: dict) -> pd.DataFrame:

    """
    Основна функція сканування. Проходить по сторінках оголошень для заданих моделей.
    
    Args:
        targets (list): Список моделей (або одна модель у списку) для пошуку.
    """

    all_laptops = []
    laptops_df = pd.DataFrame()

    for model in targets:

        logging.info(f"Почався пошук моделі: {model}.")

        for i in range(1,26):
            try:
                link = url + f"{model.replace(' ', '%20')}/?page={i}"

                html, res_link = fetch_html(link, headers)

                if html is None:
                    logging.warning(f"Пропущено сторінку {i} для {model} через помилку завантаження.")
                    continue
                
                data = parse_and_save(html, selectors)
                if not data or ((res_link != link) and i!=1):
                    logging.info(f"Досягнуто кінець списку для {model} на сторінці {i}.")
                    break
                
                else:
                    all_laptops.extend(data)
                    logging.info(f"Сторінка {i} ({model}): додано {len(data)} оголошень.")

            except Exception as e:
                logging.warning(f"Помилка при зчитуванні сторінки {i} для товара {model}")

    models_text = ", ".join(targets)

    logging.info(f"Пошук моделей {models_text} завершено. Всього знайдено: {len(all_laptops)}")

    try:
        if not all_laptops:
            logging.warning(f"Жодної з моделей {models_text} не було знайдено.")
            return pd.DataFrame()
        
        laptops_df = pd.DataFrame(all_laptops)
        laptops_df = laptops_df.drop_duplicates(subset=['id'])
    
    except Exception as e:
        logging.error(f"Критична помилка при створенні DataFrame: {e}", exc_info=True)

    return laptops_df



#функція для категоризації товарів по цільовим назвам
def get_category(text: str, target: list) -> str:

    """
    Визначає модель ноутбука на основі заголовка за допомогою Fuzzy Matching.
    
    Args:
        title (str): Заголовок оголошення.
        target (list): Список шуканих моделей.
    
    Returns:
        str: Назва моделі або "unKnown".
    """

    try:
        if not text or not isinstance(text, str):
            return "unKnown"
        
        if not target or not isinstance(target, list):
            logging.warning(f"get_category отримала невірний тип target: {type(target)}")
            return "unKnown"

        list_models = [m[0] if isinstance(m, list) else m for m in target]

        cat_res = process.extractOne(text, list_models, scorer=fuzz.token_set_ratio)

        if cat_res and cat_res[1] > 90:
            return cat_res[0]
            
        return "unKnown"
    
    except Exception as e:
        logging.error(f"Помилка при класифікації '{text}': {e}")
        return "unKnown"

#функція перевірки тексту на наявність слів з чорного списку видає на виход True або False
def is_spam(text: str, black_list: list) ->  bool:

    """
    Перевіряє текст на наявність стоп-слів (спаму).
    
    Args:
        text (str): Опис або заголовок.
        black_list (list): Список заборонених слів.
    
    Returns:
        bool: True, якщо знайдено спам.
    """

    try:
        if not text or not isinstance(text, str):
            return False
        
        if not black_list or not isinstance(black_list, list):
            return False

        spam_res = process.extractOne(text, black_list, scorer=fuzz.partial_ratio)

        if spam_res and spam_res[1] > 80:
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Помилка при перевірці на спам '{text}': {e}")
        return False

#функція для очистки ціни від валюти
def clean_price(price: str) -> int:

    """
    Очищає рядок ціни від зайвих символів і перетворює в число.
    
    Args:
        price (str): "Сира" ціна (наприклад, "12 000 грн").
    
    Returns:
        int: Чиста ціна (12000) або 0.
    """

    if isinstance(price, (int, float)):
        return int(price)

    if not price or not isinstance(price, str):
        logging.debug(f"Нетипове значення ціни: {price}")
        return 0
    
    try:
        digits = re.sub(r'\D', '', price)
        return int(digits) if digits else 0
    
    except Exception as e:
        logging.error(f"Помилка при очистці ціни '{price}': {e}")
        return 0



def cleaner(data: pd.DataFrame, black_list: list) -> pd.DataFrame:

    """
    Фільтрує DataFrame: видаляє спам та валідує типи даних.
    """

    clean_data = pd.DataFrame()

    if data.empty or not isinstance(data,pd.DataFrame):
        logging.warning("Cleaner отримав порожній або некоректний DataFrame.")
        return pd.DataFrame()
    
    start_len = len(data)
    logging.debug(f"Початкова кількість оголошень: {start_len}")

    try:

        clean_data = data.copy()
        
        if 'id' in clean_data.columns:
            clean_data.drop_duplicates(subset=['id'], keep='first', inplace=True)
            clean_data.reset_index(inplace=True,drop=True)

        else:
            logging.warning("Cleaner отримав некоректний DataFrame, відсутня колонка 'id'.")
            return pd.DataFrame()

        if black_list:
            clean_data = data[~data['offer_title'].apply(lambda x: is_spam(x, black_list))]
            clean_data.reset_index(drop=True, inplace=True)    
        
        clean_data['price'] = clean_data['price'].apply(clean_price)        
           
    except Exception as e:
        logging.error(f"Помилка при очищенні DataFrame: {e}",exc_info=True)
        return data

    end_len = len(clean_data)
    logging.debug(f"Після очищення залишилось: {end_len} (видалено {start_len - end_len})")

    return clean_data


#функція для отримання деталей з html сторінки оголошення
def fetch_and_parse_advert(url: str, headers: list, target_models: list, selectors: dict) -> LaptopItem:

    """
    Глибокий парсинг: заходить в оголошення і дістає деталі (RAM, CPU, Опис).
    """

    ram, disk_v, cpu = 0, 0, ""
    description, img_url, title = "", "", "Без назви"

    trash_pattern = r'[!\?\(\)\[\]@,\.\;\/\\"\']'
    
    try:
        html, _ = fetch_html(url, headers)
        if not html:
            return LaptopItem(id="error", offer_title="Page not found", link=url)

        soup = BeautifulSoup(html, 'html.parser')


        container_params = soup.find('div', selectors.get('ad_params', {}))
        if container_params:
            raw_params = container_params.get_text(" ", strip=True)
            
            ram_match = re.search(r'RAM:.*?(\d+)', raw_params)
            ram = int(ram_match.group(1)) if ram_match else 0

            disk_match = re.search(r'dysku:.*?(\d+)', raw_params)
            disk_v = int(disk_match.group(1)) if disk_match else 0

            cpu_match = re.search(r'procesora:\s(.*\d)\s', raw_params) 
            cpu = cpu_match.group(1).strip() if cpu_match else ''
        else:
            logging.debug(f"На сторінці {url} не знайдено блок параметрів.")

        container_desc = soup.find('div', selectors.get('description', {}))
        if container_desc:
            description = container_desc.get_text(" ", strip=True)

        container_img = soup.find('img', selectors.get('image_url', {}))
        if container_img:
            img_url = container_img.get('src', '')
        
        if not img_url or "https://" not in img_url:
            img_url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRcCBHgbS23kyBw2r8Pquu19UtKZnrZmFUx1g&s'


        container_title = soup.find('div', selectors.get('offer_title', {})) 
        if container_title:
            raw_title = container_title.get_text(strip=True)

        clean_title = re.sub(trash_pattern, " ", raw_title)
            
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()

        category = get_category(clean_title.lower(), target_models)

        
        return LaptopItem(
            id=extract_advertisement_id(url),
            offer_title=title,
            link=url,
            category=category,
            image_link=img_url, 
            description=description, 
            ram=ram,
            disk_v=disk_v,
            cpu=cpu
        )
       
    except Exception as e:
        logging.error(f"Помилка при отриманні даних про товар {url}: {e}", exc_info=True)
        return LaptopItem(id="error", offer_title="Page not found", link=url)

        
def get_details(links: list, headers: list, target_models: list, selectors: dict) -> pd.DataFrame:

    """
    Запускає багатопотоковий парсинг деталей для списку посилань.
    """

    items_details = [] 
        
    with ThreadPoolExecutor(max_workers=6) as executor:
        items_details = list(executor.map(
        fetch_and_parse_advert, 
        links, 
        repeat(headers), 
        repeat(target_models), 
        repeat(selectors)
    ))
    
    valid_dicts = [
        item.to_dict() for item in items_details 
        if item is not None and item.id != "error"
    ]

    new_details = pd.DataFrame(valid_dicts)
    
    return new_details


def run_scraper():

    """
    Головна функція (Entry Point). Запускає повний цикл оновлення бази.
    """

    laptops = pd.DataFrame()

    try:

        config = ConfigManager()

        models = config.data.get('models', [])
        blacklist = config.data.get('blacklist', [])
        site_url = config.data.get('url')
        path_to_save = config.data.get('path_data', 'data/laptops.csv')
        selectors = config.data.get('selectors')
        headers = [str(Headers()) for x in range(15)]

        target_models = [[model.lower()] for model in models]
        black_list = [bl.lower() for bl in blacklist]

        with ThreadPoolExecutor(max_workers=6) as executor:
            results_list = list(executor.map(
                target_scrap_OLX,
                repeat(site_url),        
                repeat(headers), 
                target_models, 
                repeat(selectors)))
        
        if results_list:
            dirt_data = pd.concat(results_list, ignore_index=True)
        else:
            logging.warning(f"Не знайдено жодних оголошень для моделей: {models}")
            return False            
        
        clean_data = cleaner(dirt_data, black_list)
        if clean_data.empty:
            logging.warning("Після очищення даних не залишилося жодного оголошення.")
            return False


        links = list(clean_data['link'])

        logging.info(f"Отримуємо деталі з кожного оголошення.")
        details_df = get_details(links, headers, target_models, selectors)

        clean_data.drop_duplicates(subset=['id'], keep='first', inplace=True)
        details_df.drop_duplicates(subset=['id'], keep='first', inplace=True)

        clean_data.set_index('id', inplace=True)
        details_df.set_index('id', inplace=True)

        cols_to_exclude = ['offer_title', 'price']

        clean_data.update(details_df.drop(columns=cols_to_exclude, errors='ignore'))

        clean_data.reset_index(inplace=True)

        laptops = clean_data

        if laptops.empty:
            logging.error(f"При спробі отримати деталі вивникла помилка.",exc_info=True)
            laptops.to_csv(path_to_save, index=False)
            return None

        laptops.to_csv(path_to_save, index=False)

        logging.info(f"Скрапінг успішно завершено. Збережено {len(laptops)} оголошень.")
        return True

    except Exception as e:
        logging.error(f"Критична помилка в run_scraper: {e}", exc_info=True)
        return False    


if __name__ == "__main__":
    run_scraper()
    pass
