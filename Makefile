PY ?= python3
ADDON := plugin.video.rivedila7
VERSION := $(shell $(PY) -c "import xml.etree.ElementTree as E;print(E.parse('addon.xml').getroot().get('version'))")
DEST ?= $(HOME)/.var/app/tv.kodi.Kodi/data/addons/$(ADDON)
BUILD ?= /tmp/$(ADDON)-build
ZIP ?= $(HOME)/Downloads/$(ADDON)-$(VERSION).zip

.PHONY: all test smoke walk fixtures zip shipped deploy clean

all: test smoke

test:                ## offline tests: the harness rules and the code it judges
	$(PY) -m unittest discover -s tests -t . -v

smoke:               ## live check of every section against the site
	$(PY) tests/harness.py smoke

walk:                ## make walk ARGS="tutti_programmi --depth 2"
	$(PY) tests/harness.py walk $(ARGS)

fixtures:            ## recapture the site fixtures the offline tests read
	$(PY) tests/fixtures/capture.py

zip:                 ## build the installable ZIP: the add-on, and nothing that is not the add-on
	rm -rf $(BUILD) && mkdir -p $(BUILD)/$(ADDON)
	git archive HEAD | tar -x -C $(BUILD)/$(ADDON)
	# the suite, the design notes and the CI are how the add-on is made, not what it is:
	# Kodi installs a plugin by unpacking it and importing addon.py, and nothing else
	rm -rf $(BUILD)/$(ADDON)/tests $(BUILD)/$(ADDON)/design $(BUILD)/$(ADDON)/.github
	cd $(BUILD) && rm -f $(ZIP) && zip -qr $(ZIP) $(ADDON)
	@echo $(ZIP)

shipped: zip         ## the ZIP carries the add-on: this proves it
	@if unzip -Z1 $(ZIP) | grep -E '^(plugin\.video\.rivedila7/)?(tests|design|\.github)/'; then \
		echo "the ZIP carries files that are not the add-on"; exit 1; \
	else \
		echo "$(notdir $(ZIP)) carries the add-on only: $$(unzip -Z1 $(ZIP) | wc -l) files"; \
	fi

deploy:              ## install the committed tree into Kodi, identical to the ZIP
	rm -rf $(DEST) && mkdir -p $(DEST)
	git archive HEAD | tar -x -C $(DEST)
	rm -rf $(DEST)/tests $(DEST)/design $(DEST)/.github
	find $(DEST) -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "deployed $(VERSION) to $(DEST)"

clean:
	rm -rf $(BUILD)
