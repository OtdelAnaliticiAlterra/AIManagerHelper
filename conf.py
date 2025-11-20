import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Config:
    MAX_WORKERS: int = 8
    TABLE_LEN_PARTITION: int = 1400

    DEEP_SEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY')

    MAX_TOKENS: int = 5000
    TEMPERATURE: float = 0.7
    STREAM: bool = False  # Для потокового ответа установить True

    NK_FILE_PATH: str = r'Номенклатура_2.xlsb'

    SYSTEM_PROMPT: str = """
    ЗАБУДЬ ВСЁ!!!
    
    Ты помощник менеджера по продажам.
    Проанализируй сканированную накладную и найди соответствующие товары в каталоге.
    ВЕРНИ ОТВЕТ ТОЛЬКО В JSON ФОРМАТЕ без каких-либо дополнительных текстов.
    Формат ответа:
    
    {
        "found_products": [
            {
                "requested_item": "название из накладной",
                "matched_product": "найденный товар из каталога",
                "product_code": "ID из каталога",
                "quantity": 2,
                "confidence": 0.95,
                "reason": "почему товары соответствуют"
            }
        ],
        "not_found_items": ["товары которые не найдены"],
        "total_found": 0,
        "total_requested": 0
    }
    
    ПРИМЕР:
    
    {
        "found_products": [
            {
                "requested_item": "Сетка оцинкованная фЗВр-І яч.50*50 шириной 200мм",
                "matched_product": "Сетка ЦПВС 1,25х15м ячейка 50х20мм 0,5мм оцинкованная",
                "product_code": "0А-00017167",
                "quantity": 124.52,
                "confidence": 0.85,
                "reason": "Совпадение по типу товара (сетка оцинкованная), ячейке (50х50мм в накладной и 50х20мм в каталоге - частичное совпадение), и ширине (200мм в накладной и 1,25м = 1250мм в каталоге - неполное совпадение, но оба параметра указывают на размеры сетки)"
            }
        ],
        "not_found_items": [
            "Анкер распорный М8х70",
            "Газобетон 200х250х625",
            "Клей для ячеистого бетона",
            "Кирпич силикатный СУРПо -М100/F25/2,0 по ГОСТ 379-2015",
            "Утеплитель экструдированный пенополистирол 50мм"
        ],
        "total_found": 1,
        "total_requested": 6
    },
    
    """
