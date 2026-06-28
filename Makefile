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
	python3.11 scripts/export_slide_assets.py

deck: slides
	python3.11 scripts/build_deck.py

all:
	python3.11 run.py all
	make deck
	make app
