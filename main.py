import os

from rich import print as rprint
from rich.tree import Tree
from rich.console import Console
from rich.table import Table

from pdf_processing import ocr_pdf_to_dict, get_pdf_main_image
from person_builder import PersonProfile
from ms_word_editor import DocEditor
from intro import intro_ascii
from melody import melody_loop

import pickle

DEBUG_MODE = True  # some reports for developing purposes

melody = melody_loop()
person_cards = []
errors_dict = {}

# INTRO PART:
rprint('[#FF00FF]' + 'Project page: github.com/OlehOleinikov/easy_DMS\nLicense:      GNU GPL v.3' + '[/#FF00FF]')
rprint(intro_ascii)
rprint('[#FF00FF]Scanning...\n')

next(melody)

# LOOK FOR PDF FILES:
files_in_dir = [x for x in os.listdir() if x.lower().endswith('.pdf')]
if not files_in_dir:
    rprint(f'[#FF0000]No PDF files in directory:\n{os.getcwd()}\n')
    input()
    exit()

# PRINT PDF FILES TREE:
tree = Tree('[#FF00FF]' + f"{os.getcwd()}", guide_style="bold bright_blue")
for f in files_in_dir:
    tree.add('[#FF00FF]' + f)
rprint(tree)
print('\n\n')

# CONVERTING LOOP:
rprint('[#FF00FF]Converting...\n')
for cur_file in files_in_dir:
    status = False

    try:
        assert os.stat(cur_file).st_size < 1000000, "Файл заважкий, вірогідно всередині не анкета..."
        data_ukr, data_eng = ocr_pdf_to_dict(cur_file)
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка читання: {str(err)}'})
        continue

    try:
        person_photo = get_pdf_main_image(cur_file)
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка парсингу фото: {str(err)}'})
        person_photo = None

    try:
        cur_person = PersonProfile(data_ukr, data_eng, person_photo)
        person_cards.append(cur_person)
        status = True
    except Exception as err:
        errors_dict.update({cur_file: f'Помилка збору відомостей: {str(err)}'})

    if status:
        rprint("[#00FF00]   OK   [#FF00FF]file: %s" % cur_file)
    else:
        rprint("[#FF0000] ERROR! [#FF00FF]file: %s" % cur_file)

if errors_dict:
    print('\n')
    table = Table(title="ERRORS LOG", width=65, style="#FF00FF")
    table.add_column("File", justify="center", style="#FF00FF", no_wrap=False)
    table.add_column("Error text", justify="center", style="#FF00FF", no_wrap=False)
    for file, error_desc in errors_dict.items():
        table.add_row(file, error_desc)
    console = Console()
    console.print(table)

if not person_cards:
    rprint(f'[#FF0000]No person data in files')
    input()
    exit(0)

print('\n\n')
rprint('[#FF00FF]Saving to MS Word...\n')

ms_word_file = DocEditor()
for i in (range(len(person_cards))):
    ms_word_file.add_card(person_cards[i])

try:
    ms_word_file.save_docx('dms_result.docx')
    rprint('[#00FF00]MS Word saved - OK\n')
except Exception:
    rprint('[#FF0000]MS Word save error - check permission or close file in other app\n')

next(melody)
input()
