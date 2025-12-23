import json
import concurrent.futures
import os.path

import pandas
from openai import OpenAI

from conf import CONFIG

client = OpenAI(api_key=CONFIG.DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")


def process_invoice_with_deepseek(request_products: str, product_catalog: str):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": CONFIG.SYSTEM_PROMPT
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
            max_tokens=CONFIG.MAX_TOKENS,
            temperature=0.1,
            response_format={"type": "json_object"},
            stream=CONFIG.STREAM
        )

        result_json = json.loads(response.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return {"error": str(e)}


def get_nk():
    nk_data = pandas.read_excel(os.path.join(CONFIG.WORK_DIR, CONFIG.NK_FILE_PATH))

    result = []
    part = 0
    while part < len(nk_data):
        data_piece = nk_data[part:part + CONFIG.TABLE_LEN_PARTITION].to_markdown()
        result.append(data_piece)
        part += CONFIG.TABLE_LEN_PARTITION

    return result


def process_chunk(args):
    """Вспомогательная функция для многопоточности"""
    chunk, request_products, chunk_id = args
    print(f"Обрабатывается чанк {chunk_id + 1}")
    return process_invoice_with_deepseek(request_products, chunk)


def processing_data(data: list[dict]) -> None:
    products = []
    for obj in data:
        try:
            products.extend(obj["found_products"])
            products.extend(obj["not_found_items"])
        except Exception as e:
            print(e)
            print('=' * 20 + ' ERROR ' + '=' * 20)
    products_df = pandas.DataFrame(products)

    only_max_confidence_data = products_df.loc[products_df.groupby('requested_item')['confidence'].idxmax()]

    results = {
        'found_products_with_best_confidence': only_max_confidence_data.to_dict(orient='records'),
        'all_found_products': products,
        'responses': data.copy()
    }

    with open(os.path.join(CONFIG.WORK_DIR, "result.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    only_max_confidence_data.to_excel(os.path.join(CONFIG.WORK_DIR, 'products_with_best_confidence.xlsx'),
                                      index=False)
    products_df.to_excel(os.path.join(CONFIG.WORK_DIR, 'all_products.xlsx'), index=False)


def _processing_data(data: list[dict]):
    # Объединяем список всех найденных продуктов
    found_products = []
    not_processed_data = []
    for obj in data:
        if obj.get("found_products", None) is not None:
            found_products.extend(obj['found_products'])
        else:
            not_processed_data.extend(obj)

    found_products_df = pandas.DataFrame(found_products)  # **

    # Отбираем продукты с максимальной точностью
    only_max_confidence_data = found_products_df.loc[found_products_df.groupby('requested_item')['confidence'].idxmax()]

    results = {
        'found_products_with_best_confidence': only_max_confidence_data.to_dict(orient='records'),
        'all_found_products': found_products,
        'responses': data.copy()
    }

    with open(os.path.join(CONFIG.WORK_DIR, "result.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    only_max_confidence_data.to_excel(os.path.join(CONFIG.WORK_DIR, 'found_products_with_best_confidence.xlsx'),
                                      index=False)
    found_products_df.to_excel(os.path.join(CONFIG.WORK_DIR, 'all_found_products.xlsx'), index=False)


def main():
    nk_data = get_nk()

    request_products = """
    Линолеум шир.3м.- 6м.п.(18м2)
    Плинтус 2,5м – 9шт.
    Угол внутр. – 4шт.
    Угол наруж. – 2шт.
    Заглушки 4шт.
    Соединитель – 8шт.
    Дюбель-гвоздь 55мм- 100шт. - 200 шт. Шлифовка
    Профиль направляющий ПН-27*28 – 20шт.
    Профиль стоечный ПС 60*27 – 70шт.
    Саморез м/м 16мм – 1000шт.
    Подвес прямой – 200шт.
    
    Помещение весовой:
    Линолеум шир.3м.- 7м.п.(21м2) 3,5 м ширине
    Плинтус 2,5м – 14шт.
    Угол внутр. – 12шт.
    Угол наруж. – 6шт.
    Заглушки – 6шт.
    Соединитель – 4шт.
    """

    print(f"Всего чанков для обработки: {len(nk_data)}")

    # Подготавливаем аргументы для потоков
    chunk_args = [(chunk, request_products, i) for i, chunk in enumerate(nk_data)]

    # Многопоточная обработка
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.MAX_WORKERS) as executor:
        results = list(executor.map(process_chunk, chunk_args))

    print("Обрабатываем данные!")
    processing_data(results)
    print('--- COMPLETE ---')


if __name__ == '__main__':
    main()
