.DEFAULT_GOAL := help
PORT ?= 8000
SITE := build/site

.PHONY: help install build serve clean

help: ## Show this list
	@awk -F':.*## ' '/^[a-z]+:.*## / {printf "  make %-8s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

node_modules: package.json package-lock.json
	npm ci --ignore-scripts
	@touch $@

install: node_modules ## Install Antora from the lockfile

build: node_modules ## Generate the static site into build/site
	npx antora antora-playbook.yml

serve: build ## Build, then serve at http://127.0.0.1:8000 (other port: PORT=8080 make serve)
	python3 -m http.server $(PORT) --bind 127.0.0.1 --directory $(SITE)

clean: ## Remove build/
	rm -rf build
