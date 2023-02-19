from io import StringIO
import re

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from image_from_pdf import get_image


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
            spec_status = re.search(r"Документ визнано недійсним|необмежений", text)
            self.expired_status = spec_status.group(0) if spec_status else None

        if len(dates_list) > 1:
            dates_list = sorted(dates_list, key=lambda date_text: date_text[-4:])
            self.date_created = dates_list[0]
            self.date_expired = dates_list[1]

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

    def __init__(self, data: str, file_name):
        self.file_name = file_name
        self.pass_internal = []
        self.pass_external = []
        splitted_lines_pdf = data.split('\n')
        cleaned_strings = [str(x).strip() for x in splitted_lines_pdf if len(x.strip()) > 2]
        data = '\n'.join(cleaned_strings)

        # assert re.match('ОСОБОВА КАРТКА', data) is not None, 'Відсутній заголовок "ОСОБОВА КАРТКА", ' \
        #                                                      'можливо файл не являється карткою ДМС'

        # ПРІЗВИЩЕ ІМ'Я ПОБАТЬКОВІ:
        regex_half_name = r"Державна міграційна служба України\n([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,})"
        regex_full_name = r"([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,})\n([А-ЯІЇЄ`’']{2,}\n)|" \
                          r"Прізвище\n([А-ЯІЇЄ`’']{2,})\nІм.я\n([А-ЯІЇЄ`’']{2,})\nПо батькові\n([А-ЯІЇЄ`’']{2,})\n|" \
                          r"([А-ЯІЇЄ`’']{2,})\nПр.звище\n([А-ЯІЇЄ`’']{2,})\n.м.я\nПо батькові\n([А-ЯІЇЄ`’']{2,})"
        name_search = re.search(regex_full_name, data)
        if not name_search:
            name_search = re.search(regex_half_name, data)
        if not name_search:
            raise ImportError('Не виявлено співпадінь маски ПІБ')
        name_lines = [x for x in name_search.groups() if x is not None]
        name_full_str = ' '.join(name_lines)
        self.name_full = re.sub(r' +|\n', ' ', name_full_str)

        # ДАТА НАРОДЖЕННЯ:
        dob_res = re.search(r'Дата народження[\s:-]{0,2}(\d{2}.\d{2}.\d{4})', data)
        self.dob = dob_res.group(1) if dob_res else self.dob
        assert self.dob is not None, "Не виявлено дату народження"

        # УНЗР
        uni_res = re.search(r'\n(\d{13})\n', data)
        self.code_uni = uni_res.group(1) if uni_res else self.code_uni

        # РНОКПП
        tax_res = re.search(r'\n(\d{10})\n', data)
        self.code_tax = tax_res.group(1) if tax_res else self.code_tax

        # МІСЦЕ НАРОДЖЕННЯ / АДРЕСА
        places_res = re.search(r"перебування\n([\s\S]*)UA\d{17}", data)
        if not places_res:
            places_res = re.search(r"перебування\n([\s\S] * )Паспорт\n", data)

        if places_res:
            places_str = places_res.group(1)
            live_from = re.search(r"\d{8}$", places_str)
            if live_from:
                lf = live_from.group(0)
                self.live_from = lf[:2] + '.' + lf[2:5] + '.' + lf[-4:]
            locations = []
            for p in places_str.split('УКРАЇНА'):
                pure_search = re.search(r"(\w[\s\S]*\w)", p)
                if pure_search:
                    cur_location = pure_search.group(1)
                    words = re.finditer(r"[\S]*", cur_location)
                    if words:
                        for w in words:
                            cur_location = cur_location.replace(w.group(), w.group().title())
                            cur_location = cur_location.replace("\n", ' ')
                            for adr_type in self.address_types:
                                cur_location = cur_location.replace(adr_type, adr_type.lower())

                    words = re.finditer(r"[\S]*\. ", cur_location)
                    if words:
                        for w in words:
                            cur_location = cur_location.replace(w.group(), w.group().lower())
                            cur_location = cur_location.replace("\n", ' ')
                            for adr_type in self.address_types:
                                cur_location = cur_location.replace(adr_type, adr_type.lower())

                    locations.append(cur_location)
            if locations:
                self.address = locations[-1]
                self.address = re.sub(r" \d{8}$", '', self.address)
                self.pob = locations[0]

        # ТЕЛЕФОН
        phone_res = re.search(r"\n(0\d{9}|\+38\d{10}|38\d{10}|8\d{10})\n", data)
        if phone_res:
            phone = phone_res.group(1)
            phone = phone[1:] if phone.startswith('+') else phone
            phone = '38' + phone if len(phone) == 10 else phone
            self.phone = phone

        # PASS INTERNAL:
        pass_int = re.search(r"Паспорт громадянина України\n([.\s\S]*)Паспорт\(и\) громадянина "
                             r"України для виїзду за кордон", data)
        # додати \n(\S{2}\d{6})\n для старого формату
        if pass_int:
            text_int = pass_int.group(1)
            res_search = re.finditer('Номер', text_int)
            starts_list_occur = []
            for match in res_search:
                starts_list_occur.append(match.start())
            if starts_list_occur:
                starts_list_occur.append(len(text_int))
            pass_ranges = []
            for el_num in range(len(starts_list_occur)):
                cur_el = starts_list_occur[el_num]
                if not cur_el == starts_list_occur[-1]:
                    pass_ranges.append([cur_el, starts_list_occur[el_num + 1]])
            for pass_range in pass_ranges:
                try:
                    pass_inst = DocumentId(text_int[pass_range[0]: pass_range[1]])
                    if type(pass_inst) == DocumentId:
                        self.pass_internal.append(pass_inst)
                except Exception:
                    pass

        # PASS EXTERNAL:
        pass_ext = re.search(r"Паспорт\(и\) громадянина України для виїзду за кордон\n([.\s\S]*)Запит здійснив", data)
        if pass_ext:
            text_ext = pass_ext.group(1)
            res_search = re.finditer('Номер', text_ext)
            starts_list_occur = []
            for match in res_search:
                starts_list_occur.append(match.start())
            if starts_list_occur:
                starts_list_occur.append(len(text_ext))
            pass_ranges = []
            for el_num in range(len(starts_list_occur)):
                cur_el = starts_list_occur[el_num]
                if not cur_el == starts_list_occur[-1]:
                    pass_ranges.append([cur_el, starts_list_occur[el_num + 1]])
            for pass_range in pass_ranges:
                try:
                    pass_inst = DocumentId(text_ext[pass_range[0]: pass_range[1]])
                    if type(pass_inst) == DocumentId:
                        self.pass_external.append(pass_inst)
                except Exception:
                    pass

        # PHOTO
        try:
            self.image = get_image(self.file_name)
        except Exception:
            self.image = None


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


def get_pdf_data(file) -> str:
    """Отримання даних ПДФ файлу у вигляді стрінги з розділювачами нового рядку (очищення від 1-2 символьних рідків)"""
    output_string = StringIO()
    with open(file, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)

    pdf_text = output_string.getvalue()
    splitted_lines_pdf = pdf_text.split('\n')
    clean_string = [str(x).strip() for x in splitted_lines_pdf if len(x.strip()) > 2]
    data = '\n'.join(clean_string)
    # with open(f"Output_{file}.txt", "w") as text_file:
    #     text_file.write(data)
    return data
