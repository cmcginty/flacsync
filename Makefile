NAME=flacsync
VER=0.2.1
DIST_DIR=dist
TAR=${DIST_DIR}/${NAME}-${VER}.tar.gz
SRC_DIR=${DIST_DIR}/${NAME}-${VER}

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  help           to print his output message"
	@echo "  test           to run all unit-tests"
	@echo "  cover          to run unit-tests w/ code coverage stats"
	@echo "  install        to install the applicataion"
	@echo "  clean          to remove tmp files"
	@echo "  doc            to genearte Sphinx html documents"
	@echo "  doc-svnprop    to set correct svn prop mime type on docs"
	@echo "  dist           to generate a complete source archive"
	@echo "  release        to perform a full test/dist/install"
	@echo "  register       to update the PyPI registration"

.PHONY: test
test:
	nosetests -w flacsync

.PHONY: cover
cover:
	nosetests -w flacsync --with-coverage --cover-package=flacsync --cover-erase --cover-inclusive

.PHONY: install
install:
	python setup.py install

.PHONY: clean
clean:
	python setup.py clean

.PHONY: doc
doc:
	make -C doc html

.PHONY: doc-svnprop
doc-svnprop:
	svn propset -R svn:mime-type text/css        `find doc/_build/html/ -name .svn -type f -prune -o -name *.css`
	svn propset -R svn:mime-type text/javascript `find doc/_build/html/ -name .svn -type f -prune -o -name *.js`
	svn propset -R svn:mime-type text/x-png      `find doc/_build/html/ -name .svn -type f -prune -o -name *.png`
	svn propset -R svn:mime-type text/html       `find doc/_build/html/ -name .svn -type f -prune -o -name *.html`

.PHONY: dist
dist:
	python setup.py sdist --force-manifest
	make clean

.PHONY: dist-test
dist-test:
	tar xzf ${TAR} -C ${DIST_DIR}
	sudo make -C ${SRC_DIR} install
	sudo rm -rf ${SRC_DIR}

.PHONY: release
release: test dist dist-test

.PHONY: register
register:
	python setup.py register

