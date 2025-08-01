import streamlit as st
import numpy as np
import pandas as pd
from fedstat_api import FedStatIndicator
from io import BytesIO
import sys


#Блок функций
def reset_blocks(active_block):
    st.session_state.show_block_1 = (active_block == 1)
    st.session_state.show_block_2 = (active_block == 2)
    st.session_state.show_block_3 = (active_block == 3)

def display_and_download(df, indicator_title):

        if df is not None and not df.empty:
            st.dataframe( 
                df.head(10),
                use_container_width=True,
                height=400
            )

            col1, col2 = st.columns([0.05, 0.4])
            encoding = 'windows-1251'
            with col1:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer) as writer:
                    st.session_state.df.to_excel(writer, index = False)
                buffer.seek(0)
                if st.download_button(
                    label = "Скачать Excel",
                    data = buffer.getvalue(),
                    file_name = f"{indicator_title}.xlsx"
                ):
                    return None

            with col2:
                if st.download_button(
                    label = "Скачать CSV",
                    data = st.session_state.df.to_csv(encoding = encoding, index = False),
                    file_name = f"{indicator_title}.csv"
                ):
                    st.session_state.df = None
                    st.rerun()
                    return None
            return df
def get_selectbox_args(indicator):

    selectbox_values = indicator.filter_codes
    options = indicator.filter_categories
        
    selected_values = []

    col1, col2 = st.columns([0.5, 1])
    for key, val in selectbox_values.items():
        sb_options = list(options.get(key).values())
        if len(sb_options) > 1:
            all_options = ["Выбрать все"] + sb_options
            with col1:
                selected = st.multiselect(val, options = all_options, default = all_options[0], placeholder = "Выберите один или несколько вариантов")
                    
            if "Выбрать все" in selected:
                selected = sb_options
            selected_values.append(selected)
        else:
            selected_values.append(sb_options)
    options_dict = {}
    for option in options.values():
        options_dict.update(option)

    values_to_pass = []  
    for selected_list in selected_values:
        for value in selected_list:
            for k, v in options_dict.items():
                if v == value:
                    values_to_pass.append(k)
    return values_to_pass

def remove_differences(df1, df2):
    df_1, df_2 = df1.copy(), df2.copy()
    df1_size, df2_size = df1.shape[0], df2.shape[0]
    if df1_size == df2_size:
        return df_1, df_2

    key_columns = df1.columns[:3]
    bigger_df, smaller_df = (df_1, df_2) if df1_size > df2_size else (df_2, df_1) 

    diff = bigger_df[key_columns].merge(smaller_df[key_columns], how='outer', indicator=True)
    diff_values = diff[diff['_merge'] == 'left_only']

    mask = bigger_df[key_columns].apply(tuple, axis=1).isin(
        diff_values[key_columns].apply(tuple, axis=1)
    )
    bigger_df = bigger_df[~mask]

    if df1_size > df2_size:
        df_1, df_2 = bigger_df, smaller_df
    else:
        df_2, df_1 = bigger_df, smaller_df

    if len(df_1) != len(df_2):
        raise ValueError(
            f"Размеры не совпали после обработки: df1={len(df_1)}, df2={len(df_2)}. "
            "Возможно, в данных есть дубликаты ключевых колонок."
        )
    return df_1, df_2

def fill_missing_column(df_men, df_women):
    df_men = df_men.copy()
    df_rel = df_men.select_dtypes(include = ['object']).copy()
    year_cols = [col for col in df_men.columns if "end" in col]

    for col in year_cols:
        df_rel[col] = df_men[col] / df_women[col].replace(0, np.nan)
    df_rel['age_category'] = df_men['age_category']
    
    mean_2021 = (df_rel['2020end'] + df_rel['2022end']) / 2
    df_rel["2021end"] = df_rel["2021end"].fillna(mean_2021)
    men_2021 = df_women["2021end"] * df_rel["2021end"]
    men_2021 = men_2021.replace([np.inf, -np.inf], np.nan)
    df_men["2021end"] = df_men["2021end"].astype("float")
    df_men["2021end"] = df_men["2021end"].fillna(men_2021)

    df_men["2022mid"] = (df_men["2022end"] + df_men["2021end"]) / 2
    df_men["2021mid"] = (df_men["2021end"] + df_men["2020end"]) / 2
    return df_men


def total_sum(df_men, df_women):
    df_men = df_men.copy()
    df_women = df_women.copy()
    df_men = df_men.reset_index(drop = True)
    df_women = df_women.reset_index(drop = True)

    df_all = pd.DataFrame()
    year_cols = [col for col in df_men.columns if "end" in col or "mid" in col]
    for col in df_men.columns:
        if col in year_cols:
            df_all[col] = df_men[col] + df_women[col]
        else:
            df_all[col] = df_men[col]
    return df_all


if "show_block_1" not in st.session_state:
    st.session_state.show_block_1 = True
if "show_block_2" not in st.session_state:
    st.session_state.show_block_2 = False
if "show_block_3" not in st.session_state:
    st.session_state.show_block_3 = False
if "df" not in st.session_state:
     st.session_state.df = None


st.set_page_config(page_title="Статистические показатели", layout="wide", page_icon="📊")
st.title("📊 Приложение для скачивания статистических показателей")

with st.sidebar:
    st.title("🔍 Показатели")
    if st.button("🏠 Домашний экран", key = "home_screen"):
        reset_blocks(1)
    if st.button("📈 Численность населения", key='button_population'):
        reset_blocks(2)
    if st.button("👩‍🍼 Число родившихся по возрасту матери", key='button_birth'):
        reset_blocks(3)


if st.session_state.show_block_1:
    with st.container():
        st.markdown(
            '''
            <p style='font-size:24px;'>С помощью этого приложения можно:</p>
            <ul style='color: black; font-size: 20px;'>
                <li>Скачать данные по численности населения в разрезе пола и возраста</li>
            </ul>
            <p style='font-size:24px;'>Вы можете ввести свой запрос ниже либо выбрать необходимые данные на боковой панели</p>
            ''',
            unsafe_allow_html=True
        )

        prompt = st.chat_input("Пример запроса: выведи численность мужского населения с 2021 по 2025 по однолетним группам")
        if prompt:
            st.write(f"Prompt: {prompt}")


if st.session_state.show_block_2:
    with st.expander("", expanded = True):
        st.markdown(
                "<p style='font-size:22px; font-weight:bold;'>Численность населения</p>", 
                unsafe_allow_html=True
            )
        col1, col2 = st.columns([0.5, 1])
        
        with col1:
            gender = st.selectbox(
                "Выберите пол",
                options = ["Все", "Мужчины", "Женщины"]
            )
        gender_codes = {
            "Мужчины" : 31548,
            "Женщины" : 33459
        }
        if gender != "Все":
            try:
                indicator_1 = FedStatIndicator(gender_codes.get(gender))
                
            except Exception as e:
                print(f"Ошибка загрузки данных: {e}")
        else:
            try:
                indicator_1 = FedStatIndicator(gender_codes.get("Мужчины"))
                indicator_2 = FedStatIndicator(gender_codes.get("Женщины"))
            except Exception as e:
                st.write(f"Ошибка загрузки данных: {e}")

        values_to_pass = get_selectbox_args(indicator_1)

        if st.button("Загрузить данные"):
            with st.spinner("Загрузка данных... Это может занять до 10 минут"):
                if gender != "Все":
                    st.write(indicator_1.indicator_title)
                    indicator_title = indicator_1.indicator_title
                    st.session_state.df = indicator_1.get_processed_data(filter_ids = values_to_pass)
                    st.success("Данные успешно загружены!")
                if gender == "Все":
                    st.write(f"{indicator_1.indicator_title} / {indicator_2.indicator_title}")
                    try:
                        df_men =indicator_1.get_processed_data(filter_ids = values_to_pass)
                        df_women =indicator_2.get_processed_data(filter_ids = values_to_pass)
                        indicator_title = "Численность всего населения"
                        df_men, df_women = remove_differences(df_men, df_women)
                        df_men = fill_missing_column(df_men, df_women)
                        df_all = total_sum(df_men, df_women)
                        st.session_state.df = df_all
                        st.success("Данные успешно загружены!")
                    except Exception as e:
                        print(f"Ошибка обработки данных: {e}")
            
        if "df" in st.session_state and st.session_state.df is not None:
            result = display_and_download(st.session_state.df, indicator_title )
            if result is None:
                st.session_state.df = None
                st.rerun()

if st.session_state.show_block_3:
    with st.expander("", expanded = True):
        st.markdown(
                "<p style='font-size:22px; font-weight:bold;'>Число родившихся по возрасту матери и очередности рождения</p>", 
                unsafe_allow_html=True
            )
        try:
            birth_num = FedStatIndicator(indicator_id = "59992")
        except Exception as e:
                st.write(f"Ошибка загрузки данных: {e}")

        values_to_pass = get_selectbox_args(birth_num)




        if st.button("Загрузить данные"):
            with st.spinner("Загрузка данных... Это может занять до 10 минут"):
                try:
                    st.session_state.df = birth_num.get_processed_data(filter_ids = values_to_pass)
                except Exception as e:
                    print(f"Ошибка обработки данных: {e}")

        if "df" in st.session_state and st.session_state.df is not None:
            result = display_and_download(st.session_state.df, birth_num.indicator_title)
            if result is None:
                st.session_state.df = None
                st.rerun()
         
