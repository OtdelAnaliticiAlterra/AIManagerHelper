import datetime
import json
import concurrent.futures
import os.path
import re

import pandas
from openai import OpenAI

from conf import CONFIG, Region

client = OpenAI(api_key=CONFIG.DEEP_SEEK_API_KEY, base_url="https://api.deepseek.com")


def clean_text_for_json(text: str) -> str:
    """Очищает текст для безопасного использования в JSON/промптах"""
    # Заменяем кавычки на их HTML-эквиваленты или экранируем
    text = text.replace('"', "'")  # или используем text.replace('"', '\\"')
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\s+', ' ', text)
    # Экранируем другие потенциально опасные символы
    text = text.replace('\n', ' ').replace('\r', ' ')
    # Удаляем непечатаемые символы
    text = ''.join(char for char in text if char.isprintable())
    return text.strip()


def normalize_request(request: str) -> str:
    """
    Нормализует запрос клиента в Markdown таблицу
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """
                    Ты помощник менеджера по продажам. Твоя задача, привести не структурированную заявку клиента в  
                    читаемый табличный вид.
                    
                    Преобразуй запрос в Markdown таблицу с колонками:

                    | № | Товар | Количество | Единица измерения | Параметры | Примечания |
                    |---|-------|------------|-------------------|-----------|------------|

                    КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

                    1. КАЖДЫЙ отдельный товар или размер - ОТДЕЛЬНАЯ строка в таблице
                       Пример: "Шпатель 100 мм. - 5 шт. 300 мм. - 5 шт." → 
                       ДВЕ строки:
                       | 1 | Шпатель | 5 | шт | 100 мм | - |
                       | 2 | Шпатель | 5 | шт | 300 мм | - |

                    2. СЛОЖНЫЕ записи с "+" - разделяй на несколько строк
                       Пример: "СВП 1,4 мм. 1000 шт. + клинья" → 
                       ДВЕ строки:
                       | 1 | СВП | 1000 | шт | 1,4 мм | - |
                       | 2 | Клинья для СВП | 1000 | шт | - | Для СВП 1,4 мм |

                    3. Единицы измерения стандартизируй:
                       - шт, м, м², кг, уп, рулон, мешок, л, мм
                       - "упаковки" → "уп"
                       - "метров" → "м"
                       - "литров" → "л"
                       - "миллиметров" → "мм"

                    4. Сохраняй ВСЕ параметры в колонке "Параметры":
                       - Толщину: "1,4 мм"
                       - Диаметр: "125 мм"  
                       - Длину: "2 м"
                       - Объем: "12 л"
                       - Диапазон: "10-12 мм"

                    5. Колонка "Примечания" - для:
                       - Назначения: "для шпаклевки", "для краски"
                       - Материала: "пластик", "сталь"
                       - Особенностей: "малярные", "строительные"
                       - Если нет примечаний - ставь "-"

                    6. Если бренд явно не указан - не добавляй колонку бренда

                    7. Нумерация с 1

                    8. Если параметры указаны в названии - выноси их в колонку "Параметры"
                       Пример: "СВП 1,4 мм" → Товар: "СВП", Параметры: "1,4 мм"

                    ВЕРНИ ТОЛЬКО MARKDOWN ТАБЛИЦУ БЕЗ ЛЮБЫХ ДОПОЛНИТЕЛЬНЫХ КОММЕНТАРИЕВ."""
                },
                {
                    "role": "user",
                    "content": request
                }
            ],
            max_tokens=CONFIG.MAX_TOKENS,
            temperature=0.1
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Ошибка при нормализации запроса: {e}")
        return f"Ошибка: {str(e)}"


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
                        "{clean_text_for_json(request_products)}"

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


def get_nk(region: Region):
    nk_data = pandas.read_excel(os.path.join(CONFIG.WORK_DIR, CONFIG.NK_FILE_PATH))

    select_fields = [
        "Код",
        "Наименование",
        "Вес",
        "Объем",
        "Длина",
        "Площадь",
    ]

    region_fields = [
        "Филиал Барнаул",
        "Филиал Бийск",
        "Филиал Выбор",
        "Филиал Майма",
        "Центральный офис",
    ]

    acceptable_classes = [
        "B - класс",
        "A - класс",
        "C - класс",
        "Новинка",
    ]

    if region == Region.ANY:
        select_fields.extend(region_fields)
        mask = nk_data[region_fields].isin(acceptable_classes).any(axis=1)
    else:
        select_fields.append(str(region.value))
        mask = nk_data[region.value].isin(acceptable_classes)

    nk_data = nk_data[mask]
    nk_data = nk_data[select_fields]

    nk_data.to_excel('TEST_BRN.xlsx', index=False)

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


def get_request() -> str:
    with open(os.path.join(CONFIG.WORK_DIR, "REQUEST.md"), "r", encoding="utf-8") as f:
        data = f.read()
        return data


def processing_request() -> str:
    data = get_request()
    processed_data = normalize_request(data)
    with open(os.path.join(CONFIG.WORK_DIR, "REQUEST.md"), "w", encoding="utf-8") as f:
        f.write(processed_data)
    return processed_data


def main():
    start = datetime.datetime.now()

    nk_data = get_nk(CONFIG.REGION)

    if CONFIG.PREPROCESSING_REQUEST:
        print('--- Идет обработка запроса ---')
        processing_request()
        input('Проверьте корректность обработанного запроса.\n'
              'Если какие-то моменты не устраивают - исправьте вручную.\n'
              'Когда будете готовы нажмите Enter на клавиатуре')

    request_products = get_request()

    print(f"Всего чанков для обработки: {len(nk_data)}")

    # Подготавливаем аргументы для потоков
    chunk_args = [(chunk, request_products, i) for i, chunk in enumerate(nk_data)]

    # Многопоточная обработка
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG.MAX_WORKERS) as executor:
        results = list(executor.map(process_chunk, chunk_args))

    print("Обрабатываем данные!")
    processing_data(results)
    print('--- COMPLETE ---')
    print(f'Общее время обработки {datetime.datetime.now() - start}')


if __name__ == '__main__':
    main()
