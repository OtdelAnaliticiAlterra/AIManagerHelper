import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Config:
    DEEP_SEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY')

    MAX_TOKENS: int = 500,
    TEMPERATURE: float = 0.7,
    STREAM: bool = False  # Для потокового ответа установить True

    NK_FILE_PATH: str = r'Номенклатура.xlsx'

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
    """
