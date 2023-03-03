"""
Project page: github.com/OlehOleinikov/easy_DMS
License:      GNU GPL v.3
Version:      0.4-beta (patch 24.02.23)
"""
import os

from tqdm import tqdm
from rich import print as rprint
from rich.tree import Tree
from rich.console import Console
from rich.table import Table

from pdf_processing import ocr_pdf_to_dict, get_pdf_main_image
from person_builder import PersonProfile
from ms_word_editor import DocEditor
from intro import intro_ascii
from melody import melody_loop

melody = melody_loop()  # beeps
person_cards = []       # converted profiles
errors_dict = {}        # errors
string_report = ''      # finish report

# Intro:
rprint('[#FF00FF]' + 'Project page: github.com/OlehOleinikov/easy_DMS\n'
                     'License:      GNU GPL v.3\n'
                     'Version:      0.4-beta (patch 24.02.23)' + '[/#FF00FF]')
rprint(intro_ascii)
rprint('[#FF00FF]Scanning...\n')

next(melody)

# Look for PDF files:
files_in_dir = [x for x in os.listdir() if x.lower().endswith('.pdf')]
if not files_in_dir:
    rprint(f'[#FF0000]No PDF files in directory:\n{os.getcwd()}\n')
    input()
    exit()

# Print PDF files tree:
tree = Tree('[#FF00FF]' + f"{os.getcwd()}", guide_style="bold bright_blue")
for f in files_in_dir:
    tree.add('[#FF00FF]' + f)
rprint(tree)
print('\n\n')

# CONVERTING LOOP:
rprint('[#FF00FF]Converting...\n')
for file_index in tqdm(range(len(files_in_dir)), bar_format='{l_bar}{bar:45}{r_bar}{bar:-45b}'):
    cur_file = files_in_dir[file_index]
    status = False

    # Upload and OCR processing
    try:
        assert os.stat(cur_file).st_size < 1000000, "Файл заважкий, вірогідно всередині не анкета..."
        data_ukr, data_eng = ocr_pdf_to_dict(cur_file)
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка читання: {str(err)}'})
        string_report += f"[#FF0000] ERROR! [#FF00FF]file: {cur_file}\n"
        continue

    # Photo load
    try:
        person_photo = get_pdf_main_image(cur_file)
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка парсингу фото: {str(err)}'})
        person_photo = None

    # Convert data to instance
    try:
        cur_person = PersonProfile(data_ukr, data_eng, person_photo, cur_file)
        person_cards.append(cur_person)
        status = True
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка збору відомостей: {str(err)}'})

    if status:
        string_report += f"[#00FF00]   OK   [#FF00FF]file: {cur_file}\n"
    else:
        string_report += f"[#FF0000] ERROR! [#FF00FF]file: {cur_file}\n"

# Success result by files:
if person_cards:
    rprint('[#FF00FF]\n\n*****************\n**** Result ****\n*****************')
    rprint(string_report)

# Errors report - table:
if errors_dict:
    print('\n')
    table = Table(title="ERRORS LOG", width=65, style="#FF00FF")
    table.add_column("File", justify="center", style="#FF00FF", no_wrap=False)
    table.add_column("Error text", justify="center", style="#FF00FF", no_wrap=False)
    for file, error_desc in errors_dict.items():
        table.add_row(file, error_desc)
    console = Console()
    console.print(table)

# No valid data message:
if not person_cards:
    rprint(f'[#FF0000]No person data in files')
    input()
    exit(0)

# Prepare MS Word document instance:
print('\n\n')
rprint('[#FF00FF]Saving to MS Word...\n')

ms_word_file = DocEditor()
for i in (range(len(person_cards))):
    ms_word_file.add_card(person_cards[i])

# Save MS Word file:
try:
    docx_status = ms_word_file.save_docx('dms_result.docx')
    if docx_status:
        rprint('[#00FF00]MS Word saved - OK\n')
    else:
        rprint(f'[#FF0000]MS Word save error - check permission or close file in other app\n')
except Exception as err:
    rprint(f'[#FF0000]MS Word save error - check permission or close file in other app - {err}\n')

# The End pause:
next(melody)
end_word = input()

# Generate debug images (*.png with OCR mesh):
if end_word == 'plot':
    ocr_plot_log = ''
    for p_index in tqdm(range(len(person_cards)), bar_format='{l_bar}{bar:45}{r_bar}{bar:-45b}'):
        person = person_cards[p_index]
        person.save_ocr_plot()


