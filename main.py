import json
from pprint import pprint

import pandas
from openai import OpenAI

from conf import Config

client = OpenAI(api_key=Config.DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")


def process_invoice_with_deepseek(request_products: str, product_catalog: str):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": Config.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
                    Товары из накладной:
                    "{request_products}"
                 
                    Проанализируй список товаров из накладной и найди товары в этом каталоге:
                    КАТАЛОГ ТОВАРОВ:
                    {product_catalog}
                    
                    Найди соответствия и верни в указанном JSON формате.""",
            }
        ],
        max_tokens=4000,
        temperature=0.1,
        response_format={"type": "json_object"},

        stream=Config.STREAM
    )

    result_json = json.loads(response.choices[0].message.content)
    return result_json


def main():
    nk_data = pandas.read_excel(Config.NK_FILE_PATH).to_markdown(index=False)

    request_products = """Анкерный болт с гайкой 12x150мм. 200шт 
                    Анкерный болт с гайкой 10x77мм 100шт 
                    Аквапанель наружная (Кнауф) 12,5мм 1,2x2,4м /30
                    Мешки мусорные 20л"""

    result = process_invoice_with_deepseek(request_products, nk_data)
    pprint(result)


if __name__ == '__main__':
    main()
