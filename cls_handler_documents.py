import re
from typing import List, Union, Tuple

from cls_document import DocumentId

from defines import *
from draw_funcs import *


class HandlerDocuments:
    def __init__(self, linked_person):
        self.data_ukr = linked_person.data_ukr
        self.data_eng = linked_person.data_eng
        self.pic = linked_person.pic

    def get_cert_birth(self) -> List[DocumentId]:
        """Накопичення та валідація всіх записів свідоцтв"""
        certificate_of_birth = []
        section_starts, section_ends = self._get_document_section_range('Свідоцтво', "Паспорт")
        if not section_starts:
            return certificate_of_birth
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                certificate_of_birth.append(passport)
        return certificate_of_birth

    def get_pass_int(self) -> List[DocumentId]:
        """Накопичення та валідація всіх записів паспортів (внутрішніх)"""
        section_starts, section_ends = self._get_document_section_range(r'Паспорт', r"Паспорт\(и\)")
        pass_internal = []
        if not section_starts:
            return pass_internal
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1])
            if passport:
                pass_internal.append(passport)
        return pass_internal

    def get_pass_ext(self) -> List[DocumentId]:
        """Накопичення та валідація всіх записів паспортів (закордонних)"""
        pass_external = []
        section_starts, section_ends = self._get_document_section_range(r"Паспорт\(и\)", r"Запит")
        if not section_starts:
            return pass_external
        blanks_ranges = self._get_blanks_ranges(section_starts, section_ends)
        for b in blanks_ranges:
            passport = self._create_pass(b[0], b[1], lang='eng')
            if passport:
                pass_external.append(passport)
        return pass_external

    def _get_document_section_range(self, start_word: str, end_word: str) -> Union[Tuple[int, int], Tuple[None, None]]:
        """
        Визначення меж секції (від одного ключого слова до іншого).
        Якщо визначене у аргументах друге слово відсутнє - спроба пошуку типових для заголовків блоків

        :returns: координати у пікселях по вертикалі (входження першого слова, входження другого)
        """
        section_starts = None
        section_ends = None

        # Прохід по всім словам та координатам для пошуку входжень ключових слів
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
            for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
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

    @staticmethod
    def __clear_pass_blank(text):
        # Виправлення OCR артефактів, формування літерної серії паспортів:
        text = re.sub(r"O", '0', text)
        text = re.sub(r"б", '6', text)
        wrong_zero = re.match(
            r'^[А-ЯA-Z](0)[\d]{6}|^(0)[А-ЯA-Z][\d]{6}|^\d-[А-ЯA-Z](0)[\d]{6}|^\d-(0)[А-ЯA-Z][\d]{6}', text)
        if wrong_zero and text:
            t_char_list = list(text)
            zero_pos = wrong_zero.start(1)
            t_char_list[zero_pos] = 'О'
            text = ''.join(t_char_list)
        return text

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
            for i, (x, y, t, h, w, c) in enumerate(self.data_eng):
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    t = re.sub(r"O", '0', t)
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ\-]{7,10}$)", t)
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
        for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
            if lang == 'ukr':
                if ((y_min - OFFSET) < y < (y_min + OFFSET)) and ((BLANK_MIN - OFFSET) < x < (BLANK_MAX + OFFSET)):
                    # Виправлення OCR артефактів:
                    t = self.__clear_pass_blank(t)
                    blank_present = re.search(r"([A-ZА-Я0-9ІЇЄ\-]{7,11}$)", t)
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
            for i, (x, y, t, h, w, c) in enumerate(self.data_ukr):
                if ((office_y - OFFSET) < y < (y_max - OFFSET)) and ((OFFICE_VAL_X - OFFSET) < x):
                    office_lines.append(t)
                    self.pic = d_elem(self.pic, x, y, h, w, C_G, desc=f'({x};{y})')
        if office_lines:
            office_string = ' '.join(office_lines)
            office_string = office_string.strip()
            office_string = re.sub(r' +|\n', ' ', office_string)
            office_string = re.sub(r' Мо ', ' №', office_string)
            office = office_string

        # Створити екземпляр, якщо є хоча б номер бланку документу:
        if blank:
            return DocumentId(blank, date_created, date_expired, expired_status, office)
        else:
            return None
