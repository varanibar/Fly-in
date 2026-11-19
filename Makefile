#------------COLORS
GREEN = \033[1;92m
RED = \033[1;91m
RESET = \033[0m # resets all terminal colors and text styles back to their default normal state.

#------------TOOLS



#------------FLAGS



# ------------COMMANDS

# /*
# ** INSTALL
# ** Install project dependencies using pip, uv, pipx, or any other package
# ** manager of your choice.
# */

# /*
# ** RUN
# ** Execute the main script of your project (e.g., via Python interpreter).
# */

# /*
# ** DEBUG
# ** Run the main script in debug mode using Python’s built-in debugger (e.g.,
# ** pdb).
# */

# /*
# ** CLEAN
# ** Remove temporary files or caches (e.g., __pycache__, .mypy_cache) to
# ** keep the project environment clean.
# */

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf __pycache__ .mypy_cache
	rm -rf */__pycache__ */.mypy_cache


# /*
# ** FCLEAN
# ** CLEAN + Remove vitual environment
# */

# /*
# ** LINT
# ** Execute the commands flake8 . and mypy . --warn-return-any
# ** --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs
# ** --check-untyped-defs
# */

lint:
	@status=0; \
	echo "=== flake8 ==="; \
	python3 -m flake8 . || status=1; \
	echo "\n=== mypy ==="; \
	python3 -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	exit $$status

# /*
# ** LINT-STRICT
# ** (optional) Execute the commands flake8 . and mypy . --strict
# */
lint-strict:
	@status=0; \
	echo "=== flake8 ==="; \
	python3 -m flake8 . || status=1; \
	echo "\n=== mypy ==="; \
	python3 -m mypy --strict . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
	exit $$status

#------------ADDITIONAL COMMANDS

parse:
	clear
	@echo "$(GREEN) Parsing files....$(RESET)"
	python3 src/file_parser.py

t-val-zone:
	clear
	python3 -m tests.zone_testing tests/valid_maps
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf __pycache__ .mypy_cache
	rm -rf */__pycache__ */.mypy_cache

t-inval-zone:
	clear
	python3 -m tests.zone_testing tests/invalid_maps/invalid_zones
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf __pycache__ .mypy_cache
	rm -rf */__pycache__ */.mypy_cache


.PHONY: run, clean, lint, lint-strict, parse, t-val-zone, t-inval-zone
