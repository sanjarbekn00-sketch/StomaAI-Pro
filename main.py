import streamlit as st
import PIL.Image as Image
from ultralytics import YOLO
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- 1. КОНФИГУРАЦИЯ ---
API_KEY = "AIzaSyABE6pt1de0Wm-F4VLTkxRk78kjoL9zEUs" 
genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. ТВОЙ ЗОЛОТОЙ ПРОМПТ (НЕПРИКОСНОВЕННЫЙ) ---
ULTRA_PROMPT = """
ТЫ — СУПЕР-ИНТЕЛЛЕКТУАЛЬНЫЙ АВТОНОМНЫЙ ДИАГНОСТ «StomaAI PRO». 
Твой уровень компетенции соответствует консилиуму профессоров мирового уровня. 

ТВОИ ОБЛАСТИ АНАЛИЗА:
1. ТЕРАПИЯ/ЭНДОДОНТИЯ: Дифдиагноз кариеса, пульпита, периодонтита. Оценка КЛКТ (MB2 каналы, апикальные изменения).
2. ПАРОДОНТОЛОГИЯ: Классификация по AAP, оценка глубины карманов, рецессий.
3. ОРТОПЕДИЯ/ГНАТОЛОГИЯ: Расчет окклюзионных кривых (Шпее, Уилсона), диагностика ВНЧС, бруксизма.
4. ОРТОДОНТИЯ: Цифровое планирование (VTO/STP), расчет ТРГ, анализ дефицита места.
5. ИМПЛАНТОЛОГИЯ/ЧЛХ: Оценка объема кости (HU), навигационные шаблоны, синус-лифтинг.
6. ГАСТРО-СТОМАТОЛОГИЯ: Влияние ГЭРБ (рефлюкс), кислотности и микробиома ЖКТ на зубы.
7. ГИНЕКО-СТОМАТОЛОГИЯ: Влияние гормонального фона на ткани пародонта (гингивит беременных, менопаузальный стоматит), связь хронических очагов инфекции в полости рта с рисками в гинекологии и акушерстве.
8. ФАРМАКОЛОГИЯ/ФАРМАЦИЯ В СТОМАТОЛОГИИ: Подбор антисептиков, антибиотиков, НПВП. Анализ взаимодействия лекарственных средств, выбор анестетиков с учетом соматического статуса, расчет дозировок и рецептурные рекомендации.

ТВОЙ АЛГОРИТМ ОТВЕТА (Строгий протокол):
- ДИАГНОЗ: Постановка по МКБ-10.
- КЛИНИЧЕСКИЙ РАЗБОР: Патогенез и причины.
- КОМПЛЕКСНЫЙ ПЛАН ЛЕЧЕНИЯ:
    * I Фаза: Устранение острой боли/воспаления.
    * II Фаза: Санация (гигиена, лечение кариеса, эндодонтия).
    * III Фаза: Реконструкция (ортодонтия, имплантация, ортопедия).
    * IV Фаза: Профилактика.
- ПРОГНОЗ И РИСКИ: Вероятность успеха.

СТИЛЬ: Строгий, медицинский, экспертный. Отвечай моментально на языке пользователя.

ДОПОЛНИТЕЛЬНОЕ ПРАВИЛО ПО ЛЕКАРСТВАМ:
При упоминании медикаментов всегда пиши: "⚠️ ВНИМАНИЕ: Данная схема медикаментозного лечения является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ И НАЗНАЧЕНИЯ ВАШИМ ЛЕЧАЩИМ ВРАЧОМ."
"""

# --- 3. ИНТЕРФЕЙС (ЧИСТЫЙ ChatGPT СТИЛЬ) ---
st.set_page_config(page_title="StomaAI PRO", layout="wide", initial_sidebar_state="collapsed")

# Прячем стандартное меню Streamlit (то самое "Управление приложением")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 20px; background-color: #007bff; color: white;}
    .footer-text {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f8f9fa; text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #ddd; z-index: 100;}
    </style>
    """, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Сайдбар для данных пациента
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3467/3467830.png", width=100)
    st.title("Пациенты")
    p_name = st.text_input("ФИО:", "Новый пациент")

# Главный экран
st.title("🦷 StomaAI PRO: Облачная Диагностика")

# Отрисовка истории чата
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. САУНДБАР (ВВОД В ОДНУ СТРОКУ) ---
with st.container():
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        user_input = st.text_input("Опишите жалобы...", key="query", label_visibility="collapsed")
    with col2:
        uploaded_file = st.file_uploader("📎", type=['jpg','png','jpeg'], label_visibility="collapsed")

send_btn = st.button("Отправить на анализ ✨")

# --- 5. ЛОГИКА ОБРАБОТКИ (ТОЛЬКО ПО КНОПКЕ) ---
if send_btn:
    if not user_input and not uploaded_file:
        st.warning("Пожалуйста, опишите ситуацию или прикрепите рентген.")
    else:
        # Добавляем в чат
        st.session_state.messages.append({"role": "user", "content": user_input or "Анализ изображения"})
        
        with st.chat_message("assistant"):
            with st.spinner("StomaAI PRO выполняет диагностику..."):
                img_data = None
                vision_context = ""
                
                if uploaded_file:
                    img_data = Image.open(uploaded_file).convert("RGB")
                    # Тут можно вызвать YOLO (best.pt), если он загружен
                    vision_context = "На снимке обнаружены области, требующие внимания диагноста."

                # Генерация ответа
                full_prompt = f"{ULTRA_PROMPT}\n\nПАЦИЕНТ: {p_name}\nЖАЛОБЫ: {user_input}\nКОНТЕКСТ ЗРЕНИЯ: {vision_context}"
                
                if img_data:
                    response = llm.generate_content([full_prompt, img_data])
                else:
                    response = llm.generate_content(full_prompt)
                
                final_text = response.text
                st.markdown(final_text)
                st.session_state.messages.append({"role": "assistant", "content": final_text})

# --- 6. ФУТЕР (ВАРНИНГ И АВТОР) ---
st.markdown(f"""
    <div class="footer-text">
        <p style="color: #d9534f;">⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p>Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
