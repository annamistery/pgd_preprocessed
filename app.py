# Файл: app.py

import streamlit as st
import time
from datetime import datetime

# Импортируем ваши классы
from cashka_preprocessor import PersonalityProcessor
from pgd_bot import PGD_Person_Mod  # Убедитесь, что pgd_bot.py в той же папке

# --- Вспомогательные функции ---

def perform_full_calculation(name: str, dob: datetime, gender: str) -> tuple | None:
    """
    Выполняет полный расчет личности с использованием класса PGD_Person_Mod.
    Возвращает кортеж с тремя словарями: (основные_точки, задачи, периоды)
    или None в случае ошибки.
    """
    try:
        # 1. Преобразуем данные из формата Streamlit в формат, ожидаемый классом
        date_str = dob.strftime('%d.%m.%Y')
        sex_char = 'Ж' if gender == 'Женский' else 'М'

        # 2. Создаем экземпляр класса
        person_mod = PGD_Person_Mod(name, date_str, sex_char)

        # 3. Выполняем все расчеты
        main_cup_data = person_mod.calculate_points()
        tasks_data = person_mod.tasks()
        periods_data = person_mod.periods_person()

        # 4. Проверяем, не вернул ли основной расчет ошибку
        if not isinstance(main_cup_data, dict):
            st.error(f"Ошибка при расчете основной матрицы: {main_cup_data}")
            return None

        # Класс PersonalityProcessor ожидает словарь, где основной словарь находится
        # под ключом, а не просто сам словарь.
        wrapped_cup_data = {'Основная чашка': main_cup_data}

        return wrapped_cup_data, tasks_data, periods_data

    except Exception as e:
        st.error(f"Произошла критическая ошибка при расчете: {e}")
        return None


def format_results_for_download(name: str, dob: datetime, results: dict, tasks: dict, periods: dict) -> str:
    """Форматирует все результаты в красивую строку для .txt файла."""
    header = (
        f"Анализ личности\n{'='*20}\n"
        f"Имя: {name}\nДата рождения: {dob.strftime('%d.%m.%Y')}\n{'='*20}\n"
    )

    # Добавляем задачи
    tasks_content = "\n--- Задачи по Матрице ---\n"
    if tasks:
        for key, value in tasks.items():
            tasks_content += f"{key}: {value if value is not None else '-'}\n"
    
    # Добавляем периоды
    periods_content = "\n--- Бизнес Периоды ---\n"
    if periods and "Бизнес периоды" in periods:
        for key, value in periods["Бизнес периоды"].items():
            periods_content += f"{key}: {value if value is not None else '-'}\n"

    # Добавляем основное описание
    main_content = "\n--- Подробное описание ---\n"
    for key, value in results.items():
        # Здесь мы используем чистый текст, полученный из PersonalityProcessor
        clean_value = value
        main_content += f"\n--- {key} ---\n{clean_value}\n"
    
    return header + tasks_content + periods_content + main_content


# --- Интерфейс приложения Streamlit ---

st.set_page_config(page_title="Анализ Личности", layout="wide")
st.title("Сервис Психологической Диагностики")

# Инициализация состояния сессии
if 'results' not in st.session_state:
    st.session_state.results = None
    st.session_state.tasks = None
    st.session_state.periods = None
    st.session_state.processing_time = 0

# --- Блок ввода данных для мобильных устройств (удобнее в expander) ---
with st.expander("Ввод данных для анализа", expanded=True):
    name = st.text_input("Имя", placeholder="Например, Анастасия")
    dob = st.date_input("Дата рождения", value=None, min_value=datetime(1930, 1, 1), format="DD.MM.YYYY")
    gender = st.radio("Пол", ('Женский', 'Мужской'), horizontal=True)
    
    if st.button("🚀 Рассчитать", use_container_width=True):
        if not name or not dob:
            st.warning("Пожалуйста, заполните все поля: Имя и Дата рождения.")
        else:
            progress_bar = st.progress(0, text="Подготовка к анализу...")
            start_time = time.monotonic()
            
            calculation_result = perform_full_calculation(name, dob, gender)
            
            if calculation_result:
                wrapped_cup_data, tasks_data, periods_data = calculation_result
                
                try:
                    processor = PersonalityProcessor(wrapped_cup_data)
                    results = processor.get_full_description()
                    
                    st.session_state.results = results
                    st.session_state.tasks = tasks_data
                    st.session_state.periods = periods_data
                    st.session_state.name = name
                    st.session_state.dob = dob
                    st.session_state.processing_time = time.monotonic() - start_time
                except Exception as e:
                    st.error(f"Произошла ошибка на этапе обработки описаний: {e}")
                    st.session_state.results = None
            else:
                progress_bar.empty()
                st.session_state.results = None


# Основная область для вывода результатов
if st.session_state.results:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"Анализ для **{st.session_state.name}** успешно завершен!")
    with col2:
        st.metric(label="Время обработки", value=f"{st.session_state.processing_time:.2f} сек.")
    
    st.download_button(
        label="📥 Сохранить полный результат в .txt",
        data=format_results_for_download(
            st.session_state.name, st.session_state.dob,
            st.session_state.results, st.session_state.tasks, st.session_state.periods
        ).encode('utf-8'),
        file_name=f"analysis_{st.session_state.name}_{st.session_state.dob.strftime('%Y%m%d')}.txt",
        mime='text/plain'
    )
    
    st.write("---")

    # --- Блок для отображения сводных данных (без изменений, т.к. Streamlit сам адаптирует) ---
    st.header("Сводные данные по матрице")
    col_tasks, col_periods = st.columns(2)

    with col_tasks:
        st.subheader("Задачи по Матрице")
        tasks = st.session_state.tasks
        if tasks:
            for key, value in tasks.items():
                st.markdown(f"**{key}** `{value if value is not None else '-'}`")
        else:
            st.info("Данные по задачам отсутствуют.")

    with col_periods:
        st.subheader("Бизнес Периоды")
        periods = st.session_state.periods
        if periods and "Бизнес периоды" in periods:
            for key, value in periods["Бизнес периоды"].items():
                st.markdown(f"**{key}:** `{value if value is not None else '-'}`")
        else:
            st.info("Данные по бизнес периодам отсутствуют.")

    st.write("---")
    
    # Блок с подробным описанием
    st.header("Подробное описание по точкам")
    for key, value in st.session_state.results.items():
        with st.expander(f"**{key}**"):
            # Используем st.write для лучшей совместимости с разметкой
            st.write(value)
else:
    st.info("Заполните данные и нажмите 'Рассчитать', чтобы увидеть результат.")