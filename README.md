# easy_DMS
PDF person profile to MS Word document 

pip uninstall fitz

pip install PyMuPDF

pip install Pillow

pyinstaller --add-data "C:\_easy_dms\venv\Lib\site-packages\pyfiglet;./pyfiglet" --hidden-import gradient_figlet --hidden-import pyfiglet --hidden-import pyfiglet.fonts --noconfirm --onefile --icon C:/_easy_dms/bitmap.ico --name easy_dms C:/_easy_dms/main.py