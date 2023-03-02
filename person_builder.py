"""
Модуль формування екземплярів профайлів зі словника розпізнаного тексту
"""
import io
from typing import Union

from cls_handler_personal import HandlerMainData
from cls_handler_places import HandlerPlaces
from cls_handler_documents import HandlerDocuments

from pdf_processing import get_cv_image
from defines import *
from draw_funcs import *


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
        # Списки накопичення інстансів DocumentId:
        self.certificate_of_birth = []  # Свідоцтво про народження
        self.pass_internal = []  # Паспорт (внутрішній)
        self.pass_external = []  # Паспорт (закордонний)

        self.pic = get_cv_image(origin_file)  # опрацьоване зображення
        self.image = person_photo if person_photo else None  # фото з анкети
        self._data_ukr_voc = data  # результати OCR українською мовою (словник)
        self._data_eng_voc = data_eng  # результати OCR англійською мовою (словник)
        self.inline_title = None  # відступ від лівого краю з заголовками полів
        self.inline_value = PERS_VALS_LOC  # відступ від лівого краю зі значеннями (основні анкетні дані)

        # результати OCR українською мовою (словник):
        self.words = data.get('text', [])  # розпізнаний текст (слово)
        self.pos_x = data.get('left', [])  # ліва межа боксу слова
        self.pos_y = data.get('top', [])  # верхня межа боксу слова
        self.width = data.get('width', [])  # ширина боксу
        self.heigh = data.get('height', [])  # висота боксу
        self.conf = data.get('conf', [])
        self._zipped_data = list(zip(self.pos_x, self.pos_y, self.words, self.heigh, self.width, self.conf))

        # результати OCR англійською мовою (словник):
        self.words_e = data_eng.get('text', [])
        self.pos_x_e = data_eng.get('left', [])
        self.pos_y_e = data_eng.get('top', [])
        self.width_e = data_eng.get('width', [])
        self.heigh_e = data_eng.get('height', [])
        self.conf_e = data_eng.get('conf', [])
        self._zipped_data_eng = list(zip(self.pos_x_e, self.pos_y_e, self.words_e, self.heigh_e, self.width_e, self.conf_e))

        # І. ОСНОВНІ ПОЛЯ
        handler_main = HandlerMainData(linked_person=self)
        # Ім'я (в якості валідації)
        s_name, f_name, t_name = handler_main.get_names()
        assert s_name is not None, "Не розпізнано прізвище"
        assert f_name is not None, "Не розпізнано ім'я"
        names_list = [x for x in [s_name, f_name, t_name] if x is not None]
        self.name_full = ' '.join(names_list)
        # Заповнення основних анкетних даних:
        self.dob = handler_main.get_dob()
        self.code_uni = handler_main.get_uni_code()
        self.code_tax = handler_main.get_tax_code()
        self.phone = handler_main.get_phone()

        # ІІ. АДРЕСИ
        handler_addr = HandlerPlaces(linked_person=self)
        self.pob = handler_addr.get_place_birth()
        self.address = handler_addr.get_place_live()

        # ІІІ. ДОКУМЕНТИ
        handler_docs = HandlerDocuments(linked_person=self)
        self.certificate_of_birth = handler_docs.get_cert_birth()
        self.pass_internal = handler_docs.get_pass_int()
        self.pass_external = handler_docs.get_pass_ext()

    @property
    def data_ukr(self):
        return self._zipped_data
    
    @property
    def data_eng(self):
        return self._zipped_data_eng

    def save_ocr_plot(self):
        """Збереження файлу зображення з відміченими словами (які включені у профайл) та заголовками"""
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
