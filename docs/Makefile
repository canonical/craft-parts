# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= -q
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
PORT          = 8080
VENV          = sphinx-resources/.sphinx/venv/bin/activate

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

install:
	@echo "... setting up virtualenv"
	python3 -m venv sphinx-resources/.sphinx/venv
	. $(VENV); pip install --upgrade -e ..[docs]
	. $(VENV); pip install python-apt@https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/python-apt/2.4.0ubuntu1/python-apt_2.4.0ubuntu1.tar.xz
	. $(VENV); pip install --upgrade -r requirements.txt
	. $(VENV); pip install setuptools  # Needed for Python 3.12: https://github.com/sphinx-contrib/sphinxcontrib-details-directive/issues/5

	@echo "\n" \
		"--------------------------------------------------------------- \n" \
		"* watch, build and serve the documentation: make run \n" \
                "* only build: make html \n" \
                "* only serve: make serve \n" \
                "* clean built doc files: make clean-doc \n" \
                "* clean full environment: make clean \n" \
		"* check spelling: make spelling \n" \
                "* check inclusive language: make woke \n" \
		"--------------------------------------------------------------- \n"
run:
	. $(VENV); sphinx-autobuild -c . -b html "$(SOURCEDIR)" "$(BUILDDIR)"

html:
	. $(VENV); $(SPHINXBUILD) -c . -b html "$(SOURCEDIR)" "$(BUILDDIR)" -w sphinx-resources/.sphinx/warnings.txt

epub:
	. $(VENV); $(SPHINXBUILD) -c . -b epub "$(SOURCEDIR)" "$(BUILDDIR)" -w sphinx-resources/.sphinx/warnings.txt

serve:
	cd "$(BUILDDIR)"; python3 -m http.server 8000

clean: clean-doc
	rm -rf reference/commands
	rm -rf sphinx-resources/.sphinx/venv

clean-doc:
	git clean -fx "$(BUILDDIR)"

clean-html: clean-doc
	+$(MAKE) html

spelling: clean-html
	. $(VENV) ; python3 -m pyspelling -c sphinx-resources/.sphinx/spellingcheck.yaml -j $(shell nproc)

linkcheck:
	. $(VENV) ; $(SPHINXBUILD) -c . -b linkcheck  "$(SOURCEDIR)" "$(BUILDDIR)"

woke:
	type woke >/dev/null 2>&1 || { snap install woke; exit 1; }
	woke *.rst **/*.rst -c https://github.com/canonical-web-and-design/Inclusive-naming/raw/main/config.yml

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	. $(VENV); $(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

rundocs: ## start a documentation runserver
	sphinx-autobuild $(SPHINXOPTS) --ignore ".git/*" --ignore "*.scss" --ignore "*.kate-swp"  --host 0.0.0.0 --port $(PORT) "$(SOURCEDIR)" "$(BUILDDIR)"

