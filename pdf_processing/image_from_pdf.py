"""
Отримання байтового представлення першого зображення PDF документу.
"""
import fitz
import io


def get_pdf_main_image(file_name) -> io.BytesIO:
    """
    Отримання першого зображення PDF документу у байтовому представленні (RGB)
    """
    file_path = file_name
    pdf_file = fitz.open(file_path)

    # кількість сторінок у файлі
    number_of_pages = len(pdf_file)
    # проходження по кожній сторінці pdf
    for current_page_index in range(number_of_pages):
        # проходження по кожній сторінці
        for img_index,img in enumerate(pdf_file.get_page_images(current_page_index)):
            xref = img[0]
            image = fitz.Pixmap(pdf_file, xref)
            # для зображень з кольоровою схемою GRAY та RGB
            if image.n < 5:
                stream = image.pil_tobytes(format='PNG')
                memory_file = io.BytesIO(stream)
                return memory_file
            # для кольорової схеми  CMYK: перетворення на  RGB
            else:
                new_image = fitz.Pixmap(fitz.csRGB, image)
                memory_file = io.BytesIO()
                new_image.pil_tobytes(memory_file)
                return memory_file