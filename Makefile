.PHONY: test

help :
	@echo "-----------------------------------------------------------"
	@echo "Look in README.md for general information                  "
	@echo "-----------------------------------------------------------"
	@echo "up              ... Run local service                      "
	@echo "down            ... Stop local service                     "
	@echo "test            ... Run unit tests                         "
	@echo "deploy          ... Deploy cloud service                   "
	@echo
	@echo "clean           ... cleanup python cache files             "
	@echo "help            ... print this message                     "
	@echo "-----------------------------------------------------------"

up:
	echo "Start local service"

down:
	echo "Stop local service"

test:
	echo "Running unit tests"
	-coverage run -m pytest tests/ | tee coverage.log
	coverage report -m | tee -a coverage.log

deploy:
	echo "Cloud deploy"

clean:
	rm -rf `find . -name .cache`
	rm -rf `find . -name .pytest_cache`
	rm -rf `find . -name __pycache__`
	rm -rf `find . -name .mypy_cache`
