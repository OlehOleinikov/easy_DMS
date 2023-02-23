import warnings
import io
import re
from rich import print as rprint
from typing import Tuple

import numpy as np
import cv2
import fitz

from pdfminer.converter import PDFPageAggregator, TextConverter
from pdfminer.layout import LTTextBox, LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

import pytesseract
from pytesseract import Output

pytesseract.pytesseract.tesseract_cmd = r"full path to the exe file"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


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


def get_text_data(file) -> str:
    """
    Отримання даних PDF файлу у вигляді стрінги з розділювачами нового рядку
    (очищення від 1-2 символьних рідків) DeprecationWarning
    """
    warnings.warn("Через замішування тексту всередині блоків методи process_page() не будуть використовуватись. "
                  "Все опрацювання замінено на OCR", DeprecationWarning)
    output_string = io.StringIO()
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


def show_pdf_text_localization(file):
    """
    Збір текстових записів з PDF та відображення розмірів блоків (положення на сторінці).
    Для відображення у консоль якості вилучення тексту з PDF. DeprecationWarning
    """
    warnings.warn("Через замішування тексту всередині блоків методи process_page() не будуть використовуватись. "
                  "Все опрацювання замінено на OCR", DeprecationWarning)
    fp = open(file, 'rb')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    pages = PDFPage.get_pages(fp)

    for page in pages:
        interpreter.process_page(page)
        layout = device.get_result()
        for l in layout:
            if isinstance(l, LTTextBox):
                x_min, y_max, y_min, x_max, text = l.bbox[0], l.bbox[3], l.bbox[1], l.bbox[2],  l.get_text()
                if len(text) > 2:

                    res_text = []
                    for part in text.split('\n'):
                        if len(part) > 2:
                            res_text.append(part)
                    res_text = '\n'.join(res_text)

                    if res_text:
                        print('--------------------------------------------')
                        print(f'height: {round(y_min)}-{round(y_max)} (size: {round(abs(y_min - y_max))})')
                        print(f'width:  {round(x_min)}-{round(x_max)} (size: {round(abs(x_min - x_max))})')
                        rprint('[red]' + res_text + '[/red]')