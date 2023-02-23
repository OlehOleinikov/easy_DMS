"""
Converter PDF to text
add text to branch
"""
import io
import re
from typing import Union

OFFSET = 10  # можлива похибка при визначенні меж боксу слова (у пікселях)
ROW_HEIGHT = (68+2)  # типова висота рядку у пікселях (для крокування)
BLANK_MIN = 355
BLANK_MAX = 635
CREATED_MIN = 923
CREATED_MAX = 1202
EXPIRED_MIN = 1490
OFFICE_TIT_X = 183
OFFICE_VAL_X = 465
PAGE_HEIGHT = 2500
PAGE_WIDTH = 1800



class DocumentId:
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

    def find_office(self, text):
        office_lines = []
        for line in text.split('\n'):
            append_status = True
            for word in self.non_office_starts:
                if line.startswith(word):
                    append_status = False
                    break
            if re.search(r'\d{2}.\d{2}.\d{4}', line):
                append_status = False
            if append_status:
                office_lines.append(line)
        if office_lines:
            office = ' '.join(office_lines)
            self.pass_office = re.sub(r'Орган видачі: ', '', office)

    def __str__(self):
        return str(self.blank_number) + " (" \
               + str(self.date_created) + " - " \
               + str(self.date_expired) + ")" \
               + str(self.pass_office)


class PersonProfile:
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

    def __init__(self, data: dict, data_eng: dict, person_photo: io.BytesIO):
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

        # PHOTO
        self.image = person_photo if person_photo else None

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
        """Пошук повного імені поблизу назв полів анкети"""
        sn_y = None  # Позиція прізвища
        fn_y = None  # Позиція ім'я
        tn_y = None  # Позиція по батькові

        sn_t = None  # Текст прізвища
        fn_t = None  # Текст імені
        tn_t = None  # Текст по батькові

        # Пошук розташування заголовків по "у":
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if sn_y is None:
                sn_y = y if re.search(r'(Прізвище)', t) else None
                self.inline_title = x if re.search(r'(Прізвище)', t) else None  # фіксується лінія заголовків по "х"
            if fn_y is None:
                fn_y = y if re.search(r'(Ім.я)', t) else None
            if tn_y is None:
                tn_y = y if re.search(r'(батькові)', t) else None

        def parse_name(expected_y_location: int, current_y: int, text: str) -> Union[str, None]:
            """Парсинг частини імені в межах дії заголовку"""
            if (expected_y_location - OFFSET) < current_y < (expected_y_location + OFFSET):
                mask_test = re.search(r"([А-ЯІЇЄ`’'\-]{2,})", text)
                if mask_test:
                    return mask_test.group(1)
            return None

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if sn_y and sn_t is None:
                test_result = parse_name(expected_y_location=sn_y, current_y=y, text=t)
                sn_t = test_result if test_result else None
                self.inline_value = x if test_result else None
            if fn_y and fn_t is None:
                test_result = parse_name(expected_y_location=fn_y, current_y=y, text=t)
                fn_t = test_result if test_result else None
            if tn_y and tn_t is None:
                test_result = parse_name(expected_y_location=tn_y, current_y=y, text=t)
                tn_t = test_result if test_result else None

        assert sn_t is not None, "Не розпізнано ПРІЗВИЩЕ"
        assert fn_t is not None, "Не розпізнано ІМ'Я"

        result_list = [x for x in [sn_t, fn_t, tn_t] if x is not None]
        result_string = ' '.join(result_list)
        return result_string

    def _get_dob(self) -> Union[str, None]:
        """Пошук дати народження"""
        birth_value = None
        birth_title_y_loc = None  # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        birth_occur = []  # Позиції у яких зустрічається слово "народження"
        date_occur = []  # Позиції у яких зустрічається слово "Дата"
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
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

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (birth_title_y_loc - OFFSET < y < birth_title_y_loc + OFFSET):
                birth_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if birth_present:
                    birth_value = birth_present.group(1)
                    break
        return birth_value

    def _get_uni_code(self) -> Union[str, None]:
        """Пошук особистого номеру УНЗР"""
        uni_code_value = None
        uni_code_title_y_loc = None
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            unicode_title_present = re.search(r'(УНЗР)', t)
            if unicode_title_present:
                uni_code_title_y_loc = y
                break

        if uni_code_title_y_loc is None:
            return None

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (uni_code_title_y_loc - OFFSET < y < uni_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{13})", t)
                if value_present:
                    uni_code_value = value_present.group(1)
                    break
        return uni_code_value

    def _get_tax_code(self) -> Union[str, None]:
        """Пошук коду платника податків (РНОКПП)"""
        tax_code_value = None
        tax_code_title_y_loc = None
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            tax_title_present = re.search(r'(РНОКПП)', t)
            if tax_title_present:
                tax_code_title_y_loc = y
                break
        if tax_code_title_y_loc is None:
            return None

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
               (tax_code_title_y_loc - OFFSET < y < tax_code_title_y_loc + OFFSET):
                value_present = re.search(r"(\d{10})", t)
                if value_present:
                    tax_code_value = value_present.group(1)
                    break
        return tax_code_value

    def _get_phone(self) -> Union[str, None]:
        """Пошук засобу зв'язку (телефон)"""
        phone_value = None
        phone_title_y_loc = None
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            phone_title_present = re.search(r'(Телефон)', t)
            if phone_title_present:
                phone_title_y_loc = y
                break
        if phone_title_y_loc is None:
            return None

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (self.inline_value - OFFSET < x < self.inline_value + OFFSET) and \
                    (phone_title_y_loc - OFFSET < y < phone_title_y_loc + OFFSET):
                value_present = re.search(r"(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})", t)
                if value_present:
                    phone_value = value_present.group(1)
                    phone_value = phone_value[1:] if phone_value.startswith('+') else phone_value
                    phone_value = '38' + phone_value if len(phone_value) == 10 else phone_value
                    break
        return phone_value

    def _get_place_birth(self):
        """Пошук місця народження"""
        birth_value = None
        birth_title_y_loc = None  # Позиція по вертикалі "y" (px) заголовка "Дата народження"
        next_section_y_loc = None
        birth_occur = []  # Позиції у яких зустрічається слово "народження"
        place_occur = []  # Позиції у яких зустрічається слово "Місце"
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
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

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (y > birth_title_y_loc) and ((self.inline_title - OFFSET) < x < (self.inline_title + OFFSET)):
                if not (str(t).startswith('Місце') | str(t).startswith('народження')):
                    next_section_y_loc = y
                    break
        if next_section_y_loc is None:
            return None

        result_list = []
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if x > (self.inline_value - OFFSET) and (birth_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET):
                result_list.append(t)
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

        # Скорочення (буд.|кв.|...) всі літери малі:
        words = re.finditer(r"[\S]*\. ", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().lower())

        # Видалення унікального номеру території
        text_line = re.sub(r"..\d{17}", '', text_line)
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
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            place_word_present = re.search(r'(Місце)', t)
            if place_word_present:
                place_occur.append(y)
            living_word_present = re.search(r'(проживання)', t)
            if living_word_present:
                living_occur.append(y)
        for p in place_occur:
            if not adr_title_y_loc:
                for liv in living_occur:
                    if abs(p-liv) <= ROW_HEIGHT + OFFSET:  # Місце, де слова "Місце" та "проживання" - поруч
                        adr_title_y_loc = liv if liv <= p else p  # Розташування визначається за вищим словом (Місце)

        # Якщо не знайдено заголовок - припинення пошуку:
        if not adr_title_y_loc:
            return None

        # Пошук початку наступної секції (для обмеження пошуку поточної адреси) - заголовок з відступом inline_title:
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (y > adr_title_y_loc) and ((self.inline_title - OFFSET) < x < (self.inline_title + OFFSET)):
                t = str(t)
                if not (t.startswith('Місце') | t.startswith('проживання') | t.startswith('перебування') | (t == '')):
                    next_section_y_loc = y
                    break
        if next_section_y_loc is None:
            return None

        # Накопичення слів у ділянці документу (визначена попередньо)
        result_list = []
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if x > (self.inline_value - OFFSET) and (adr_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET):
                result_list.append(t)
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
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
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
            for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
                if y > (section_starts + ROW_HEIGHT + OFFSET):
                    end_present = re.search(r'(Свідоцтво|Паспорт|Запит)', t)
                    if end_present:
                        section_ends = y
                        break

        # Неочікуваний випадок, якщо початок блоку визначений пізніше ніж закінчення:
        if section_starts > section_ends:
            return None, None

        # Повернення результатів опрацювання:
        if section_starts and section_ends:
            return section_starts, section_ends
        else:
            return None, None

    def _get_blanks_ranges(self, section_start: int, section_end: int) -> Union[list, None]:
        """Формування списку пар координат по осі у - межі запису окремого паспорту"""
        kw_present = []  # координати по "у" у яких зустрічається слово номер
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (section_start - OFFSET) < y < (section_end + OFFSET):
                if str(t).startswith('Номер'):
                    kw_present.append(y)
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
        """Створення інстансу ДокументІД"""
        assert lang in ['ukr', 'eng']

        blank = None
        date_created = None
        date_expired = None
        expired_status = None
        office = None
        office_lines = []
        office_y = None

        if lang is 'eng':
            for i, (x, y, t) in enumerate(zip(self.data_eng['left'], self.data_eng['top'], self.data_eng['text'])):
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ]{0,4}[\d]{6}$)", t)
                    if blank_present:
                        blank = blank_present.group(1)
                        break

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if lang is 'ukr':
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ]{0,4}[\d]{6}$)", t)
                    if blank_present:
                        blank = blank_present.group(1)

            if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((CREATED_MIN - OFFSET) < x < (CREATED_MAX + OFFSET)):
                created_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if created_present:
                    date_created = created_present.group(1)

            if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((EXPIRED_MIN - OFFSET) < x):
                expired_present = re.search(r"(\d{2}.\d{2}.\d{4})", t)
                if expired_present:
                    date_expired = expired_present.group(1)

                spec_status = re.search(r"(недійсним)|(необмежений)", t)
                if spec_status:
                    if spec_status.group(0) == 'недійсним':
                        expired_status = 'недійсний'
                    elif spec_status.group(0) == 'необмежений':
                        expired_status = 'необмежений'

            if ((y_min - OFFSET) < y < (y_max - OFFSET)) and ((OFFICE_TIT_X - OFFSET) < x < (OFFICE_TIT_X + OFFSET)):
                office_title_present = re.search(r"(Орган)", t)
                if office_title_present:
                    office_y = y

        if office_y:
            for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
                if ((office_y - OFFSET) < y < (y_max - OFFSET)) and ((OFFICE_VAL_X - OFFSET) < x):
                    office_lines.append(t)
        if office_lines:
            office_string = ' '.join(office_lines)
            office_string = office_string.strip()
            office_string = re.sub(r' +|\n', ' ', office_string)
            office = office_string

        if blank:
            return DocumentId(blank, date_created, date_expired, expired_status, office)

    def _get_cert_birth(self):
        section_starts, section_ends = self._get_document_section_range('Свідоцтво', "Паспорт")
        if not section_starts:
            return None
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                self.certificate_of_birth.append(passport)

    def _get_pass_int(self):
        section_starts, section_ends = self._get_document_section_range(r'Паспорт', r"Паспорт\(и\)")
        if not section_starts:
            return None
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                self.pass_internal.append(passport)

    def _get_pass_ext(self):
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
