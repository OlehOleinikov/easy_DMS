from typing import Union, Tuple, Optional
import re

# from person_builder import PersonProfile
from defines import *
from draw_funcs import *

RX_NAME = re.compile(r"([А-Яа-яІЇєЄ`’'\-]{2,})")
RX_DATE = re.compile(r"(\d{2}.\d{2}.\d{4})")
RX_UNI = re.compile(r"(\d{13})")
RX_TAX = re.compile(r"(\d{10})")
RX_PHONE = re.compile(r"(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})")


class HandlerMainData:
    """Пошук та вибірка основних анкетних даних (один рядок) з результатів розпізнання OCR"""
    def __init__(self, linked_person):
        self.data_ukr = linked_person.data_ukr
        self.inline_title = PERS_TITL_LOC
        self.inline_value = PERS_VALS_LOC
        self.pic = linked_person.pic

    @staticmethod
    def _parse_name(expected_y_location: int, current_y: int, text: str) -> Union[str, None]:
        """Пошук слів схожих на частину імені (прізвище/імя/побатькові) в межах наданої порції тексту"""
        if (expected_y_location - OFFSET) < current_y < (expected_y_location + OFFSET):
            mask_test = re.search(r"([А-Яа-яІЇєЄ`’'\-]{2,})", text)
            if mask_test:
                return mask_test.group(1)
        return None

    def get_names(self) -> Tuple:
        """Пошук повного імені поблизу назв відповідних полів профайлу"""
        sn_y = None  # Позиція прізвища
        fn_y = None  # Позиція ім'я
        tn_y = None  # Позиція по батькові

        sn_t = None  # Текст прізвища
        fn_t = None  # Текст імені
        tn_t = None  # Текст по батькові

        # Пошук розташування заголовків по "у":
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if sn_y is None:
                sn_y = y if re.search(r'(Прізвище)', t) else None
                self.inline_title = x if re.search(r'(Прізвище)', t) else None  # фіксується лінія заголовків по "х"
                if sn_y:
                    print(self.inline_title)
                    self.pic = d_elem(self.pic, x, y, h, w, C_R, desc=f'({x};{y})')
                    self.pic = line_h(self.pic, y, C_R)
                    self.pic = d_text(self.pic, 5, y, f's_name(y={y})', color=C_R)

            if fn_y is None:
                fn_y = y if re.search(r'([Іі]м.я)', t) else None
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

        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            # Значення ПРІЗВИЩЕ:
            if sn_y and sn_t is None:
                if (PERS_VALS_LOC - OFFSET) < x < (PERS_VALS_LOC + OFFSET):
                    test_result = self._parse_name(expected_y_location=sn_y, current_y=y, text=t)
                    sn_t = str(test_result).upper() if test_result else None
                    # self.inline_value = x if test_result else None
                    if test_result:
                        self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')

            # Значення ІМ'Я:
            if fn_y and fn_t is None:
                if (PERS_VALS_LOC - OFFSET) < x < (PERS_VALS_LOC + OFFSET):
                    test_result = self._parse_name(expected_y_location=fn_y, current_y=y, text=t)
                    fn_t = str(test_result).upper() if test_result else None
                    if test_result:
                        self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')

            # Значення ПО БАТЬКОВІ:
            if tn_y and tn_t is None:
                if (PERS_VALS_LOC - OFFSET) < x < (PERS_VALS_LOC + OFFSET):
                    test_result = self._parse_name(expected_y_location=tn_y, current_y=y, text=t)
                    tn_t = str(test_result).upper() if test_result else None
                    if test_result:
                        self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')

        # Нанесення розмітки (лінії в межах яких здійснюється вибірка значень та заголовків):
        if self.inline_value:
            self.pic = cv2.line(self.pic, (self.inline_value, 0), (self.inline_value, 1382), C_R, LINE_DEF_THICK)
            self.pic = cv2.line(self.pic, (self.inline_value+OFFSET, 0), (self.inline_value+OFFSET, 1382), C_R, 1)
            self.pic = cv2.line(self.pic, (self.inline_value - OFFSET, 0), (self.inline_value - OFFSET, 1382), C_R, 1)
            self.pic = d_text(self.pic, self.inline_value+5, 240, f'values line (x={self.inline_value})', color=C_R)

        if self.inline_title:
            self.pic = line_v(self.pic, self.inline_title, color=C_R)
            self.pic = d_text(self.pic, self.inline_title + 5, 240, f'headers line (x={self.inline_title})', color=C_R)

        return sn_t, fn_t, tn_t

    def get_dob(self) -> Union[str, None]:
        """Пошук дати народження"""
        birth_value = None
        birth_title_y_loc = None    # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        birth_occur = []            # Позиції у яких зустрічається слово "народження"
        date_occur = []             # Позиції у яких зустрічається слово "Дата"

        # Пошук випадку коли слова "Дата" та "народження" розташовані поруч та визначення координати по "у":
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (birth_title_y_loc - OFFSET < y < birth_title_y_loc + OFFSET):
                birth_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if birth_present:
                    birth_value = birth_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return birth_value

    def get_uni_code(self) -> Union[str, None]:
        """Пошук особистого номеру УНЗР"""
        uni_code_value = None
        uni_code_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (uni_code_title_y_loc - OFFSET < y < uni_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{13})", t)
                if value_present:
                    uni_code_value = value_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return uni_code_value

    def get_tax_code(self) -> Union[str, None]:
        """Пошук коду платника податків (РНОКПП)"""
        tax_code_value = None
        tax_code_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (tax_code_title_y_loc - OFFSET < y < tax_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{10})", t)
                if value_present:
                    tax_code_value = value_present.group(1)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    break
        return tax_code_value

    def get_phone(self) -> Union[str, None]:
        """Пошук засобу зв'язку (телефон)"""
        phone_value = None
        phone_title_y_loc = None

        # Пошук заголовку:
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
                    (phone_title_y_loc - OFFSET < y < phone_title_y_loc + OFFSET):
                t = t.replace('-', '')
                t = re.sub(r' +|\n', ' ', t)
                value_present = re.search(r"(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})", t)
                if value_present:
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
                    phone_value = value_present.group(1)
                    phone_value = phone_value[1:] if phone_value.startswith('+') else phone_value
                    phone_value = '38' + phone_value if len(phone_value) == 10 else phone_value
                    break
        return phone_value
