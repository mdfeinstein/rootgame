@echo off
setlocal
call "C:\Users\Mati\miniconda3\condabin\conda.bat" activate spyderweb || (echo [ERR] conda activate failed&exit /b 1)
cd /d "F:\RootGame" || (echo [ERR] project path not found&exit /b 1)
python manage.py runserver
cmd /k