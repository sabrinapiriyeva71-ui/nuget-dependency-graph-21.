.PHONY: build test

build:
	python3 -m compileall -q src

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
