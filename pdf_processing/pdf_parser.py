"""
Модуль перетворення PDF до тексту за допомогою OCR
"""
import re
from typing import Tuple

import numpy as np
import cv2
import fitz

import pytesseract
from pytesseract import Output

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

pytesseract.pytesseract.tesseract_cmd = r"full path to the exe file"
pytesseract.pytesseract.tesseract_cmd = r".\tess\tesseract.exe"
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def pdfminer_to_dict(file: str) -> Tuple[dict, dict]:
    text = []
    left = []
    top = []
    width = []
    height = []
    conf = []  # rudiment from ocr method
    for page_layout in extract_pages("anketa_9576427.pdf"):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text.append(element.get_text())
                left.append(element.x0)
                top.append()

def ocr_pdf_to_dict(file: str) -> Tuple[dict, dict]:
    """
    Отримання змісту PDF у представленні словника з розпізнаними словами та їх положеннями на сторінці
    """
    image_data = _convert_pdf_to_image(file)
    return _compute_ocr(image_data)


def _compute_ocr(parsed_image: bytes, write_test_file=False) -> Tuple[dict, dict]:
    """
    Розпізнання зображення (попередньо вилученого з файлу та перетвореного у байтове представлення),
    формування словника з розпізнаним текстом та його координатами

    :returns: два словника (розпізнаний української, розпізнаний англійською)
    """
    nparr = np.fromstring(parsed_image, np.uint8)  # формування масиву зображення
    img_np = cv2.imdecode(nparr, -1)
    ocr_ukr_dict = pytesseract.image_to_data(img_np, output_type=Output.DICT, lang='ukr')
    ocr_eng_dict = pytesseract.image_to_data(img_np, output_type=Output.DICT, lang='eng')

    # Вивід у консоль, якщо треба перевірити правильність розпізнання
    if write_test_file:
        test_pattern = 'Номер|Паспорт|Дата|Прізвище|Стать|УНЗР|РНОКПП|Дійсний|Орган|Місце|народження|проживання' \
                       '|Ім.я|батькові|Телефон'

        n_boxes = len(ocr_ukr_dict['text'])
        for i in range(n_boxes):
            if int(ocr_ukr_dict['conf'][i]) > 60:
                if re.match(test_pattern, ocr_ukr_dict['text'][i]):
                    (x, y, w, h) = (ocr_ukr_dict['left'][i],
                                    ocr_ukr_dict['top'][i],
                                    ocr_ukr_dict['width'][i],
                                    ocr_ukr_dict['height'][i])
                    img_np = cv2.rectangle(img_np, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    print('Розпізнаний текст:')
                    print(f'\nТЕКСТ: {ocr_ukr_dict["text"][i]}'
                          f'\n\tПолож. X: {x}'
                          f'\n\tПолож. Y: {y}'
                          f'\n\tШирина  : {w}'
                          f'\n\tВисота  : {h}')
        # Збереження зображення з виділенням знайдених ключових слів
        cv2.imwrite('OK2.png', img_np)
    return ocr_ukr_dict, ocr_eng_dict


def _convert_pdf_to_image(file: str) -> bytes:
    """
    Читання PDF файлу, формування графічного зображення документу у байтовому представленні
    """
    # Кратність збільшення матриці майбутнього зображення (для більшої роздільної здатності:
    zoom_x = 4.0
    zoom_y = 4.0
    mat = fitz.Matrix(zoom_x, zoom_y)

    # Збереження PDF як зображення у байтовому представленні
    doc = fitz.open(file)  # open document
    pix = doc[0].get_pixmap(matrix=mat)  # render page to an image
    pix_io = pix.pil_tobytes(format="PNG", optimize=True)
    return pix_io


def get_cv_image(pdf_file):
    """
    (3368, 2382, 3)
    """
    file_io = _convert_pdf_to_image(pdf_file)
    nparr = np.fromstring(file_io, np.uint8)  # формування масиву зображення
    img_np = cv2.imdecode(nparr, -1)
    return img_np
