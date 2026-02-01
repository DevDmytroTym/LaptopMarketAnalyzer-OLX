import json 
from pathlib import Path

class ConfigManager:

    def __init__(self):
        self.path = Path(__file__).resolve().parent / "config.json"
        self.data = self.load()
    

    def load(self):
        if not self.path.exists():
            output = {
                    "models": set(),
                    "blacklist": set(),
                    "min_deal_score": 0.15,
                    "max_deal_score": 0.35,
                    "cheak_interval": 30,
                    "is_paused": False,
                    "url": "https://www.olx.pl/elektronika/komputery/laptopy/q-",
                    "selectors": {
                        "ad_list": {
                            "data-testid": "listing-grid"
                        },
                        "ad_card": {
                            "data-testid": "l-card"
                        },
                        "price": {
                            "data-testid": "ad-price"
                        },
                        "description": {
                            "data-testid": "ad_description"
                        },
                        "date": {
                            "data-testid": "ad-posted-at"
                        },
                        "place": {
                            "data-testid": "map-aside-section"
                        },
                        "ad_params": {
                            "data-testid": "ad-parameters-container"
                        },
                        "ad_card_title": {
                            "data-testid": "ad-card-title"
                        },
                        "offer_title": {
                            "data-testid": "offer_title"
                        },
                        "link": {
                            "data-testid": "ad-link"
                        },
                        "image_url": {
                            "data-testid": "swiper-image"
                        }
                    },
                    "token": "",
                    "chat_id": "",
                    "path_data": "data/laptops.csv"
                }
            return output
        
        with open(self.path, 'r') as f:
            json_load = json.load(f)
            json_load['models'] = set(json_load['models'])
            json_load['blacklist'] = set(json_load['blacklist'])
            return json_load
        
        
    def save(self): 
        data_to_save = dict(self.data)

        data_to_save['models'] = list(self.data.get('models', []))
        data_to_save['blacklist'] = list(self.data.get('blacklist', []))

        with open(self.path, 'w') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def add(self, name_setting: str, elements: list):
        self.data[name_setting].update(set(elements))
        self.save()
    
    def remove(self, name_setting: str, elements: list): 
        self.data[name_setting].difference_update(set(elements))
        self.save()


  