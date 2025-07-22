import streamlit as st
from fedstat_api import FedStatIndicator

def reset_blocks(active_block):
    st.session_state.show_block_1 = (active_block == 1)
    st.session_state.show_block_2 = (active_block == 2)


if "show_block_1" not in st.session_state:
    st.session_state.show_block_1 = True
if "show_block_2" not in st.session_state:
    st.session_state.show_block_2 = False
if "df" not in st.session_state:
     st.session_state.df = None


st.set_page_config(page_title="Статистические показатели", layout="wide", page_icon="📊")
st.title("📊 Приложение для скачивания показателей")

with st.sidebar:
    st.title("🔍 Показатели")
    if st.button("🏠 Домашний экран", key = "home_screen"):
        reset_blocks(1)
    if st.button("📈 Численность населения", key='button1'):
        reset_blocks(2)


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
        col1, col2 = st.columns(2)
        
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
                print(f"Ошибка загрузки данных: {e}")

        selectbox_values = indicator_1.filter_codes
        options = indicator_1.filter_categories
        
        
        selected_values = []

        col1, col2 = st.columns([1, 1])
        for key, val in selectbox_values.items():
            sb_options = list(options.get(key).values())
            if len(sb_options) > 1:
                all_options = ["Выбрать все"] + sb_options
                with col1:
                    selected = st.multiselect(val, options = all_options, default = all_options[0])
                        
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
       
        if st.button("Загрузить данные"):
            with st.spinner("Загрузка данных... Это может занять до 10 минут"):
                if gender != "Все":
                    st.write(indicator_1.indicator_title)
                    st.session_state.df = indicator_1.get_processed_data(filter_ids = values_to_pass)
            
            if st.session_state is not None:

                st.dataframe(
                    st.session_state.df.head(10),
                    use_container_width= True,
                    height = 400
                )
