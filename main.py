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
API_KEY = "AIzaSyD99Uks4Lf68tsZo5HUYg98ly4Ebe9m6jU" 
genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('models/gemini-2.5-flash')

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

# --- 3. ФУНКЦИИ ОБРАБОТКИ ЗНАНИЙ ---
def extract_kb_data():
    kb_dir = "knowledge_base"
    if not os.path.exists(kb_dir):
        os.makedirs(kb_dir)
        return "База знаний пуста. Загрузите PDF/DOCX в папку knowledge_base."
    text = ""
    for f in os.listdir(kb_dir):
        p = os.path.join(kb_dir, f)
        try:
            if f.endswith(".pdf"):
                for page in PdfReader(p).pages: text += (page.extract_text() or "")
            elif f.endswith(".docx"):
                for para in Document(p).paragraphs: text += para.text + "\n"
            elif f.endswith(".xlsx"): text += pd.read_excel(p).to_string()
            elif f.endswith(".txt"):
                with open(p, "r", encoding="utf-8") as file: text += file.read()
        except Exception as e:
            st.warning(f"Не удалось прочитать {f}: {e}")
    return text[:25000]

# --- 4. БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('stoma_pro.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS diag (name TEXT, date TEXT, report TEXT)')
    conn.commit()
    return conn

db = init_db()

# --- 5. ГЕНЕРАЦИЯ PDF ---
def make_pdf(content, name, img_o, img_y):
    pdf = FPDF()
    pdf.add_page()
    # Поиск шрифта в текущей папке
    font_file = "DejaVuSans.ttf"
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.set_font('DejaVu', '', 11)
    else:
        pdf.set_font('Helvetica', '', 11)
    
    pdf.set_text_color(0, 50, 150)
    pdf.cell(0, 10, "STOMAAI PRO CLINICAL REPORT", ln=True, align='C')
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Patient: {name} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    
    y_pos = pdf.get_y()
    # Вставляем снимки, если они есть
    if img_o and os.path.exists(img_o): pdf.image(img_o, x=10, y=y_pos+5, w=90)
    if img_y and os.path.exists(img_y): pdf.image(img_y, x=105, y=y_pos+5, w=90)
    
    pdf.set_y(y_pos + 65)
    pdf.multi_cell(0, 7, content.replace('*', '').replace('#', ''))
    return pdf.output(dest='S')

# --- 6. ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="StomaAI PRO Server", layout="wide", page_icon="🔬")

# Загрузка модели YOLO
@st.cache_resource
def load_yolo():
    for m_path in ['best.pt', 'yolov8n.pt']:
        if os.path.exists(m_path):
            return YOLO(m_path)
    return None

model = load_yolo()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/387/387561.png", width=100)
    st.title("🗂 Пациенты")
    cursor = db.cursor()
    cursor.execute("SELECT name, date, report FROM diag ORDER BY rowid DESC LIMIT 10")
    recent = cursor.fetchall()
    for n, d, r in recent:
        with st.expander(f"👤 {n} ({d})"):
            st.write(r[:300] + "...")

st.title("🔬 StomaAI PRO: Облачная Диагностика")
if "chat" not in st.session_state: st.session_state.chat = []

# Вывод чата
for m in st.session_state.chat:
    with st.chat_message(m["role"]): 
        st.write(m["content"])
        if "pdf" in m: 
            st.download_button("📥 Скачать клинический отчет PDF", m["pdf"], f"Report_{name}.pdf")

# Панель ввода
st.divider()
col1, col2 = st.columns([2, 3])
with col1:
    name = st.text_input("ФИО пациента:", "Новый пациент")
    up = st.file_uploader("Загрузить рентген/фото", type=['jpg','png','jpeg'])
with col2:
    txt = st.chat_input("Опишите жалобы или задайте вопрос...")

if txt or up:
    st.session_state.chat.append({"role": "user", "content": txt or "Анализ изображения"})
    with st.chat_message("assistant"):
        with st.spinner("Обработка данных..."):
            kb = extract_kb_data()
            o_p, y_p = "temp_orig.png", "temp_yolo.png"
            findings = "Анализ по визуальным признакам"
            
            if up:
                img = Image.open(up).convert("RGB")
                img.save(o_p)
                if model:
                    res = model(img)
                    det = [model.names[int(b.cls[0])] for b in res[0].boxes]
                    findings = ", ".join(set(det)) if det else "Патологий на снимке не обнаружено"
                    res_img = res[0].plot()
                    Image.fromarray(res_img).save(y_p)
                    st.image(res_img, caption="Результат распознавания ИИ")
                
                prompt = f"{ULTRA_PROMPT}\n\nБАЗА ЗНАНИЙ:\n{kb}\n\nДАННЫЕ: {name}, YOLO НАШЛА: {findings}, ТЕКСТ: {txt}"
                ai_res = llm.generate_content([prompt, img]).text
            else:
                ai_res = llm.generate_content(f"{ULTRA_PROMPT}\n\nБАЗА ЗНАНИЙ:\n{kb}\n\nТЕКСТ: {txt}").text
            
            st.markdown(ai_res)
            
            # Сохраняем в базу
            db.execute("INSERT INTO diag VALUES (?, ?, ?)", (name, datetime.now().strftime("%Y-%m-%d"), ai_res))
            db.commit()
            
            # Генерируем PDF
            pdf = make_pdf(ai_res, name, o_p if up else None, y_p if up else None)
            st.session_state.chat.append({"role": "assistant", "content": ai_res, "pdf": pdf})
            
            # Удаляем временные файлы
            for f in [o_p, y_p]: 
                if os.path.exists(f): os.remove(f)
            
            st.rerun()
