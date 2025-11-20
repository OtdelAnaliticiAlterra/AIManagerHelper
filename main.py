import json
from pprint import pprint
import concurrent.futures
import pandas
from openai import OpenAI
from conf import Config

client = OpenAI(api_key=Config.DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")


def process_invoice_with_deepseek(request_products: str, product_catalog: str):
    try:
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
            max_tokens=Config.MAX_TOKENS,
            temperature=0.1,
            response_format={"type": "json_object"},
            stream=Config.STREAM
        )

        result_json = json.loads(response.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return {"error": str(e)}


def get_nk():
    nk_data = pandas.read_excel(Config.NK_FILE_PATH)

    result = []
    part = 0
    while part < len(nk_data):
        data_piece = nk_data[part:part + Config.TABLE_LEN_PARTITION].to_markdown()
        result.append(data_piece)
        part += Config.TABLE_LEN_PARTITION

    return result


def process_chunk(args):
    """Вспомогательная функция для многопоточности"""
    chunk, request_products, chunk_id = args
    print(f"Обрабатывается чанк {chunk_id + 1}")
    return process_invoice_with_deepseek(request_products, chunk)


def main():
    nk_data = get_nk()

    request_products = """
    Анкер распорный М8х70	шт	83
    Газобетон 200х250х625	шт	427 / м2	13,35
    Клей для ячеистого бетона	кг	650
    Сетка оцинкованная фЗВр-І яч.50*50 шириной 200мм	м.п	124,52
    Кирпич силикатный СУРПо -М100/F25/2,0 по ГОСТ 379-2015	шт	217
    Утеплитель экструдированный пенополистирол 50мм	м2	200
    """

    print(f"Всего чанков для обработки: {len(nk_data)}")

    # Подготавливаем аргументы для потоков
    chunk_args = [(chunk, request_products, i) for i, chunk in enumerate(nk_data)]

    # Многопоточная обработка
    with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        results = list(executor.map(process_chunk, chunk_args))

    print("Обработка завершена!")
    pprint(results)

    # Сохраняем результаты
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
