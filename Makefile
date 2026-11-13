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

# /*
# ** LINT-STRICT
# ** (optional) Execute the commands flake8 . and mypy . --strict
# */


#------------ADDITIONAL COMMANDS

parse:
	@echo "$(GREEN) Parsing files....$(RESET)"


