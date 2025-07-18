import streamlit as st
from fedstat_api import FedStatIndicator


st.set_page_config(page_title="Статистические показатели", layout="wide", page_icon="📊")
st.title("📊 Приложение для скачивания показателей")

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

query = st.text_area(label = "Введите запрос")

if "show_block_1" not in st.session_state:
    st.session_state.show_block_1 = False

def reset_blocks(active_block):
    st.session_state.show_block_1 = (active_block == 1)

with st.sidebar:
    st.title("Показатели")
    if st.button("Численность населения", key='button1'):
            reset_blocks(1)

if st.session_state.show_block_1:
    with st.expander("", expanded = True):
        st.markdown(
                "<p style='font-size:22px; font-weight:bold;'>Численность населения</p>", 
                unsafe_allow_html=True
            )
        if st.button("Мужчины", key = "men_population"):
            men_population = FedStatIndicator(indicator_id = 31548)
            df_men = men_population.get_processed_data()
            df.head(10)
    
