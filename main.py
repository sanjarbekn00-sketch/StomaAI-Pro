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

# --- 3. ФУНКЦИИ ОБРАБОТКИ (БЕЗ ИЗМЕНЕНИЙ) ---
def extract_kb_data():
    kb_dir = "knowledge_base"
    if not os.path.exists(kb_dir):
        os.makedirs(kb_dir)
        return ""
    text = ""
    for f in os.listdir(kb_dir):
        p = os.path.join(kb_dir, f)
        try:
            if f.endswith(".pdf"):
                for page in PdfReader(p).pages: text += (page.extract_text() or "")
            elif f.endswith(".docx"):
                for para in Document(p).paragraphs: text += para.text + "\n"
        except: pass
    return text[:25000]

def init_db():
    conn = sqlite3.connect('stoma_pro.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS diag (name TEXT, date TEXT, report TEXT)')
    conn.commit()
    return conn

db = init_db()

def make_pdf(content, name, img_o):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Patient: {name}", ln=True)
    pdf.multi_cell(0, 7, content.replace('*', '').replace('#', ''))
    return pdf.output(dest='S')

# --- 4. ИНТЕРФЕЙС STREAMLIT (ChatGPT Style) ---
st.set_page_config(page_title="StomaAI PRO", layout="wide")

# Стиль для фиксации футера и саундбара
st.markdown("""
    <style>
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; color: gray; text-align: center; padding: 10px; font-size: 12px; border-top: 1px solid #eee; z-index: 999; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_yolo():
    return YOLO('best.pt') if os.path.exists('best.pt') else None
model = load_yolo()

# Сайдбар с историей
with st.sidebar:
    st.title("🗂 Пациенты")
    patient_name = st.text_input("ФИО пациента:", "Новый пациент")
    cursor = db.cursor()
    cursor.execute("SELECT name, date FROM diag ORDER BY rowid DESC LIMIT 10")
    for n, d in cursor.fetchall():
        st.write(f"👤 {n} ({d})")

# Основное окно чата
st.title("🔬 StomaAI PRO: Облачная Диагностика")
if "chat" not in st.session_state: st.session_state.chat = []

# Вывод истории диалога
for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if "pdf" in m and m["pdf"]:
            st.download_button("📥 Скачать PDF", m["pdf"], "report.pdf", "application/pdf")

# САУНДБАР (Ввод как в ChatGPT)
st.divider()
input_col, file_col = st.columns([0.85, 0.15])
with input_col:
    txt = st.text_input("Описание клинической картины...", key="main_input", label_visibility="collapsed")
with file_col:
    up = st.file_uploader("📎", type=['jpg','png','jpeg'], label_visibility="collapsed")

# ЛОГИКА ОТПРАВКИ
if st.button("Отправить на анализ", use_container_width=True):
    if txt or up:
        st.session_state.chat.append({"role": "user", "content": txt or "Запрос к изображению"})
        
        with st.chat_message("assistant"):
            with st.spinner("Анализирую..."):
                kb = extract_kb_data()
                findings = "Анализ снимка"
                img_obj = None
                
                if up:
                    img_obj = Image.open(up).convert("RGB")
                    if model:
                        res = model(img_obj)
                        det = [model.names[int(b.cls[0])] for b in res[0].boxes]
                        findings = ", ".join(set(det)) if det else "Патологий не найдено"
                        st.image(res[0].plot(), caption="Результат YOLO", width=400)
                
                # Формируем промпт для Gemini
                prompt = f"{ULTRA_PROMPT}\n\nКЛИНИКА: {txt}\nYOLO: {findings}\nБАЗА: {kb}"
                
                if up:
                    ai_res = llm.generate_content([prompt, img_obj]).text
                else:
                    ai_res = llm.generate_content(prompt).text
                
                st.markdown(ai_res)
                
                # Сохранение и PDF
                db.execute("INSERT INTO diag VALUES (?, ?, ?)", (patient_name, datetime.now().strftime("%Y-%m-%d"), ai_res))
                db.commit()
                pdf = make_pdf(ai_res, patient_name, None)
                
                st.session_state.chat.append({"role": "assistant", "content": ai_res, "pdf": pdf})
        st.rerun()

# ПРЕДУПРЕЖДЕНИЕ И РАЗРАБОТЧИК
st.markdown(f"""
    <div class="footer">
        <p>⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p>Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
