import re

#from person_builder import PersonProfile
from defines import *
from draw_funcs import *


class HandlerPlaces:
    """Пошук та вибірка адрес (декілька рядків) з результатів розпізнання OCR"""
    def __init__(self, linked_person):
        self.data_ukr = linked_person.data_ukr
        self.inline_title = PERS_TITL_LOC  # відступ розміщення заголовків
        self.inline_value = PERS_VALS_LOC  # відступ розміщення значень
        self.pic = linked_person.pic  # зображення OCR (для нанесення пояснювальних фігур, написів)

    def get_place_birth(self):
        """Пошук місця народження"""
        birth_value = None
        birth_title_y_loc = None    # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        next_section_y_loc = None   # Позиція по вертикалі "у" (рх) з якої починається наступна секція
        birth_occur = []            # Позиції у яких зустрічається слово "народження"
        place_occur = []            # Позиції у яких зустрічається слово "Місце"

        # Пошук заголовка:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            place_word_present = re.search(r'(Місце)', t)
            if place_word_present:
                place_occur.append(y)
            birth_word_present = re.search(r'(народження)', t)
            if birth_word_present:
                birth_occur.append(y)
        for p in place_occur:
            if not birth_title_y_loc:
                for b in birth_occur:
                    if abs(p-b) <= ROW_HEIGHT + OFFSET:  # Місце, де слова "Місце" та "народження" - поруч
                        birth_title_y_loc = b if b <= p else p  # Розташування визначається за вищим словом (Дата)
        if birth_title_y_loc:
            self.pic = line_h(self.pic, birth_title_y_loc, C_R)
            self.pic = d_text(self.pic, 5, birth_title_y_loc, f'birth place(y={birth_title_y_loc})', color=C_R)
        # Припинити, якщо не знайдено заголовок:
        if birth_title_y_loc is None:
            return None

        # Пошук закінчення секції:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (y > birth_title_y_loc) and ((self.inline_title - OFFSET) < x < (self.inline_value - OFFSET*5)):
                if not (str(t).startswith('Місце') | str(t).startswith('народження') | (not bool(t))):
                    next_section_y_loc = y
                    self.pic = cv2.line(self.pic, (0, y - OFFSET*2), (PAGE_W, y - OFFSET*2), C_M, 1)
                    self.pic = d_text(self.pic, 5, y-30, f'lim(y={y})', color=C_M)
                    break

        # Припинити, якщо не визначено межі секції:
        if next_section_y_loc is None:
            return None

        # Збір слів з ділянки, яка містить значення місця народження:
        result_list = []
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if PLACE_X_LIM > x > (self.inline_value - OFFSET) and \
                    (birth_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET*2):
                result_list.append(t)
                self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if result_list:
            result_string = ' '.join(result_list)
            birth_value = self._clear_adr_line(result_string)
        return birth_value

    def get_place_live(self):
        """Пошук адреси"""
        adr_value = None
        adr_title_y_loc = None  # Позиція по вертикалі "y" (px) заголовка
        next_section_y_loc = None
        place_occur = []  # Позиції у яких зустрічається слово "народження"
        living_occur = []  # Позиції у яких зустрічається слово "Місце"

        # Визначення лінії (позиції по вертикалі) з якої починається запис адреси (заголовок):
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            place_word_present = re.search(r'(Місце)', t)
            if place_word_present:
                place_occur.append(y)
            living_word_present = re.search(r'(проживання)', t)
            if living_word_present:
                living_occur.append(y)
        for p in place_occur:
            if not adr_title_y_loc:
                for liv in living_occur:
                    if abs(p-liv) <= ROW_HEIGHT - 5:  # Місце, де слова "Місце" та "проживання" - поруч
                        adr_title_y_loc = liv if liv <= p else p  # Розташування визначається за вищим словом (Місце)
        if adr_title_y_loc:
            self.pic = line_h(self.pic, adr_title_y_loc, C_R)
            self.pic = d_text(self.pic, 5, adr_title_y_loc, f'adr(y={adr_title_y_loc})', color=C_R)
        # Якщо не знайдено заголовок - припинення пошуку:
        if not adr_title_y_loc:
            return None

        # Пошук початку наступної секції (для обмеження пошуку поточної адреси) - заголовок з відступом inline_title:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (y > adr_title_y_loc) and ((self.inline_title - OFFSET) < x < (self.inline_title + OFFSET)):
                t = str(t)
                if not (t.startswith('Місце') | t.startswith('проживання') | t.startswith('перебування') | (t == '')):
                    next_section_y_loc = y
                    self.pic = cv2.line(self.pic, (0, y - OFFSET - 2), (PAGE_W, y - OFFSET - 2), C_M, 1)
                    self.pic = d_text(self.pic, 5, y-30, f'lim(y={y})', color=C_M)
                    break
        if next_section_y_loc is None:
            return None

        # Накопичення слів у ділянці документу (визначена попередньо)
        result_list = []
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if PLACE_X_LIM > x > (self.inline_value - OFFSET) and \
                    (adr_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET):
                result_list.append(t)
                self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if result_list:
            result_string = ' '.join(result_list)
            adr_value = self._clear_adr_line(result_string)

        # Нанесення лінії обмеження адреси (обмежити від фото):
        self.pic = line_v(self.pic, PLACE_X_LIM, color=C_R)
        self.pic = d_text(self.pic, PLACE_X_LIM + 5, 240, f'places lim (x={PLACE_X_LIM})', color=C_R)

        return adr_value

    @staticmethod
    def _clear_adr_line(text_line: str) -> str:
        """Очищення рядку адрес, форматування кемелкейсом"""
        address_types = ['Район', "Область", "Місто", 'Село']
        text_line = re.sub(r' +|\n', ' ', text_line)
        text_line = re.sub(r'УКРАЇНА, ', '', text_line)
        text_line = re.sub(r'УКРАЇНА ', '', text_line)
        text_line = text_line.strip(' ,')

        # Всі слова кемелкейсом:
        words = re.finditer(r"([\S`’']{2,})| ([\S`’']{2,})", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().title())
                text_line = text_line.replace("\n", ' ')
                for adr_type in address_types:
                    text_line = text_line.replace(adr_type, adr_type.lower())

        # Виправлення неправильно застосування кемелкейсу для однокореневих слів:
        words = re.finditer(r"[ ]([А-ЯІЇЙ`’'\-][а-яіїй`’'\-]+[А-ЯІЇЙ`’'\-]+)[ ,]", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().title())
                text_line = text_line.replace("\n", ' ')
                for adr_type in address_types:
                    text_line = text_line.replace(adr_type, adr_type.lower())

        # Виправлення неправильно застосування кемелкейсу для слів з апострофом:
        words = re.finditer(r"([А-Яа-яІЇЙЄ][`’']+[А-Яа-яІЇЙЄ]{2,})", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(1), w.group(1).lower())
                text_line = text_line.replace("\n", ' ')

        # Скорочення (буд.|кв.|...) всі літери малі:
        words = re.finditer(r"[\S]*\. ", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().lower())

        # Видалення унікального номеру території
        text_line = re.sub(r" .{2,5}[\d]{15,17}$", '', text_line)
        text_line = text_line.strip()
        # Видалення дати реєстрації:
        text_line = re.sub(r"\d{8}", '', text_line)
        text_line = text_line.strip()
        # Виправлення пунктуації:
        text_line = text_line.replace(' Кв.', ", кв.")
        text_line = text_line.replace(' кв. ', ", кв.")
        text_line = text_line.replace(' буд. ', ", ")
        text_line = text_line.replace('Вулиця', "вул.")
        text_line = text_line.replace(' Б-Р ', " бульвар ")
        text_line = text_line.replace(' вул. ', ", вул.")
        text_line = text_line.replace('/М.', " місто ")
        text_line = text_line.replace('Провулок', "пров.")
        text_line = text_line.replace('Смт ', "смт.")
        text_line = text_line.replace(' Оа7/', "")
        text_line = text_line.replace(' Оаз', "")
        text_line = text_line.replace(' Буд.', ", ")
        text_line = text_line.replace(' Т ', " смт.")
        text_line = text_line.replace(' М ', " м.")
        text_line = text_line.replace('П/Б', "(п/б)")
        text_line = text_line.replace(' М-Н ', " мікрорайон ")
        text_line = text_line.replace(' C ', " село ")
        text_line = text_line.replace(' Проспект ', ", просп.")
        text_line = text_line.replace(' Гурт', " (гуртожиток)")
        text_line = re.sub(r" .{2,5}[\d]{15,17}$", '', text_line)
        text_line = re.sub(r"^М\.", 'м.', text_line)
        return text_line
