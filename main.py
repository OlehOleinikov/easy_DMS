import os
import time

from gradient_figlet import print_with_gradient_figlet
from rich.console import Group
from rich.panel import Panel
from rich.live import Live
from rich import print as rprint
from rich.tree import Tree
from rich.console import Console
from rich.table import Table
from rich.progress import BarColumn, TimeElapsedColumn, Progress, TextColumn, SpinnerColumn

from converter_pdf import PersonProfile, get_pdf_data
from ms_word_editor import DocEditor
from defines import melody_run

person_cards = []
errors_dict = {}

rprint('[#FF00FF]' + 'build 140223 - 2023 by @matematik_777 (https://github.com/OlehOleinikov)' + '[/#FF00FF]')
print_with_gradient_figlet('--------', color1='#FF00FF', color2='#01FFFF', font='speed')
print_with_gradient_figlet('Easy DMS', color1='#FF00FF', color2='#01FFFF', font='speed')
print_with_gradient_figlet('--------', color1='#FF00FF', color2='#01FFFF', font='speed')
rprint('[#FF00FF]Scaning...\n')

melody = melody_run()
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


def run_steps(name, step_times, app_steps_task_id):
    """Run steps for a single app, and update corresponding progress bars."""

    for idx, step_time in enumerate(step_times):
        # add progress bar for this step (time elapsed + spinner)
        action = step_actions[idx]
        step_task_id = step_progress.add_task("", action=action, name=name)

        # run steps, update progress
        for _ in range(step_time):
            time.sleep(0.5)
            step_progress.update(step_task_id, advance=1)

        # stop and hide progress bar for this step when done
        step_progress.stop_task(step_task_id)
        step_progress.update(step_task_id, visible=False)

        # also update progress bar for current app when step is done
        app_steps_progress.update(app_steps_task_id, advance=1)


# progress bar for current app showing only elapsed time,
# which will stay visible when app is installed
current_app_progress = Progress(
    TimeElapsedColumn(),
    TextColumn("{task.description}"),
)

# progress bars for single app steps (will be hidden when step is done)
step_progress = Progress(
    TextColumn("  "),
    TimeElapsedColumn(),
    TextColumn("[bold purple]{task.fields[action]}"),
    SpinnerColumn("simpleDots"),
)
# progress bar for current app (progress in steps)
app_steps_progress = Progress(
    TextColumn(
        "[bold blue]Progress for app {task.fields[name]}: {task.percentage:.0f}%"
    ),
    BarColumn(),
    TextColumn("({task.completed} of {task.total} steps done)"),
)
# overall progress bar
overall_progress = Progress(
    TimeElapsedColumn(), BarColumn(), TextColumn("{task.description}")
)
# group of progress bars;
# some are always visible, others will disappear when progress is complete
progress_group = Group(
    Panel(Group(current_app_progress, step_progress, app_steps_progress), width=65, style='#FF00FF'),
    overall_progress,
)

# tuple specifies how long each step takes for that app
step_actions = ("reading file", "searching person", "getting image", "saving")

# create overall progress bar
overall_task_id = overall_progress.add_task("", total=len(files_in_dir))

# use own live instance as context manager with group of progress bars,
# which allows for running multiple different progress bars in parallel,
# and dynamically showing/hiding them
with Live(progress_group):

    for idx, name in enumerate(files_in_dir):
        status = False
        try:
            data = get_pdf_data(name)
            cur_person = PersonProfile(data, name)
            person_cards.append(cur_person)
            status = True
        except Exception as err:
            errors_dict.update({name: str(err)})

        step_times = [1, 1, 1, 1]
        # update message on overall progress bar
        top_descr = "[bold #AAAAAA](%d out of %d files converted)" % (idx, len(files_in_dir))
        overall_progress.update(overall_task_id, description=top_descr)

        # add progress bar for steps of this app, and run the steps
        current_task_id = current_app_progress.add_task("Converting file %s" % name)
        app_steps_task_id = app_steps_progress.add_task("", total=len(step_times), name=name)
        run_steps(name, step_times, app_steps_task_id)

        # stop and hide steps progress bar for this specific app
        app_steps_progress.update(app_steps_task_id, visible=False)
        current_app_progress.stop_task(current_task_id)
        if status:
            current_app_progress.update(current_task_id,
                                        description="[#00FF00]   OK   [#FF00FF]Person from file: %s" % name)
        else:
            current_app_progress.update(current_task_id,
                                        description="[#FF0000] ERROR! [#FF00FF]Person from file: %s" % name)

        # increase overall progress now this task is done
        overall_progress.update(overall_task_id, advance=1)

    # final update for message on overall progress bar
    overall_progress.update(
        overall_task_id, description="[bold green]%s PDF processed!" % len(files_in_dir)
    )

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
