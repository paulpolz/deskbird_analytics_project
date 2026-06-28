.PHONY: setup generate dbt app all slides deck

setup:
	python3.11 run.py setup

generate:
	python3.11 run.py generate

dbt:
	python3.11 run.py dbt

app:
	python3.11 run.py app

slides:
	python3.11 run.py slides

deck:
	python3.11 run.py deck

all:
	python3.11 run.py all
	python3.11 run.py deck
	python3.11 run.py app
