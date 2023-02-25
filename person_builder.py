"""
Модуль формування екземплярів профайлів зі словника розпізнаного тексту
"""
import io
import re
from typing import Union

from pdf_processing import get_cv_image
import cv2

OFFSET = 10             # можлива похибка при визначенні меж боксу слова (у пікселях)
ROW_HEIGHT = (68+2)     # типова висота рядку у пікселях (для крокування)
BLANK_MIN = 345         # межі значення номеру бланку по х
BLANK_MAX = 600         # межі значення номеру бланку по х
CREATED_MIN = 900       # межі значення дати видачі по х
CREATED_MAX = 1100      # межі значення дати видачі по х
EXPIRED_MIN = 1450      # початок значення "Дійсний до" по х
OFFICE_TIT_X = 183      # початок заголовку "Орган видачі" по х
OFFICE_VAL_X = 450      # початок значення "Орган видачі" по х

C_R = (0, 0, 255)
C_G = (0, 200, 0)
C_B = (255, 0, 0)
C_M = (255, 0, 255)
C_C = (255, 0, 255)
C_Y = (0, 200, 200)

DEF_COLOR = C_G
TEXT_DEF_THICK = 1
TEXT_DEF_SIZE = 0.6
LINE_DEF_THICK = 2
DEF_RADIUS = 5
DEF_FONT = cv2.FONT_HERSHEY_SIMPLEX
PAGE_H = 3368
PAGE_W = 2382


def d_text(img, x, y, text, font=DEF_FONT, size=TEXT_DEF_SIZE, color=DEF_COLOR, thick=TEXT_DEF_THICK):
    img = cv2.putText(img, text, (x+5+OFFSET, y-5-OFFSET), font, size, color, thick)
    return img


def d_rect(img, x, y, h, w, color=DEF_COLOR, desc=None, line=LINE_DEF_THICK):
    img = cv2.rectangle(img, (x, y), (x + w, y + h), color, line)
    if desc:
        img = d_text(img, x, y, desc, color=color)
    return img


def d_circ(img, x, y, radius=DEF_RADIUS, color=DEF_COLOR, desc=None):
    img = cv2.circle(img, (x, y), radius=radius, color=color, thickness=LINE_DEF_THICK)
    if desc:
        img = d_text(img, x, y, desc, color=color)
    return img


def line_h(img, y, color=C_C, thick=LINE_DEF_THICK):
    img = cv2.line(img, (0, y), (PAGE_W, y), color, thick)
    img = cv2.line(img, (0, y + OFFSET), (PAGE_W, y+OFFSET), color, 1)
    img = cv2.line(img, (0, y - OFFSET), (PAGE_W, y-OFFSET), color, 1)
    return img


def line_v(img, x, color=DEF_COLOR, thick=LINE_DEF_THICK):
    img = cv2.line(img, (x, 0), (x, PAGE_H), color, thick)
    img = cv2.line(img, (x - OFFSET, 0), (x-OFFSET, PAGE_H), color, 1)
    img = cv2.line(img, (x + OFFSET, 0), (x+OFFSET, PAGE_H), color, 1)
    return img


def d_elem(img, x, y, h, w, color=DEF_COLOR, desc=None, line=LINE_DEF_THICK):
    img = d_rect(img, x, y, h, w, color, desc, line)
    img = d_circ(img, x, y, color=color)
    return img


class DocumentId:
    """Клас формування зведених даних про окремий документ"""
    blank_number = None
    date_created = None
    date_expired = None
    pass_office = None
    expired_status = None
    non_office_starts = ['Номер', 'Дата', 'Дійсний', 'необмежений', 'Документ', 'Паспорт(и)']

    def __init__(self, blank, date1, date2, status, office):
        self.blank_number = blank
        self.date_created = date1
        self.date_expired = date2
        self.pass_office = office
        self.expired_status = status

    def __str__(self):
        return str(self.blank_number) + " (" \
               + str(self.date_created) + " - " \
               + str(self.date_expired) + ")" \
               + str(self.pass_office)


class PersonProfile:
    """Клас формування інформації про профайл"""
    name_full = None
    dob = None
    pob = None
    code_uni = None
    code_tax = None
    address = None
    live_from = None
    phone = None
    image = None

    address_types = ['Район', "Область"]

    def __init__(self, data: dict, data_eng: dict, person_photo: io.BytesIO, origin_file: Union[str, None] = None):
        self.data = data
        self.data_eng = data_eng
        self.inline_title = None
        self.inline_value = None
        self.words = data.get('text', [])
        self.pos_x = data.get('left', [])
        self.pos_y = data.get('top', [])
        self.width = data.get('width', [])
        self.heigh = data.get('height', [])
        self.level = data.get('level', [])

        self.pic = get_cv_image(origin_file)

        self.certificate_of_birth = []
        self.pass_internal = []
        self.pass_external = []

        assert self._check_validation() is True, "Відсутні очікувані ключові слова (такі як ОСОБОВА/КАРТКА/міграційної)"
        self.name_full = self._get_full_name()
        self.dob = self._get_dob()
        self.code_uni = self._get_uni_code()
        self.code_tax = self._get_tax_code()
        self.phone = self._get_phone()
        self.pob = self._get_place_birth()
        self.address = self._get_place_live()
        self._get_cert_birth()
        self._get_pass_int()
        self._get_pass_ext()
        self.image = person_photo if person_photo else None

    def save_ocr_plot(self):
        try:
            cv2.imwrite(f"{self.code_tax}_result.png", self.pic)
            return ''
        except Exception as err:
            return err



    def __str__(self):
        desc_text = f'{self.name_full}, {self.dob} р.н.:' \
                f'\n\tМісце народження: {self.pob}' \
                f'\n\tУНЗР:             {self.code_uni}' \
                f'\n\tРНОКПП:           {self.code_tax}' \
                f'\n\tАдреса:           {self.address}' \
                f'\n\tЗасіб зв\'язку:   {self.phone}'
        if self.pass_external:
            desc_text += '\n\tПаспорти (внутрішні):\n\t\t'
            pass_int_list = [str(x) for x in self.pass_internal]
            pass_int_print = '\n\t\t'.join(pass_int_list)
            desc_text += pass_int_print

        if self.pass_external:
            desc_text += '\n\tПаспорти (закордонні):\n\t\t'
            pass_ext_list = [str(x) for x in self.pass_external]
            pass_ext_print = '\n\t\t'.join(pass_ext_list)
            desc_text += pass_ext_print
        return desc_text

    def _check_validation(self) -> bool:
        """Перевірка наявності слів, які свідчать про те, що файл відносить до профайлу особи"""
        for w in self.words:
            res = re.search(r'(ОСОБОВА|КАРТКА|міграційної)', w)
            if res:
                return True
        return False

    def _get_full_name(self) -> Union[str, None]:
        """Пошук повного імені поблизу назв відповідних полів профайлу"""
        sn_y = None  # Позиція прізвища
        fn_y = None  # Позиція ім'я
        tn_y = None  # Позиція по батькові

        sn_t = None  # Текст прізвища
        fn_t = None  # Текст імені
        tn_t = None  # Текст по батькові

        # Пошук розташування заголовків по "у":
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if sn_y is None:
                sn_y = y if re.search(r'(Прізвище)', t) else None
                self.inline_title = x if re.search(r'(Прізвище)', t) else None  # фіксується лінія заголовків по "х"
                if sn_y:
                    self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                    self.pic = line_h(self.pic, y, C_R)
                    self.pic = d_text(self.pic, 5, y, f's_name(y={y})', color=C_R)

            if fn_y is None:
                fn_y = y if re.search(r'(Ім.я)', t) else None
                if fn_y:
                    self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                    self.pic = line_h(self.pic, y, C_R)
                    self.pic = d_text(self.pic, 5, y, f'f_name(y={y})', color=C_R)

            if tn_y is None:
                tn_y = y if re.search(r'(батькові)', t) else None
                if tn_y:
                    self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                    self.pic = line_h(self.pic, y, C_R)
                    self.pic = d_text(self.pic, 5, y, f't_name(y={y})', color=C_R)


        def parse_name(expected_y_location: int, current_y: int, text: str) -> Union[str, None]:
            """Парсинг частини імені в межах дії заголовку"""
            if (expected_y_location - OFFSET) < current_y < (expected_y_location + OFFSET):
                mask_test = re.search(r"([А-ЯІЇЄ`’'\-]{2,})", text)
                if mask_test:
                    return mask_test.group(1)
            return None

        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            # Значення ПРІЗВИЩЕ:
            if sn_y and sn_t is None:
                test_result = parse_name(expected_y_location=sn_y, current_y=y, text=t)
                sn_t = test_result if test_result else None
                self.inline_value = x if test_result else None
                if test_result:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')

            # Значення ІМ'Я:
            if fn_y and fn_t is None:
                test_result = parse_name(expected_y_location=fn_y, current_y=y, text=t)
                fn_t = test_result if test_result else None
                if test_result:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')


            # Значення ПО БАТЬКОВІ:
            if tn_y and tn_t is None:
                test_result = parse_name(expected_y_location=tn_y, current_y=y, text=t)
                tn_t = test_result if test_result else None
                if test_result:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')

        if self.inline_value:
            self.pic = cv2.line(self.pic, (self.inline_value, 0), (self.inline_value, 1382), C_R, LINE_DEF_THICK)
            self.pic = cv2.line(self.pic, (self.inline_value+OFFSET, 0), (self.inline_value+OFFSET, 1382), C_R, 1)
            self.pic = cv2.line(self.pic, (self.inline_value - OFFSET, 0), (self.inline_value - OFFSET, 1382), C_R, 1)
            self.pic = d_text(self.pic, self.inline_value+5, 240, f'values line (x={self.inline_value})', color=C_R)

        if self.inline_title:
            self.pic = line_v(self.pic, self.inline_title, color=C_R)
            self.pic = d_text(self.pic, self.inline_title + 5, 240, f'headers line (x={self.inline_title})', color=C_R)

        assert sn_t is not None, "Не розпізнано ПРІЗВИЩЕ"
        assert fn_t is not None, "Не розпізнано ІМ'Я"

        result_list = [x for x in [sn_t, fn_t, tn_t] if x is not None]
        result_string = ' '.join(result_list)
        return result_string

    def _get_dob(self) -> Union[str, None]:
        """Пошук дати народження"""
        birth_value = None
        birth_title_y_loc = None    # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        birth_occur = []            # Позиції у яких зустрічається слово "народження"
        date_occur = []             # Позиції у яких зустрічається слово "Дата"

        # Пошук випадку коли слова "Дата" та "народження" розташовані поруч та визначення координати по "у":
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            date_word_present = re.search(r'(Дата)', t)
            if date_word_present:
                date_occur.append(y)
            birth_word_present = re.search(r'(народження)', t)
            if birth_word_present:
                birth_occur.append(y)
        for d in date_occur:
            if not birth_title_y_loc:
                for b in birth_occur:
                    if abs(d-b) <= ROW_HEIGHT + OFFSET:  # Місце, де слова "Дата" та "народження" - поруч
                        birth_title_y_loc = b if b <= d else d  # Розташування визначається за вищим словом (Дата)
        if birth_title_y_loc:
            self.pic = line_h(self.pic, birth_title_y_loc, C_R)
            self.pic = d_text(self.pic, 5, birth_title_y_loc, f'Birth title(y={birth_title_y_loc})', color=C_R)
        # Припинити, якщо не знайдено заголовок:
        if not birth_title_y_loc:
            return None

        # Виділення значення дати навпроти встановленого розташування заголовку - birth_title_y_loc:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (birth_title_y_loc - OFFSET < y < birth_title_y_loc + OFFSET):
                birth_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if birth_present:
                    birth_value = birth_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return birth_value

    def _get_uni_code(self) -> Union[str, None]:
        """Пошук особистого номеру УНЗР"""
        uni_code_value = None
        uni_code_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            unicode_title_present = re.search(r'(УНЗР)', t)
            if unicode_title_present:
                uni_code_title_y_loc = y
                self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                self.pic = line_h(self.pic, y, C_R)
                self.pic = d_text(self.pic, 5, y, f'uni code(y={y})', color=C_R)
                break

        # Припинити, якщо не знайдено заголовок:
        if uni_code_title_y_loc is None:
            return None

        # Пошук значення:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (uni_code_title_y_loc - OFFSET < y < uni_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{13})", t)
                if value_present:
                    uni_code_value = value_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return uni_code_value

    def _get_tax_code(self) -> Union[str, None]:
        """Пошук коду платника податків (РНОКПП)"""
        tax_code_value = None
        tax_code_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            tax_title_present = re.search(r'(РНОКПП)', t)
            if tax_title_present:
                tax_code_title_y_loc = y
                self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                self.pic = line_h(self.pic, y, C_R)
                self.pic = d_text(self.pic, 5, y, f'tax code(y={y})', color=C_R)
                break

        # Припинити, якщо не знайдено заголовок:
        if tax_code_title_y_loc is None:
            return None

        # Пошук значення:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (tax_code_title_y_loc - OFFSET < y < tax_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{10})", t)
                if value_present:
                    tax_code_value = value_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return tax_code_value

    def _get_phone(self) -> Union[str, None]:
        """Пошук засобу зв'язку (телефон)"""
        phone_value = None
        phone_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            phone_title_present = re.search(r'(Телефон)', t)
            if phone_title_present:
                phone_title_y_loc = y
                self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                self.pic = line_h(self.pic, y, C_R)
                self.pic = d_text(self.pic, 5, y, f'phone(y={y})', color=C_R)
                break

        # Припинити, якщо не знайдено заголовок:
        if phone_title_y_loc is None:
            return None

        # Пошук значення:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
                    (phone_title_y_loc - OFFSET < y < phone_title_y_loc + OFFSET):
                value_present = re.search(r"(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})", t)
                if value_present:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    phone_value = value_present.group(1)
                    phone_value = phone_value[1:] if phone_value.startswith('+') else phone_value
                    phone_value = '38' + phone_value if len(phone_value) == 10 else phone_value
                    break
        return phone_value

    def _get_place_birth(self):
        """Пошук місця народження"""
        birth_value = None
        birth_title_y_loc = None    # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        next_section_y_loc = None   # Позиція по вертикалі "у" (рх) з якої починається наступна секція
        birth_occur = []            # Позиції у яких зустрічається слово "народження"
        place_occur = []            # Позиції у яких зустрічається слово "Місце"

        # Пошук заголовка:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
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
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
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
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if x > (self.inline_value - OFFSET) and (birth_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET*2):
                result_list.append(t)
                self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if result_list:
            result_string = ' '.join(result_list)
            birth_value = self._clear_adr_line(result_string)
        return birth_value

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
        words = re.finditer(r"[ ]([А-ЯІЇЙ`’'\-]{1}[а-яіїй`’'\-]{1,}[А-ЯІЇЙ`’'\-]{1,})[ ,]", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().title())
                text_line = text_line.replace("\n", ' ')
                for adr_type in address_types:
                    text_line = text_line.replace(adr_type, adr_type.lower())

        # Виправлення неправильно застосування кемелкейсу для слів з апострофом:
        words = re.finditer(r"([А-Яа-яІЇЙЄ]{1}[`’']{1,}[А-Яа-яІЇЙЄ]{2,})", text_line)
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
        text_line = re.sub(r" .{2,5}\d{17}", '', text_line)
        text_line = text_line.strip()
        # Видалення дати реєстрації:
        text_line = re.sub(r"\d{8}", '', text_line)
        text_line = text_line.strip()
        # Виправлення пунктуації:
        text_line = text_line.replace(' кв. ', ", кв.")
        text_line = text_line.replace(' буд. ', ", ")
        text_line = text_line.replace(' вул. ', ", вул.")
        return text_line

    def _get_place_live(self):
        """Пошук адреси"""
        adr_value = None
        adr_title_y_loc = None  # Позиція по вертикалі "y" (px) заголовка
        next_section_y_loc = None
        place_occur = []  # Позиції у яких зустрічається слово "народження"
        living_occur = []  # Позиції у яких зустрічається слово "Місце"

        # Визначення лінії (позиції по вертикалі) з якої починається запис адреси (заголовок):
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
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
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
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
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if x > (self.inline_value - OFFSET) and (adr_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET):
                result_list.append(t)
                self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if result_list:
            result_string = ' '.join(result_list)
            adr_value = self._clear_adr_line(result_string)
        return adr_value

    def _get_document_section_range(self, start_word: str, end_word: str) -> Union[tuple, None]:
        """
        Визначення меж секції (від одного ключого слова до іншого).
        Якщо визначене у аргументах друге слово відсутнє - спроба пошуку типових для заголовків блоків

        :returns: координати у пікселях по вертикалі (входження першого слова, входження другого)
        """
        section_starts = None
        section_ends = None

        # Прохід по всім словам та координатам для пошуку входжень ключових слів
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if section_starts and section_ends:
                break

            if section_starts is None:
                start_present = re.search(f'({start_word}$)', t)
                if start_present:
                    section_starts = y
            if section_ends is None:
                end_present = re.search(f'({end_word}$)', t)
                if end_present:
                    section_ends = y

        if section_starts and not section_ends:
            for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
                if y > (section_starts + ROW_HEIGHT + OFFSET):
                    end_present = re.search(r'(Свідоцтво|Паспорт|Запит)', t)
                    if end_present:
                        section_ends = y
                        break

        # Повернення результатів опрацювання:
        if section_starts and section_ends:
            # Неочікуваний випадок, якщо початок блоку визначений пізніше ніж закінчення:
            if section_starts > section_ends:
                return None, None
            else:
                self.pic = line_h(self.pic, section_starts, C_Y)
                self.pic = d_text(self.pic, 5, section_starts+40, f's_start(y={section_starts})', color=C_Y)
                self.pic = line_h(self.pic, section_ends, C_Y)
                self.pic = d_text(self.pic, 5, section_ends-5, f's_end(y={section_ends})', color=C_Y)
                return section_starts, section_ends
        else:
            return None, None

    def _get_blanks_ranges(self, section_start: int, section_end: int) -> Union[list, None]:
        """Формування списку пар координат по осі у - межі запису окремих паспортів"""
        kw_present = []  # координати по "у" у яких зустрічається слово "Номер"
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if (section_start - OFFSET) < y < (section_end + OFFSET):
                if str(t).startswith('Номер'):
                    kw_present.append(y)
                    self.pic = d_elem(self.pic, x, y, h, w, color=C_M, desc=f'pass here(y={y})')
                    self.pic = line_h(self.pic, y, C_M)
        if not kw_present:
            return None

        kw_present.append(section_end)  # доповнення кінцем секції для формування останньої пари
        kw_present.sort()

        blanks_ranges = []
        for i in range(len(kw_present)):
            try:
                blanks_ranges.append((kw_present[i], kw_present[i+1]))
            except IndexError:
                break
        return blanks_ranges

    def _create_pass(self, y_min: int, y_max: int, lang='ukr') -> Union[DocumentId, None]:
        """
        Створення інстансу ДокументІД

        :param y_min: координата по вертикалі (у) з якої починається ділянка з відомостями про поточний документ
        :param y_max: координата по вертикалі (у) з якої починається наступна секції (не відноситься до документу)
        """
        assert lang in ['ukr', 'eng']

        blank = None
        date_created = None
        date_expired = None
        expired_status = None
        office = None
        office_lines = []
        office_y = None

        # якщо тип документу потребує розпізнання англійських літер - пошук номеру бланку:
        if lang == 'eng':
            for i, (x, y, t, h, w, c) in enumerate(zip(self.data_eng['left'], self.data_eng['top'], self.data_eng['text'], self.data_eng['height'], self.data_eng['width'], self.data_eng['conf'])):
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ]{7,10}$)", t)
                    if blank_present:
                        blank = blank_present.group(1)
                        self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                        self.pic = d_rect(self.pic,
                                          x=BLANK_MIN - OFFSET,
                                          y=y_min - OFFSET,
                                          h=(y_min + OFFSET) - (y_min - OFFSET),
                                          w=BLANK_MAX - BLANK_MIN,
                                          color=C_B, line=1)
                        self.pic = d_text(self.pic,
                                          BLANK_MIN - 25,
                                          y_min + 13,
                                          'search_area',
                                          color=C_B, thick=1,
                                          size=0.4)
                        break

        # проходження по всім записам з вибіркою атрибутів ДокументІД у вже відомих позиціях:
        for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
            if lang == 'ukr':
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ]{7,10}$)", t)
                    if blank_present:
                        blank = blank_present.group(1)
                        self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                        self.pic = d_rect(self.pic,
                                          x=BLANK_MIN - OFFSET,
                                          y=y_min - OFFSET,
                                          h=(y_min + OFFSET) - (y_min - OFFSET),
                                          w=BLANK_MAX - BLANK_MIN,
                                          color=C_B, line=1)
                        self.pic = d_text(self.pic,
                                          BLANK_MIN - 25,
                                          y_min + 13,
                                          'search_area',
                                          color=C_B, thick=1,
                                          size=0.4)

            # Дата видачі:
            if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((CREATED_MIN - OFFSET) < x < (CREATED_MAX + OFFSET)):
                created_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if created_present:
                    date_created = created_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    self.pic = d_rect(self.pic,
                                      x=CREATED_MIN - OFFSET,
                                      y=y_min - OFFSET,
                                      h=(y_min + OFFSET) - (y_min - OFFSET),
                                      w=CREATED_MAX - CREATED_MIN,
                                      color=C_B, line=1)
                    self.pic = d_text(self.pic,
                                      CREATED_MIN - 25,
                                      y_min + 13,
                                      'search_area',
                                      color=C_B, thick=1,
                                      size=0.4)
            # Дійсний до:
            if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((EXPIRED_MIN - OFFSET) < x):
                expired_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if expired_present:
                    date_expired = expired_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    self.pic = d_rect(self.pic,
                                      x=EXPIRED_MIN - OFFSET,
                                      y=y_min - OFFSET,
                                      h=(y_min + OFFSET) - (y_min - OFFSET),
                                      w=PAGE_W - EXPIRED_MIN - 10,
                                      color=C_B, line=1)
                    self.pic = d_text(self.pic,
                                      EXPIRED_MIN - 25,
                                      y_min + 13,
                                      'search_area',
                                      color=C_B, thick=1,
                                      size=0.4)
                # Статус обмеження (недійсний/необмежений):
                spec_status = re.search(r"(недійсним)|(необмежений)", t)
                if spec_status:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    if spec_status.group(0) == 'недійсним':
                        expired_status = 'недійсний'
                    elif spec_status.group(0) == 'необмежений':
                        expired_status = 'необмежений'
            # Заголовок запису про орган видачі документу:
            if ((y_min - OFFSET) < y < (y_max - OFFSET)) and ((OFFICE_TIT_X - OFFSET) < x < (OFFICE_TIT_X + OFFSET)):
                office_title_present = re.search(r"(Орган)", t)
                if office_title_present:
                    office_y = y
                    self.pic = d_elem(self.pic, x, y, h, w, C_M, desc=f'({x};{y})')
                    self.pic = d_rect(self.pic,
                                      x=EXPIRED_MIN - OFFSET,
                                      y=y_min - OFFSET,
                                      h=(y_min + OFFSET) - (y_min - OFFSET),
                                      w=PAGE_W - EXPIRED_MIN - 10,
                                      color=C_B, line=1)
                    self.pic = d_text(self.pic,
                                      EXPIRED_MIN - 25,
                                      y_min + 13,
                                      'search_area',
                                      color=C_B, thick=1,
                                      size=0.4)

        # Якщо знайдено заголовок органу видачі - вибрати весь текст до кінця секції документу:
        if office_y:
            self.pic = d_rect(self.pic,
                              OFFICE_VAL_X,
                              office_y - OFFSET,
                              (y_max - OFFSET-2) - (office_y - OFFSET),
                              PAGE_W - OFFICE_VAL_X,
                              color=C_B, line=1)
            self.pic = d_text(self.pic, OFFICE_VAL_X - 10, office_y + 13, 'search_area', color=C_B, thick=1, size=0.4)
            for i, (x, y, t, h, w, c) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'], self.data['height'], self.data['width'], self.data['conf'])):
                if ((office_y - OFFSET) < y < (y_max - OFFSET)) and ((OFFICE_VAL_X - OFFSET) < x):
                    office_lines.append(t)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if office_lines:
            office_string = ' '.join(office_lines)
            office_string = office_string.strip()
            office_string = re.sub(r' +|\n', ' ', office_string)
            office = office_string

        # Створити інстанс, якщо є хоча б номер бланку документу:
        if blank:
            return DocumentId(blank, date_created, date_expired, expired_status, office)
        else:
            return None

    def _get_cert_birth(self):
        """Накопичення та валідація всіх записів свідоцтв"""
        section_starts, section_ends = self._get_document_section_range('Свідоцтво', "Паспорт")
        if not section_starts:
            return None
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                self.certificate_of_birth.append(passport)

    def _get_pass_int(self):
        """Накопичення та валідація всіх записів паспортів (внутрішніх)"""
        section_starts, section_ends = self._get_document_section_range(r'Паспорт', r"Паспорт\(и\)")
        if not section_starts:
            return None
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                self.pass_internal.append(passport)

    def _get_pass_ext(self):
        """Накопичення та валідація всіх записів паспортів (закордонних)"""
        section_starts, section_ends = self._get_document_section_range(r"Паспорт\(и\)", r"Запит")
        if not section_starts:
            return None
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1], lang='eng')
            if passport:
                self.pass_external.append(passport)

    def print_ocr_result(self):
        """
        Друк розпізнаних слів (для дебагінгу):
        - порядковий номер
        - рівень
        - позиція по вертикалі (рх)
        - позиція по горизонталі (рх)
        - зміст
        """
        data = self.data
        for i in range(len(data['level'])):
            print(i, ':   ', data['level'][i], ' - ', data['top'][i], '/', data['left'][i], '   ', data['text'][i])
