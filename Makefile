NAME := pdftextorizer

ENV_DIR := env

SETUP_FILES := pyproject.toml
SOURCE_DIRS := src

PYTHON ?= python

all: $(NAME)

$(NAME): venv
	@echo " [BUILD]"
	. $(ENV_DIR)/bin/activate; $(PYTHON) -m pip install .

run: $(NAME)
	@echo " [RUN]"
	. $(ENV_DIR)/bin/activate; $(NAME) $(arg)

isort: venv
	@echo " [ISORT]"
	. $(ENV_DIR)/bin/activate; isort $(SOURCE_DIRS)

autopep8: venv
	@echo " [AUTOPEP8]"
	. $(ENV_DIR)/bin/activate; autopep8 -aair $(SOURCE_DIRS)

format: isort autopep8

flake8: venv
	@echo " [FLAKE8]"
	-. $(ENV_DIR)/bin/activate; flake8 $(SOURCE_DIRS)

mypy: venv
	@echo " [MYPY]"
	-. $(ENV_DIR)/bin/activate; mypy $(SOURCE_DIRS)

pylint: venv
	@echo " [PYLINT]"
	-. $(ENV_DIR)/bin/activate; pylint $(SOURCE_DIRS)

lint: flake8 mypy pylint

doxygen:
	@echo " [DOXYGEN]"
	doxygen

venv: $(ENV_DIR)/touchfile

$(ENV_DIR)/touchfile: $(SETUP_FILES)
	@echo " [VENV]"
	$(PYTHON) -m venv $(ENV_DIR)
	. $(ENV_DIR)/bin/activate; $(PYTHON) -m pip install ".[dev]"
	touch $(ENV_DIR)/touchfile

clean:
	@echo " [CLEAN]"
	rm -rf $(ENV_DIR)
	rm -rf build
	rm -rf .mypy_cache
	rm -rf doc/doxygen/html
	rm -rf $(foreach SOURCE_DIR,$(SOURCE_DIRS),$(SOURCE_DIR)/$(NAME).egg-info)

.PHONY: clean isort format nothing $(NAME) run

$(V).SILENT:
