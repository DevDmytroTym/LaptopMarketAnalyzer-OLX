import pandas as pd
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Union

@dataclass
class LaptopItem:

    id: str
    offer_title: str 
    link: str
    price: Union[int, str, None] = None
    category: str = ""
    place: str = ""
    date: str = ""
    image_link: str = ""
    description: str = ""
    ram: int = None
    cpu: str = ""
    gpu: str = ""
    disk_v: int = None
    spam: bool = False
    is_new: bool = True  

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Поле '{key}' не знайдено в LaptopItem")    
    
    def __setitem__(self, key, value):
        allowed_fields = {f.name for f in fields(self)}
        if key in allowed_fields:
            setattr(self, key, value)
        else:
            raise KeyError(f"Спроба записати в '{key}', але в датакласі є лише: {allowed_fields}")


class LaptopBase:
    def __init__(self, path: str):
        self.path = Path(path)
        self.df = self.load()

    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, key: str) -> pd.Series:
        return self.df[key]

    def load(self):
        if not self.path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(self.path)

        except Exception as e:
            return pd.DataFrame()

    def save(self):
        if not self.path.exists():
            pd.DataFrame().to_csv(self.path, index=False)

        self.df.to_csv(self.path,index=False)

    def reload(self):
        self.df = self.load()
        self.df = self.df.reset_index(drop=True)

    def update(self):
        try:
            new_bd = self.load()
            if new_bd.empty:
                return

            missing_cols = [col for col in self.df.columns if col not in new_bd.columns]
            for col in missing_cols:
                new_bd[col] = "" 

            self.df.set_index('id', inplace=True)
            new_bd.set_index('id', inplace=True)

            new_bd.update(self.df)

            new_bd = new_bd.reset_index()
            self.df = new_bd.copy()

            self.save()
            
        except Exception as e:
            print(f"Помилка оновлення бази: {e}")


    def ignore_spam(self):
        try:
            self.df = self.df[~self.df['spam']]
            self.df = self.df.reset_index(drop=True)
        except:
            pass

    def add_to_spam(self, index: int):
        try:
            self.df.loc[index,'spam'] = True
        except:
            pass

    def is_new(self, index: int) -> bool:
        if 'is_new' not in self.df:
           return None

        return self.df['is_new'][index]
    
    def make_as_seen(self, index: int):
        if 'is_new' not in self.df:
            return None
            
        self.df.loc[index,'is_new'] = False

