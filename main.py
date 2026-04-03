import streamlit as st
import PIL.Image as Image
from ultralytics import YOLO
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- 1. ТВОЯ КОНФИГУРАЦИЯ ---
API_KEY = "AIzaSyABE6pt1de0Wm-F4VLTkxRk78kjoL9zEUs" 
genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('gemini-1.5-flash')

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

# --- 3. ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ) ---
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

# --- 4. СТАРЫЙ ВИД ИНТЕРФЕЙСА ---
st.set_page_config(page_title="StomaAI PRO Server", layout="wide")

# Твой старый сайдбар с аватаром
with st.sidebar:
    st.image("https://raw.githubusercontent.com/sanjarbekn00-sketch/StomaAI-Pro/main/avatar.png", width=100) # Или твой путь к фото
    st.title("Пациенты")
    patient_name = st.text_input("ФИО пациента:", "Новый пациент")

st.title("🔬 StomaAI PRO: Облачная Диагностика")

# Поля ввода в старом стиле (как на скрине 176)
col_input, col_file = st.columns([0.6, 0.4])

with col_input:
    user_txt = st.text_area("Опишите жалобы или задайте вопрос...", height=150)

with col_file:
    st.write("Загрузить рентген/фото")
    up_file = st.file_uploader("Upload", type=['jpg','png','jpeg'], label_visibility="collapsed")

# Кнопка анализа — теперь она главная
if st.button("Отправить на анализ ✨", use_container_width=True):
    if user_txt or up_file:
        with st.spinner("Анализ в процессе..."):
            img_for_ai = None
            yolo_res_text = ""
            
            if up_file:
                img_for_ai = Image.open(up_file).convert("RGB")
                if yolo_model:
                    res = yolo_model(img_for_ai)
                    det = [yolo_model.names[int(b.cls[0])] for b in res[0].boxes]
                    yolo_res_text = f"Обнаружено на снимке: {', '.join(set(det))}"
                    st.image(res[0].plot(), caption="Результат сканирования", width=500)

            # Формируем запрос
            full_prompt = f"{ULTRA_PROMPT}\nПАЦИЕНТ: {patient_name}\nКЛИНИЧЕСКАЯ КАРТИНА: {user_txt}\nДАННЫЕ YOLO: {yolo_res_text}"
            
            if img_for_ai:
                response = llm.generate_content([full_prompt, img_for_ai])
            else:
                response = llm.generate_content(full_prompt)
            
            # Вывод результата
            st.markdown("---")
            st.markdown(response.text)
            
            # Сохранение в базу
            db.execute("INSERT INTO diag VALUES (?, ?, ?)", (patient_name, datetime.now().strftime("%Y-%m-%d"), response.text))
            db.commit()
    else:
        st.error("Ошибка: Введите текст или загрузите снимок!")

# --- 5. ТВОЙ ФУТЕР ---
st.markdown("---")
st.markdown(f"""
    <div style="text-align: center; color: gray; font-size: 12px;">
        <p>⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p>Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
