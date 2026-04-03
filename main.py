import streamlit as st
import PIL.Image as Image
from ultralytics import YOLO
import google.generativeai as genai
import os
import sqlite3
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from fpdf import FPDF
from datetime import datetime

# --- 1. КОНФИГУРАЦИЯ API ---
API_KEY = "AIzaSyABE6pt1de0Wm-F4VLTkxRk78kjoL9zEUs" 
genai.configure(api_key=API_KEY)
# Используем flash для скорости
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

# --- 3. ИНТЕРФЕЙС И СТИЛИ ---
st.set_page_config(page_title="StomaAI PRO", layout="wide", page_icon="🦷")

st.markdown("""
    <style>
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: white; color: gray; text-align: center;
        padding: 10px; font-size: 12px; border-top: 1px solid #eee; z-index: 100;
    }
    .stChatMessage { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def init_db():
    conn = sqlite3.connect('stoma_pro.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS diag (name TEXT, date TEXT, report TEXT)')
    conn.commit()
    return conn

db = init_db()

@st.cache_resource
def load_yolo():
    return YOLO('best.pt') if os.path.exists('best.pt') else None

yolo_model = load_yolo()

def make_pdf(content, name):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"REPORT: {name}", ln=1, align="C")
        pdf.multi_cell(0, 10, txt=content.encode('latin-1', 'replace').decode('latin-1'))
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# --- 5. РАБОТА С ЧАТОМ ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Вывод истории
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if "pdf" in m and m["pdf"]:
            st.download_button("📥 Скачать PDF", m["pdf"], "report.pdf", "application/pdf")

# --- 6. САУНДБАР (ВВОД) ---
st.divider()
input_col, file_col = st.columns([0.8, 0.2])

with input_col:
    txt = st.text_input("Описание клинической картины...", key="user_txt", label_visibility="collapsed")

with file_col:
    up = st.file_uploader("📎", type=['jpg','png','jpeg'], label_visibility="collapsed")

# Поле для имени в сайдбаре
with st.sidebar:
    st.title("🗂 Пациенты")
    patient_name = st.text_input("ФИО Пациента:", "Новый пациент")

# Логика обработки
if st.button("Отправить на анализ ✨", use_container_width=True):
    if txt or up:
        # 1. Показываем ввод пользователя
        with st.chat_message("user"):
            if txt: st.markdown(txt)
            if up: st.image(up, width=300)
        
        st.session_state.messages.append({"role": "user", "content": txt or "Анализ снимка"})

        # 2. Анализ
        with st.chat_message("assistant"):
            with st.spinner("StomaAI PRO анализирует..."):
                findings = ""
                img_for_ai = None
                
                if up:
                    img_for_ai = Image.open(up).convert("RGB")
                    if yolo_model:
                        res = yolo_model(img_for_ai)
                        det = [yolo_model.names[int(b.cls[0])] for b in res[0].boxes]
                        findings = f"YOLO обнаружила: {', '.join(set(det))}"
                        st.image(res[0].plot(), caption="Обнаруженные зоны", width=400)

                prompt = f"{ULTRA_PROMPT}\nПАЦИЕНТ: {patient_name}\nТЕКСТ: {txt}\nДАННЫЕ ЗРЕНИЯ: {findings}"
                
                if up:
                    response = llm.generate_content([prompt, img_for_ai])
                else:
                    response = llm.generate_content(prompt)
                
                ai_res = response.text
                st.markdown(ai_res)
                
                # PDF и БД
                pdf_file = make_pdf(ai_res, patient_name)
                db.execute("INSERT INTO diag VALUES (?, ?, ?)", (patient_name, datetime.now().strftime("%Y-%m-%d"), ai_res))
                db.commit()
                
                st.session_state.messages.append({"role": "assistant", "content": ai_res, "pdf": pdf_file})
                if pdf_file:
                    st.download_button("📥 Скачать клинический отчет PDF", pdf_file, f"{patient_name}.pdf")
        
        st.rerun()

# --- 7. ФУТЕР ---
st.markdown(f"""
    <div class="footer">
        <p>⚠️ <b>ВНИМАНИЕ:</b> Инструмент поддержки. Требуется верификация врачом.</p>
        <p>Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
