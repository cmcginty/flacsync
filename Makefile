# flacsync // (c) 2011 Patrick C. McGinty
# flacsync[@]tuxcoder[dot]com
#

NAME=flacsync
VER=0.3.2
DIST_DIR=dist
TAR=${DIST_DIR}/${NAME}-${VER}.tar.gz
HTML_ZIP=${DIST_DIR}/${NAME}-html-${VER}.zip
SRC_DIR=${DIST_DIR}/${NAME}-${VER}

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  help           to print his output message"
	@echo "  test           to run all unit-tests"
	@echo "  cover          to run unit-tests w/ code coverage stats"
	@echo "  install        to install the applicataion"
	@echo "  clean          to remove tmp files"
	@echo "  readme         to generate the README file"
	@echo "  doc            to genearte Sphinx html documents"
	@echo "  doc-clean      to clean Sphinx html documents"
	@echo "  dist           to generate a complete source archive"
	@echo "  release        to perform a full test/dist/install"
	@echo "  register       to update the PyPI registration"

.PHONY: test
test:
	python -m unittest discover -f

.PHONY: cover
cover:
	nosetests -w ${NAME} --with-coverage --cover-package=${NAME} --cover-erase --cover-inclusive

.PHONY: install
install: test
	python setup.py install --user

.PHONY: clean
clean:
	python setup.py clean

.PHONY: readme
readme:
	python -c "import ${NAME}; \
              from textwrap import dedent; \
              print dedent(${NAME}.__doc__)" > README

.PHONY: doc
doc: readme
	make -C doc html
	rm -f ${HTML_ZIP}
	cd doc/_build/html; zip -qr ../../../${HTML_ZIP} .

.PHONY: doc-clean
doc-clean:
	make -C doc clean

.PHONY: dist
dist: doc
	python setup.py sdist
	make clean

.PHONY: dist-test
dist-test: dist
	tar xzf ${TAR} -C ${DIST_DIR}
	make -C ${SRC_DIR} install
	rm -rf ${SRC_DIR}

.PHONY: release
release: test dist dist-test

.PHONY: register
register: release
	python setup.py register --strict

