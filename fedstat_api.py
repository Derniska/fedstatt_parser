from typing import List, Optional 
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from io import BytesIO
from functools import cached_property

class FedStatIndicator:
    def __init__(self, indicator_id):
        self.id = indicator_id
        self._raw_data = None

    @cached_property
    def _filters_raw(self):
        """Получает сырые данные фильтров"""
        html = requests.get(f'https://www.fedstat.ru/indicator/{self.id}')
        if html.status_code == 200:
            soup = BeautifulSoup(html.text, "lxml")
            script = soup.find_all("script")[11].text
            pattern = r"filters:\s*(\{.*?\})(?=\s*,\s*left_columns)"
            match = re.search(pattern, script, re.DOTALL).group(0)
            filters = "{" + match + "}"
            filters = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', filters)
            filters = filters.replace("'", '"')
            filters_raw = json.loads(filters)['filters']
            return filters_raw
        else:
            raise requests.RequestException(f"Ошибка HTTP-запроса")

    @cached_property
    def filter_codes(self):
        """
        Возвращает код и название показателя, доступного для фильтрации
        """
        
        filter_codes = {key : self._filters_raw[key]['title'] for key in list(self._filters_raw.keys())[1:]}
        return filter_codes

    @cached_property
    def indicator_title(self):
        """
        Возвращает название индикатора
        """
        return list(self._filters_raw.get("0").get("values").values())[0]["title"]

    def get_filter_values(self):
        """
        Возвращает названия и коды доступных значений для выбранных фильтров
        """
        filters = self._filters_raw
        filter_codes = self.filter_codes
        
        categories =[]
        for key in filter_codes.keys():
            categories.append({
                key: list(filters[key]['values'].keys())
            })
        filter_ids = [f"{k}_{val}" for item in categories for k, v in item.items() for val in v]
        return filter_ids
        
    @cached_property     
    def filter_categories(self):
        result_dict = {}
        for category in self.filter_codes.keys():
            values_data = self._filters_raw[category]['values']
            result_dict[category] = {f"{category}_{k}": v['title'] for k, v in values_data.items()}
        return result_dict

    def load_raw_indicator(self, data_type: str = "excel", filter_ids: List["str"] =  None):
        """
       Загружает данные индикатора через API

       :param data_type: тип возвращаемых данных
       :param filter_ids: список с кодами выбранных показателей
       :return: DataFrame с данными
        """

        if self._raw_data is not None:
            return self._raw_data

        if filter_ids is None:
            filter_ids = self.get_filter_values()

        columnObjectIds = ["30611", "33560", "3"]
        lineObjectIds = ["57831", "58335"]
        for key in self.filter_codes.keys():
            if key not in columnObjectIds + lineObjectIds:
                lineObjectIds.append(key)

        data = {
                "lineObjectIds": lineObjectIds,
                "columnObjectIds": columnObjectIds,
                "selectedFilterIds": [
                filter_ids
                ]
        }
        params = {
            "format" : data_type,
            "id" : self.id  
        }
        try: 
            response = requests.post("https://www.fedstat.ru/indicator/data.do?", params = params, data = data)
            response.raise_for_status()
            if "excel" in response.headers.get("Content-Type"):
                raw_data = pd.read_excel(BytesIO(response.content), engine = "xlrd", header = 4) 
                for col in raw_data.columns:
                    if "Unnamed" in col:
                        index = int(col.split(' ')[1])
                        col_index = lineObjectIds[index]
                        new_col = self.filter_codes.get(col_index)
                        raw_data.rename(columns = {col: new_col}, inplace = True)
                self._raw_data = raw_data
                return self._raw_data
            else:
                raise ValueError(
                    f"Ответ не содержит {data_type} файла"
                )
        except requests.RequestException as e:
            raise requests.RequestException(f"Ошибка HTTP-запроса: {str(e)}")

    @staticmethod
    def _get_min_age(age_str):
        numbers = re.findall(r'\d+', age_str)
        return int(numbers[0]) if numbers else None

    @staticmethod
    def _get_max_age(age_str):
        numbers = re.findall(r"\d+", age_str)
        return int(numbers[-1]) if numbers else None

    @staticmethod   
    def _categorize_age(age_str):
        numbers = re.findall(r'\d+', age_str)
        words = re.findall(r'\b[а-яА-ЯёЁ]+\b', age_str, flags=re.IGNORECASE)
        if len(numbers) == 1 and len(words) <=3:
            return 1
        elif len(numbers) == 2 and len(words) <= 1:
            if int(numbers[-1]) - int(numbers[0]) == 4:
                return 2
            else:
                return 3
        else:
            return 4
    
    def _preprocess_dataframe(self, df):

        df.iloc[:, 0] = df.iloc[:, 0].str.strip()
        years = [col for col in df.columns if col.isdigit()]
        df[years] = df[years].astype("Int64")
         
        df.iloc[:, 1] = df.iloc[:, 1].str.replace(r'\s*(лет|года|год)$', '', regex = True).str.strip()
        subset_indices = [0, 1, 2]
        df = df[~df.iloc[:, subset_indices].duplicated(keep = "last")]
        
        return df

    def _remove_districts(self, df):

        """
        Удаляет федеральные округа из данных.
        :param df: DataFrame, предварительно обработанный
        :return: DataFrame без округов
        """
        
        rm_districts = '|'.join([
            r'Южный федеральный',
            r'Сибирский федеральный',
            r'Северо-Кавказский федеральный',
            r'Дальневосточный федеральный'
        ])

        districts_mask =df.iloc[:, 0].str.contains(rm_districts, case=False)
        df = df[~districts_mask].copy().reset_index(drop = True)
        return df

    def _change_districts(self, df):
        
        """
        Группирует регионы по федеральным округам.
        :param df: DataFrame после удаления округов
        :return: DataFrame с добавленными строками по округам
        """
        districts_config = {
            'Дальневосточный федеральный округ' : '|'.join([
                r'Бурятия',
                r'Забайкал',
                r'Саха',
                r'Якутия',
                r'Камчат',
                r'Приморск',
                r'Хабаровский',
                r'Амурская',
                r'Магаданская',
                r'Сахалинская',
                r'Еврейская автономная область',
                r'Чукотский автономный округ']),
            'Сибирский федеральный округ' : '|'.join([
                r'Алтай',
                r'Тыва',
                r'Хакасия',
                r'Красноярский',
                r'Иркутская',
                r'Кемеровская',
                r'Кузбасс',
                r'Новосибирская',
                r'Омская',
                r'Томская']),
            'Южный федеральный округ': '|'.join([
                r'Адыгея', 
                r'Калмыкия',
                r'Краснодарский',
                r'Астраханская',
                r'Волгоградская',
                r'Ростовская',
                r'Крым',
                r'Севастополь'
                ]),
            'Северо-Кавказский федеральный округ' :  '|'.join([
                r'Дагестан',
                r'Ингушетия',
                r'Кабардин',
                r'Балкар',
                r'Карачаев',
                r'Черкес',
                r'Осетия',
                r'Алания',
                r'Чечен',
                r'Ставрополь'
            ])   
        }
        col_one = df.columns[0]
        col_two = df.columns[1]
        col_three = df.columns[2]
        aggregated_dfs = []
        for district_name, regions in districts_config.items():
            mask = df.iloc[:, 0].str.contains(regions, case = False, na = False)
            district_df = df[mask].copy()
            if not district_df.empty:
                agg_df = district_df.groupby(
                    [col_two, col_three],
                    as_index = False
                ).sum(numeric_only = True)
                agg_df.insert(0, col_one, district_name)
                aggregated_dfs.append(agg_df)
        df = pd.concat([df] + aggregated_dfs, ignore_index = True)
        return df   

    def _add_mid_year_values(self, df):
        
        if df is None:
            df = self._change_districts()
        
        df['min_age']  = df.iloc[:, 1].apply(self._get_min_age)
        df['max_age'] = df.iloc[:, 1].apply(self._get_max_age)
        df['age_category'] = df.iloc[:, 1].apply(self._categorize_age)

        

        min_year = min([int(col) for col in df.columns if col.isdigit()])
        df_mid = pd.DataFrame()

        for col in df.columns:
            if col.isdigit():
                if int(col) > min_year:
                    df_mid[f"{col}mid"] = (df[f"{col}"] + df[f"{int(col)-1}"])/2
                df_mid[f"{col}end"] = df[col]
            else:
                df_mid[col] = df[col]        
        region_col = df.columns[0]
        df_mid = df_mid.groupby(region_col, sort = False).apply(
                lambda x: x.sort_values(['age_category', 'min_age', 'max_age'])
                ).reset_index(drop = True)
        return df_mid

    def get_processed_data(self, data_type: str = "excel", filter_ids: List["str"] =  None ):
        
        """
        Загружает, очищает и агрегирует данные Росстата для дальнейшего анализа.

        Последовательность обработки данных:
        1. Загружает исходные данные индикатора через API (метод `load_raw_indicator`).
        2. Выполняет предварительную очистку таблицы:
        - Переименовывает столбцы,
        - Удаляет лишние строки и столбцы,
        - Приводит числовые столбцы к типу Int64.
        3. Удаляет из данных строки с федеральными округами (оставляет только регионы).
        4. Агрегирует данные по федеральным округам:
        - Объединяет данные по регионам в укрупнённые федеральные округа.
        5. Добавляет дополнительные столбцы со значениями за середину года (среднее между двумя годами).

        :param data_type: Формат загружаемых данных с сайта (по умолчанию "excel").
        :param filter_ids: Список кодов фильтров для отбора данных (если не указан, загружаются все доступные).
        :return: pandas.DataFrame с итоговыми очищенными и агрегированными данными.
        """

        raw_df = self.load_raw_indicator(
            data_type = data_type,
            filter_ids = filter_ids
        )
        df = self._preprocess_dataframe(raw_df)
        df = self._remove_districts(df)
        df = self._change_districts(df)
        df = self._add_mid_year_values(df)
        df = df.drop(columns = ['min_age', 'max_age', 'age_category'])
        return df