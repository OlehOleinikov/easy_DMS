import fitz
import io


def get_image(file_name):
    file_path = file_name
    pdf_file = fitz.open(file_path)

    #finding number of pages in the pdf
    number_of_pages = len(pdf_file)

    #iterating through each page in the pdf
    for current_page_index in range(number_of_pages):
        #iterating through each image in every page of PDF
        for img_index,img in enumerate(pdf_file.get_page_images(current_page_index)):
            xref = img[0]
            image = fitz.Pixmap(pdf_file, xref)
            #if it is a is GRAY or RGB image
            if image.n < 5:
                stream = image.pil_tobytes(format='PNG')
                memory_file = io.BytesIO(stream)
                return memory_file
            #if it is CMYK: convert to RGB first
            else:
                new_image = fitz.Pixmap(fitz.csRGB, image)
                memory_file = io.BytesIO()
                new_image.pil_tobytes(memory_file)
                return memory_file