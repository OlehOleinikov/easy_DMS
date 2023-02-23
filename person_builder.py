"""
Converter PDF to text
add text to branch
"""
import io
import re
from typing import Union

OFFSET = 10  # можлива похибка при визначенні меж боксу слова (у пікселях)
ROW_HEIGHT = (68+2)  # типова висота рядку у пікселях (для крокування)


class DocumentId:
    blank_number = None
    date_created = None
    date_expired = None
    pass_office = None
    expired_status = None
    non_office_starts = ['Номер', 'Дата', 'Дійсний', 'необмежений', 'Документ', 'Паспорт(и)']

    def __init__(self, text: str):
        self.find_blank(text)
        self.find_dates(text)
        self.find_office(text)
        assert self.blank_number is not None

    def find_blank(self, text):
        blank_search = re.search(r"Номер ([\S]*)\n", text)
        if not blank_search:
            blank_search = re.search(r"\n(\S{2}\d{6})\n", text)
        self.blank_number = blank_search.group(1) if blank_search else None

    def find_dates(self, text):
        date_occur = re.finditer(r"\d{2}.\d{2}.\d{4}", text)
        dates_list = []
        for cur_date in date_occur:
            dates_list.append(cur_date.group())
        if len(dates_list) == 1:
            self.date_created = dates_list[0]

        if len(dates_list) > 1:
            dates_list = sorted(dates_list, key=lambda date_text: date_text[-4:])
            self.date_created = dates_list[0]
            self.date_expired = dates_list[1]

        spec_status = re.search(r"Документ визнано недійсним|необмежений", text)
        self.expired_status = spec_status.group(0) if spec_status else None

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

    def __init__(self, data: dict, person_photo: io.BytesIO):
        self.data = data
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




        # splitted_lines_pdf = data.split('\n')
        # cleaned_strings = [str(x).strip() for x in splitted_lines_pdf if len(x.strip()) > 2]
        # data = '\n'.join(cleaned_strings)
        #
        # # assert re.match('ОСОБОВА КАРТКА', data) is not None, 'Відсутній заголовок "ОСОБОВА КАРТКА", ' \
        # #                                                      'можливо файл не являється карткою ДМС'
        #
        # # ПРІЗВИЩЕ ІМ'Я ПОБАТЬКОВІ:
        # regex_half_name = r"Державна міграційна служба України\n([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,})"
        # regex_full_name = r"([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,}\n)|" \
        #                   r"Прізвище\n([А-ЯІЇЄ`’']{2,})\nІм.я\n([А-ЯІЇЄ`’']{2,})\nПо батькові\n([А-ЯІЇЄ`’']{2,})\n|" \
        #                   r"([А-ЯІЇЄ`’']{2,})\nПр.звище\n([А-ЯІЇЄ`’']{2,})\n.м.я\nПо батькові\n([А-ЯІЇЄ`’']{2,})"
        # name_search = re.search(regex_full_name, data)
        # if not name_search:
        #     name_search = re.search(regex_half_name, data)
        # if not name_search:
        #     raise ImportError('Не виявлено співпадінь маски ПІБ')
        # name_lines = [x for x in name_search.groups() if x is not None]
        # name_full_str = ' '.join(name_lines)
        # self.name_full = re.sub(r' +|\n', ' ', name_full_str)
        #
        # # ДАТА НАРОДЖЕННЯ:
        # dob_res = re.search(r'Дата народження[\s:-]{0,2}(\d{2}.\d{2}.\d{4})', data)
        # self.dob = dob_res.group(1) if dob_res else self.dob
        # assert self.dob is not None, "Не виявлено дату народження"
        #
        # # УНЗР
        # uni_res = re.search(r'\n(\d{13})\n', data)
        # self.code_uni = uni_res.group(1) if uni_res else self.code_uni
        #
        # # РНОКПП
        # tax_res = re.search(r'\n(\d{10})\n', data)
        # self.code_tax = tax_res.group(1) if tax_res else self.code_tax
        #
        # # МІСЦЕ НАРОДЖЕННЯ / АДРЕСА
        # places_res = re.search(r"перебування\n([\s\S]*)UA\d{17}", data)
        # if not places_res:
        #     places_res = re.search(r"перебування\n([\s\S] * )Паспорт\n", data)
        #
        # if places_res:
        #     places_str = places_res.group(1)
        #     live_from = re.search(r"\d{8}$", places_str)
        #     if live_from:
        #         lf = live_from.group(0)
        #         self.live_from = lf[:2] + '.' + lf[2:5] + '.' + lf[-4:]
        #     locations = []
        #     for p in places_str.split('УКРАЇНА'):
        #         pure_search = re.search(r"(\w[\s\S]*\w)", p)
        #         if pure_search:
        #             cur_location = pure_search.group(1)
        #             words = re.finditer(r"[\S]*", cur_location)
        #             if words:
        #                 for w in words:
        #                     cur_location = cur_location.replace(w.group(), w.group().title())
        #                     cur_location = cur_location.replace("\n", ' ')
        #                     for adr_type in self.address_types:
        #                         cur_location = cur_location.replace(adr_type, adr_type.lower())
        #
        #             words = re.finditer(r"[\S]*\. ", cur_location)
        #             if words:
        #                 for w in words:
        #                     cur_location = cur_location.replace(w.group(), w.group().lower())
        #                     cur_location = cur_location.replace("\n", ' ')
        #                     for adr_type in self.address_types:
        #                         cur_location = cur_location.replace(adr_type, adr_type.lower())
        #
        #             locations.append(cur_location)
        #     if locations:
        #         self.address = locations[-1]
        #         self.address = re.sub(r" \d{8}$", '', self.address)
        #         self.pob = locations[0]
        #
        # # ТЕЛЕФОН
        # phone_res = re.search(r"\n(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})\n", data)
        # if phone_res:
        #     phone = phone_res.group(1)
        #     phone = phone[1:] if phone.startswith('+') else phone
        #     phone = '38' + phone if len(phone) == 10 else phone
        #     self.phone = phone
        #
        # # PASS INTERNAL:
        # pass_int = re.search(r"Паспорт громадянина України\n([.\s\S]*)Свідоцтво про народження", data)
        # if not pass_int:
        #     pass_int = re.search(r"Паспорт громадянина України\n([.\s\S]*)Паспорт\(и\) громадянина "
        #                          r"України для виїзду за кордон", data)
        # # додати \n(\S{2}\d{6})\n для старого формату
        # if pass_int:
        #     text_int = pass_int.group(1)
        #     res_search = re.finditer('Номер', text_int)
        #     starts_list_occur = []
        #     for match in res_search:
        #         starts_list_occur.append(match.start())
        #     if starts_list_occur:
        #         starts_list_occur.append(len(text_int))
        #     pass_ranges = []
        #     for el_num in range(len(starts_list_occur)):
        #         cur_el = starts_list_occur[el_num]
        #         if not cur_el == starts_list_occur[-1]:
        #             pass_ranges.append([cur_el, starts_list_occur[el_num + 1]])
        #     for pass_range in pass_ranges:
        #         try:
        #             pass_inst = DocumentId(text_int[pass_range[0]: pass_range[1]])
        #             if type(pass_inst) == DocumentId:
        #                 self.pass_internal.append(pass_inst)
        #         except Exception:
        #             pass
        #
        # # PASS EXTERNAL:
        # pass_ext = re.search(r"Паспорт\(и\) громадянина України для виїзду за кордон\n([.\s\S]*)Запит здійснив", data)
        # if pass_ext:
        #     text_ext = pass_ext.group(1)
        #     res_search = re.finditer('Номер', text_ext)
        #     starts_list_occur = []
        #     for match in res_search:
        #         starts_list_occur.append(match.start())
        #     if starts_list_occur:
        #         starts_list_occur.append(len(text_ext))
        #     pass_ranges = []
        #     for el_num in range(len(starts_list_occur)):
        #         cur_el = starts_list_occur[el_num]
        #         if not cur_el == starts_list_occur[-1]:
        #             pass_ranges.append([cur_el, starts_list_occur[el_num + 1]])
        #     for pass_range in pass_ranges:
        #         try:
        #             pass_inst = DocumentId(text_ext[pass_range[0]: pass_range[1]])
        #             if type(pass_inst) == DocumentId:
        #                 self.pass_external.append(pass_inst)
        #         except Exception:
        #             pass

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
        words = re.finditer(r"([\S`’']{2,})| ([\S`’']{2,})", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().title())
                text_line = text_line.replace("\n", ' ')
                for adr_type in address_types:
                    text_line = text_line.replace(adr_type, adr_type.lower())

        words = re.finditer(r"[ ]([А-Я]{1}[а-я]{1,}[А-Я]{1,})[ ,]", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().title())
                text_line = text_line.replace("\n", ' ')
                for adr_type in address_types:
                    text_line = text_line.replace(adr_type, adr_type.lower())

        words = re.finditer(r"[\S]*\. ", text_line)
        if words:
            for w in words:
                text_line = text_line.replace(w.group(), w.group().lower())
        text_line = re.sub(r"..\d{17}", '', text_line)
        text_line = text_line.strip()
        text_line = re.sub(r"\d{8}", '', text_line)
        text_line = text_line.strip()
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

        if not adr_title_y_loc:
            return None

        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if (y > adr_title_y_loc) and ((self.inline_title - OFFSET) < x < (self.inline_title + OFFSET)):
                t = str(t)
                if not (t.startswith('Місце') | t.startswith('проживання') | t.startswith('перебування') | (t == '')):
                    next_section_y_loc = y
                    break
        if next_section_y_loc is None:
            return None

        result_list = []
        for i, (x, y, t) in enumerate(zip(self.data['left'], self.data['top'], self.data['text'])):
            if x > (self.inline_value - OFFSET) and (adr_title_y_loc - OFFSET) < y < (next_section_y_loc - OFFSET):
                result_list.append(t)
        if result_list:
            result_string = ' '.join(result_list)
            adr_value = self._clear_adr_line(result_string)
        return adr_value

    def _get_cert_birth(self):
        ...

    def _get_pass_int(self):
        ...

    def _get_pass_ext(self):
        ...

    def _doc_in_range(self, lim_min: int, lim_max: int):
        ...

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
