import pandas as pd
import logging
from config_manager import ConfigManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def find_hot_deals():

    """
    Аналізує зібрані дані про ноутбуки для пошуку найбільш вигідних пропозицій на ринку.
    
    Алгоритм роботи:
    1. Завантажує дані з основної бази (laptops.csv).
    2. Фільтрує "сміття": видаляє спам та оголошення з невизначеною моделлю.
    3. Групує ноутбуки за ідентичними характеристиками (модель, RAM, диск, процесор).
    4. Розраховує медіанну ціну для кожної групи (за умови, що в групі > 4 оголошень).
    5. Обчислює Deal Score (відсоток відхилення ціни від медіани).
    6. Відбирає "Гарячі пропозиції" — оголошення, ціна яких нижча за ринкову на 15-35%.
    7. Зберігає результат у окремий файл (hot_deals.csv) для подальшої відправки ботом.
    """

    config = ConfigManager()
    path_data = config.data.get("path_data", "data/laptops.csv")

    min_discont = config.data["min_deal_score"]
    max_dictont = config.data["max_deal_score"]
    
    try:
        raw_data = pd.read_csv(path_data)
       
        mask = (raw_data.get("spam", False) != True) & (raw_data['category'] != 'unKnown') & (raw_data['price'] > 0)
        target_data = raw_data[mask]

        group_cols = ['category', 'ram', 'disk_v']
        stats = target_data.groupby(group_cols, as_index=False)['price'].agg(['median', 'count'])
        
        target_data = target_data.merge(stats, on=group_cols)
        

        target_data = target_data[target_data['count'] > 4].copy()
        target_data['deal_score'] = 1 - (target_data['price'] / target_data['median'])

        hot_deals = target_data[target_data['deal_score'].between(min_discont, max_dictont)].copy()
        
        hot_deals.loc[:, "is_new"] = True
        hot_deals = hot_deals.sort_values(by=['deal_score','category'], ascending=False)

        hot_deals.reset_index(drop=True, inplace=True)
        hot_deals.to_csv('data/hot_deals.csv', index=False)
        logging.info(f"Знайдено {len(hot_deals[hot_deals['is_new']==True])} гарячих пропозицій!")
        return hot_deals
        
    except Exception as e:

        logging.error(f"Помилка аналізу: {e}")

find_hot_deals()