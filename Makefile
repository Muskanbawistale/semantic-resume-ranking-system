install:
	python -m pip install -r requirements.txt

run:
	streamlit run app/streamlit_app.py

test:
	pytest -q

lint:
	ruff check .
