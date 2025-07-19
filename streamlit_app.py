import streamlit as st
from fedstat_api import FedStatIndicator

def reset_blocks(active_block):
    st.session_state.show_block_1 = (active_block == 1)


if "show_block_1" not in st.session_state:
    st.session_state.show_block_1 = False
if "df" not in st.session_state:
     st.session_state.df_men = None


st.set_page_config(page_title="Статистические показатели", layout="wide", page_icon="📊")
st.title("📊 Приложение для скачивания показателей")


if not st.session_state.show_block_1:
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

with st.sidebar:
    st.title("🔍 Показатели")
    if st.button("📈 Численность населения", key='button1'):
            reset_blocks(1)

if st.session_state.show_block_1:
    with st.expander("", expanded = True):
        st.markdown(
                "<p style='font-size:22px; font-weight:bold;'>Численность населения</p>", 
                unsafe_allow_html=True
            )
        col1, col2 = st.columns(2)
        
        with col1:
            gender = st.selectbox(
                "Выберите пол",
                options = ["Мужчины", "Женщины", "Все"]
            )
        if gender == "Мужчины":
            indicator_id = 31548
        if gender == "Женщины":
            indicator_id = 33459
        try: 
            population = FedStatIndicator(indicator_id)
        except Exception as e:
                print(f"Ошибка при загрузке данных: {e}")

        selectbox_values = population.filter_codes
        options = population.filter_categories
        selected_values = []
        for key, val in selectbox_values.items():
            col1, col2 = st.columns([1, 1])
            sb_options = list(options.get(key).values())
            if len(sb_options) > 1:
                all_options = ["Все"] + sb_options
                with col1:
                    selected = st.multiselect(val, options = all_options, default = all_options[0])
                with col2:
                    if st.button("Все", key = f"selected_{key}"):
                        seletect = all_options[1:]
                        
                if "Все" in selected:
                    selected = sb_options
            else:
                selected.append(sb_options)

        if st.button("Загрузить данные"):
            with st.spinner("Загрузка данных... Это может занять до 10 минут"):
                st.write(population.get_indicator_title())
                st.session_state.df = population.get_processed_data()
            
            if st.session_state is not None:

                st.dataframe(
                    st.session_state.df.head(10),
                    use_container_width= True,
                    height = 400
                )
