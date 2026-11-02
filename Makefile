PY ?= python3
ADDON := plugin.video.rivedila7
VERSION := $(shell $(PY) -c "import xml.etree.ElementTree as E;print(E.parse('addon.xml').getroot().get('version'))")
DEST ?= $(HOME)/.var/app/tv.kodi.Kodi/data/addons/$(ADDON)
BUILD ?= /tmp/$(ADDON)-build
ZIP ?= $(HOME)/Downloads/$(ADDON)-$(VERSION).zip

.PHONY: all test smoke walk fixtures zip deploy clean

all: test smoke

test:                ## offline tests: the harness rules and the code it judges
	$(PY) -m unittest discover -s tests -t . -v

smoke:               ## live check of every section against the site
	$(PY) tests/harness.py smoke

walk:                ## make walk ARGS="tutti_programmi --depth 2"
	$(PY) tests/harness.py walk $(ARGS)

fixtures:            ## recapture the site fixtures the offline tests read
	$(PY) tests/fixtures/capture.py

zip:                 ## build the installable ZIP from the committed tree
	rm -rf $(BUILD) && mkdir -p $(BUILD)/$(ADDON)
	git archive HEAD | tar -x -C $(BUILD)/$(ADDON)
	rm -rf $(BUILD)/$(ADDON)/tests $(BUILD)/$(ADDON)/design $(BUILD)/$(ADDON)/.github
	cd $(BUILD) && rm -f $(ZIP) && zip -qr $(ZIP) $(ADDON)
	@echo $(ZIP)

deploy:              ## install the committed tree into Kodi, identical to the ZIP
	rm -rf $(DEST) && mkdir -p $(DEST)
	git archive HEAD | tar -x -C $(DEST)
	rm -rf $(DEST)/tests $(DEST)/design $(DEST)/.github
	find $(DEST) -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "deployed $(VERSION) to $(DEST)"

clean:
	rm -rf $(BUILD)
