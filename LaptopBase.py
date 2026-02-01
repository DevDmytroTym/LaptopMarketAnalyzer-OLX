import pandas as pd
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Union
import logging

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
            if self.df.empty:
                self.df = new_bd
                self.save()
                return 
            
            self.df.drop_duplicates(subset=['id'], keep='first', inplace=True)
            new_bd.drop_duplicates(subset=['id'], keep='first', inplace=True)

            self.df['id'] = self.df['id'].astype(str)
            new_bd['id'] = new_bd['id'].astype(str)

            self.df.set_index('id', inplace=True)
            new_bd.set_index('id', inplace=True)

            if 'spam' in self.df.columns and 'spam' in new_bd.columns:
                new_bd.update(self.df[['spam']])
            
            if 'is_new' in self.df.columns and 'is_new' in new_bd.columns:
                new_bd.update(self.df[['is_new']])

            new_bd.reset_index(inplace=True)

            self.df = new_bd
            self.save()

            logging.info(f"База даних успішно оновлена.")
            
        except Exception as e:
            logging.error(f"Помилка оновлення бази: {e}",exc_info=True)
            if 'id' not in self.df.columns: 
                 self.df.reset_index(inplace=True)


    def get_valid_index(self, index: int, direction: int = 1) -> int:
        try:
            if self.df.empty:
                return 0
            
            max_idx = len(self.df) - 1

            curr = max(0,min(index,max_idx))

            while 0 <= curr <= max_idx:
                if not self.df.iloc[curr].get('spam',True):
                    return curr
                curr += direction

            for i in range(max_idx)[::direction]:
                if not self.df.iloc[i].get('spam',False):
                    return i
                   
            return 0
            
        except:
            return 0
        

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

