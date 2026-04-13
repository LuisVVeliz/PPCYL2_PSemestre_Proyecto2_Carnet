HOLA

In this repo, you can use a single Python virtual environment for both Django and Flask.

To install the dependencies in one environment:

  python -m pip install -r backend/requirements.txt
  # or
  python -m pip install -r Frontend/requirements.txt

Then run both servers from the same virtualenv with the script:

  .\run_both.ps1 -VenvPath .\venv_django

Django: http://127.0.0.1:8000
Flask: http://127.0.0.1:5000

