import streamlit as st
import PIL.Image as Image
from ultralytics import YOLO
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- 1. КОНФИГУРАЦИЯ API ---
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

# --- 3. ИНТЕРФЕЙС (УДАЛЯЕМ "УПРАВЛЕНИЕ ПРИЛОЖЕНИЕМ") ---
st.set_page_config(page_title="StomaAI PRO", layout="wide")

# CSS для удаления всех элементов управления Streamlit и фиксации футера
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .embeddedAppMetaInfoBar_container__W_B9z {display: none !important;}
    
    .footer-text {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #eee;
        z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. ОСНОВНОЙ ВИД (КАК БЫЛО) ---
st.title("🦷 StomaAI PRO: Облачная Диагностика")

col_input, col_file = st.columns([0.6, 0.4])

with col_input:
    patient_name = st.text_input("ФИО пациента:", "Новый пациент")
    clinical_text = st.text_area("Опишите жалобы или задайте вопрос...", height=150)

with col_file:
    st.write("Загрузить рентген/фото")
    uploaded_file = st.file_uploader("Upload", type=['jpg','png','jpeg'], label_visibility="collapsed")

analyze_btn = st.button("Отправить на анализ ✨")

# --- 5. ЛОГИКА (БЕЗ АВТОМАТИЗМА) ---
if analyze_btn:
    if clinical_text or uploaded_file:
        with st.spinner("StomaAI PRO анализирует..."):
            img_context = ""
            img_for_gemini = None
            
            if uploaded_file:
                img_for_gemini = Image.open(uploaded_file).convert("RGB")
                img_context = "Проведен визуальный анализ загруженного снимка."

            full_query = f"{ULTRA_PROMPT}\n\nПАЦИЕНТ: {patient_name}\nКЛИНИЧЕСКАЯ КАРТИНА: {clinical_text}\n{img_context}"
            
            if img_for_gemini:
                response = llm.generate_content([full_query, img_for_gemini])
            else:
                response = llm.generate_content(full_query)
            
            st.divider()
            st.markdown(response.text)
    else:
        st.error("Ошибка: Введите текст или загрузите снимок.")

# --- 6. ФУТЕР (ВАРНИНГ И РАЗРАБОТЧИК) ---
st.markdown(f"""
    <div class="footer-text">
        <p style="color: red; font-weight: bold;">⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p>Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
