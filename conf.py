import enum
import os
from pathlib import Path

import pandas
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Region(enum.Enum):
    BRN: str = 'Филиал Барнаул'
    BIY: str = 'Филиал Бийск'
    MAY: str = 'Филиал Майма'
    CB: str = 'Центральный офис'
    VIB: str = 'Филиал Выбор'

    ANY: str = 'ANY'


class Config:
    PREPROCESSING_REQUEST: bool = True

    MAX_WORKERS: int = 10
    TABLE_LEN_PARTITION: int = 1000

    DEEP_SEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY')

    MAX_TOKENS: int = 5000
    TEMPERATURE: float = 0.7
    STREAM: bool = False  # Для потокового ответа установить True

    NK_FILE_PATH: str = r'Номенклатура.xlsb'

    SYSTEM_PROMPT_FILE_PATH: str = r'SYSTEM_PROMPT.txt'

    BASE_DIR: str | Path = Path(__file__).resolve().parent
    WORK_DIR: str | Path = os.path.join(BASE_DIR, 'WORK_DIR')

    def __init__(self):
        self.__system_prompt: str | None = None

    @property
    def SYSTEM_PROMPT(self):
        if self.__system_prompt is None:
            with open(self.SYSTEM_PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
                self.__system_prompt = f.read()
            self.__system_prompt += f"""
            ---
            ## Пример сопоставленных номенклатур в табличном виде 
            {pandas.read_excel(os.path.join(self.WORK_DIR, 'Сопоставления очищенные.xlsx')).to_markdown()}
            
            ВАЖНО! ЭТО ЛИШЬ ПРИМЕР УЖЕ СОПОСТАВЛЕННОЙ НОМЕНКЛАТУРЫ! 
            НЕ ПОДТЯГИВАЙ ДАННЫЕ ДЛЯ СОПОСТАВЛЕНИЯ ИЗ ЭТОГО СПИСКА!
            ---
            """
        return self.__system_prompt


CONFIG = Config()
