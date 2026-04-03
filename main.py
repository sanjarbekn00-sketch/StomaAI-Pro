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

# --- 2. ТВОЙ ЗОЛОТОЙ ПРОМПТ (БЕЗ ИЗМЕНЕНИЙ) ---
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

# --- 3. ДИЗАЙН И СКРЫТИЕ ЛИШНЕГО ---
st.set_page_config(page_title="StomaAI PRO", layout="wide")

st.markdown("""
    <style>
    /* Полное удаление управления приложением */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stToolbar"] {display: none;}
    button[title="View source"] {display: none;}
    
    /* Оформление футера */
    .footer-container {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        text-align: center;
        padding: 10px;
        border-top: 1px solid #eaeaea;
        z-index: 99;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. ИНТЕРФЕЙС КАК НА СКРИНШОТАХ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3467/3467830.png", width=80)
    st.title("Пациенты")
    st.write("---")
    patient_name = st.text_input("ФИО пациента:", "Новый пациент")

st.title("🔬 StomaAI PRO: Облачная Диагностика")

# Сетка ввода (как на скрине 173/176)
col_left, col_right = st.columns([0.6, 0.4])

with col_left:
    user_text = st.text_area("Опишите жалобы или задайте вопрос...", height=200)

with col_right:
    st.write("Загрузить рентген/фото")
    up_file = st.file_uploader("Upload", type=['jpg','png','jpeg'], label_visibility="collapsed")

analyze_btn = st.button("Отправить на анализ ✨")

# --- 5. ЛОГИКА АНАЛИЗА ---
if analyze_btn:
    if user_text or up_file:
        with st.spinner("StomaAI PRO формирует экспертное заключение..."):
            img_input = None
            if up_file:
                img_input = Image.open(up_file).convert("RGB")
            
            # Сборка промпта
            final_prompt = f"{ULTRA_PROMPT}\n\nКЛИНИЧЕСКИЙ СЛУЧАЙ:\nПациент: {patient_name}\nОписание: {user_text}"
            
            if img_input:
                res = llm.generate_content([final_prompt, img_input])
            else:
                res = llm.generate_content(final_prompt)
            
            st.divider()
            st.markdown(res.text)
    else:
        st.warning("Для начала анализа введите данные или прикрепите файл.")

# --- 6. ПРЕДУПРЕЖДЕНИЕ И РАЗРАБОТЧИК ---
st.markdown(f"""
    <div class="footer-container">
        <p style="color: #d9534f; margin-bottom: 2px;">⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p style="color: #666; font-size: 11px;">Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
