import os

from rich import print as rprint
from rich.tree import Tree
from rich.console import Console
from rich.table import Table

from converter_pdf import PersonProfile, get_pdf_data, show_pdf_text_localization
from ms_word_editor import DocEditor
from defines import melody_run, intro_ascii

DEBUG_MODE = True

melody = melody_run()
person_cards = []
errors_dict = {}

rprint('[#FF00FF]' + 'Project page: github.com/OlehOleinikov/easy_DMS\nLicense:      GNU GPL v.3' + '[/#FF00FF]')
rprint(intro_ascii)
rprint('[#FF00FF]Scaning...\n')

next(melody)

files_in_dir = [x for x in os.listdir() if x.lower().endswith('.pdf')]
if not files_in_dir:
    rprint(f'[#FF0000]No PDF files in directory:\n{os.getcwd()}\n')
    input()
    exit()

tree = Tree('[#FF00FF]' + f"{os.getcwd()}", guide_style="bold bright_blue")
for f in files_in_dir:
    tree.add('[#FF00FF]' + f)
rprint(tree)

print('\n\n')
rprint('[#FF00FF]Converting...\n')

for idx, name in enumerate(files_in_dir):
    status = False
    try:
        if DEBUG_MODE:
            show_pdf_text_localization(name)

        data = get_pdf_data(name)
        cur_person = PersonProfile(data, name)
        person_cards.append(cur_person)
        status = True
    except Exception as err:
        errors_dict.update({name: str(err)})

    if status:
        rprint("[#00FF00]   OK   [#FF00FF]file: %s" % name)
    else:
        rprint("[#FF0000] ERROR! [#FF00FF]file: %s" % name)

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
