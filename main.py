import streamlit as st
import PIL.Image as Image
import google.generativeai as genai
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. НАСТРОЙКИ API ---
API_KEY = "AIzaSyCkaJmvI0dCxfm-xVmQcCJ-n9ZIFUMjsFI" 
genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. ТОТ САМЫЙ ЗОЛОТОЙ ПРОМПТ (НЕПРИКОСНОВЕННЫЙ) ---
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

# --- 3. БАЗА ДАННЫХ (АРХИВ) ---
def init_db():
    conn = sqlite3.connect('stoma_records.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS patients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, analysis TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(name, analysis):
    conn = sqlite3.connect('stoma_records.db')
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO patients (name, date, analysis) VALUES (?, ?, ?)", (name, date_str, analysis))
    conn.commit()
    conn.close()

init_db()

# --- 4. СКРЫТИЕ СИСТЕМНЫХ МЕНЮ ---
st.set_page_config(page_title="StomaAI PRO", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stToolbar"] {display: none;}
    .footer-custom {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: white; text-align: center;
        padding: 10px; border-top: 1px solid #eee; z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 5. БОКОВАЯ ПАНЕЛЬ (АРХИВ И СКАЧИВАНИЕ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3467/3467830.png", width=80)
    st.title("Архив и отчеты")
    st.write("---")
    
    conn = sqlite3.connect('stoma_records.db')
    c = conn.cursor()
    c.execute("SELECT name, date, analysis FROM patients ORDER BY id DESC")
    records = c.fetchall()
    conn.close()

    if records:
        selected_record = st.selectbox("Выберите запись:", [f"{r[0]} ({r[1]})" for r in records])
        
        if st.button("📥 Скачать PDF"):
            idx = [f"{r[0]} ({r[1]})" for r in records].index(selected_record)
            content = records[idx][2]
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font('Arial', '', 'https://github.com/reingart/pyfpdf/raw/master/font/arial.ttf', uni=True)
            pdf.set_font('Arial', size=11)
            pdf.multi_cell(0, 10, txt=content)
            
            pdf_output = pdf.output(dest='S').encode('latin-1', 'replace')
            st.download_button(label="Сохранить файл", data=pdf_output, file_name=f"Protocol_{records[idx][0]}.pdf")
    else:
        st.write("Архив пуст")

# --- 6. ОСНОВНОЙ ЧАТ (ОБЪЕДИНЕННЫЙ ВИД) ---
st.title("🔬 StomaAI PRO: Облачная Диагностика")

with st.container():
    col1, col2 = st.columns([0.6, 0.4])
    with col1:
        p_name = st.text_input("Инициалы пациента:", "Новый пациент")
    with col2:
        up_file = st.file_uploader("Загрузить снимок", type=['jpg','png','jpeg'])

    clinical_desc = st.text_area("Описание клинической картины...", height=180)
    
    if st.button("Отправить на анализ ✨"):
        if clinical_desc or up_file:
            with st.spinner("Анализ в процессе..."):
                try:
                    img_data = Image.open(up_file).convert("RGB") if up_file else None
                    prompt = f"{ULTRA_PROMPT}\n\nПАЦИЕНТ: {p_name}\nКЛИНИКА: {clinical_desc}"
                    
                    res = llm.generate_content([prompt, img_data]) if img_data else llm.generate_content(prompt)
                    
                    st.divider()
                    analysis_result = res.text
                    st.markdown(analysis_result)
                    
                    save_to_db(p_name, analysis_result)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.warning("Введите описание или прикрепите рентген.")

# --- 7. ФУТЕР ---
st.markdown(f"""
    <div class="footer-custom">
        <p style="color: red; font-weight: bold; margin: 0;">⚠️ ВНИМАНИЕ: Данная система является ознакомительной. ПРИМЕНЕНИЕ ЛЮБЫХ ПРЕПАРАТОВ ВОЗМОЖНО ТОЛЬКО ПОСЛЕ ОЧНОЙ КОНСУЛЬТАЦИИ ВРАЧА.</p>
        <p style="color: #555; font-size: 11px; margin: 0;">Разработчик: <b>Ayaz Nussan</b> | StomaAI PRO 2026</p>
    </div>
    """, unsafe_allow_html=True)
