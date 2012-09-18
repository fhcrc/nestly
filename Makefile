.PHONY: test docs tox

PYTHON ?= python

docs:
	$(MAKE) -C docs html

test:
	$(PYTHON) setup.py test

tox:
	tox
