PROJECT=craft_parts
# Define when more than the main package tree requires coverage
# like is the case for snapcraft (snapcraft and snapcraft_legacy):
# COVERAGE_SOURCE="starcraft"
UV_TEST_GROUPS := "--group=dev"
UV_DOCS_GROUPS := "--group=docs"
UV_LINT_GROUPS := "--group=lint" "--group=types"
UV_TICS_GROUPS := "--group=tics"

# If you have dev dependencies that depend on your distro version, uncomment these:
ifneq ($(wildcard /etc/os-release),)
include /etc/os-release
endif
ifdef VERSION_CODENAME
UV_TEST_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_DOCS_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_LINT_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_TICS_GROUPS += "--group=dev-$(VERSION_CODENAME)"
endif

include common.mk

.PHONY: format
format: format-ruff format-codespell format-prettier format-pre-commit  ## Run all automatic formatters

.PHONY: lint
lint: lint-ruff lint-codespell lint-mypy lint-prettier lint-pyright lint-shellcheck lint-docs lint-twine lint-uv-lockfile  ## Run all linters

.PHONY: pack
pack: pack-pip  ## Build all packages

.PHONY: pack-snap
pack-snap: snap/snapcraft.yaml  ##- Build snap package
ifeq ($(shell which snapcraft),)
	sudo snap install --classic snapcraft
endif
	snapcraft pack

# Find dependencies that need installing
APT_PACKAGES :=
ifeq ($(wildcard /usr/include/libxml2/libxml/xpath.h),)
APT_PACKAGES += libxml2-dev
endif
ifeq ($(wildcard /usr/include/libxslt/xslt.h),)
APT_PACKAGES += libxslt1-dev
endif
ifeq ($(wildcard /usr/share/doc/intltool/copyright),)
APT_PACKAGES += intltool
endif
ifeq ($(wildcard /usr/share/doc/fuse-overlayfs/copyright),)
APT_PACKAGES += fuse-overlayfs
endif
ifeq ($(wildcard /usr/share/doc/socat/copyright),)
APT_PACKAGES += socat
endif
ifeq ($(wildcard /usr/share/doc/findutils/copyright),)
APT_PACKAGES += findutils
endif
ifeq ($(wildcard /usr/share/doc/python3-venv/copyright),)
APT_PACKAGES += python3-venv
endif

# Dependencies for sources
ifeq ($(wildcard /usr/share/doc/p7zip-full/copyright),)
APT_PACKAGES += p7zip-full
endif
ifeq ($(wildcard /usr/share/doc/curl/copyright),)
APT_PACKAGES += curl
endif
ifeq ($(wildcard /usr/share/doc/git/copyright),)
APT_PACKAGES += git
endif
ifeq ($(wildcard /usr/share/doc/rpm/copyright),)
APT_PACKAGES += rpm
endif

# Java tools - Used for Java plugin integration tests.
# We need *a* jdk for our unit tests to succeed. Use 17 because a unit test looks for
# it specifically.
ifeq ($(wildcard /usr/share/doc/openjdk-17-jdk/copyright),)
APT_PACKAGES += openjdk-17-jdk
endif
ifneq ($(NO_JAVA),1)  # Allow setting NO_JAVA=1 to avoid installing java deps
ifeq ($(wildcard /usr/share/doc/default-jdk/copyright),)
APT_PACKAGES += default-jdk
endif
ifeq ($(wildcard /usr/share/doc/openjdk-8-jdk-headless/copyright),)
APT_PACKAGES += openjdk-8-jdk-headless
endif
ifeq ($(wildcard /usr/share/doc/openjdk-11-jdk/copyright),)
APT_PACKAGES += openjdk-11-jdk
endif
ifeq ($(wildcard /usr/share/doc/openjdk-21-jdk/copyright),)
APT_PACKAGES += openjdk-21-jdk
endif
ifeq ($(wildcard /usr/share/doc/tinyproxy/copyright),)
APT_PACKAGES += tinyproxy
endif
ifeq ($(wildcard /usr/share/doc/gradle/copyright),)
APT_PACKAGES += gradle
endif
# Maven
ifeq ($(wildcard /usr/share/doc/maven/copyright),)
APT_PACKAGES += maven
endif
ifeq ($(wildcard /usr/share/doc/libmaven-resources-plugin-java/copyright),)
APT_PACKAGES += libmaven-resources-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libmaven-compiler-plugin-java/copyright),)
APT_PACKAGES += libmaven-compiler-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libmaven-jar-plugin-java/copyright),)
APT_PACKAGES += libmaven-jar-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libmaven-install-plugin-java/copyright),)
APT_PACKAGES += libmaven-install-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libmaven-deploy-plugin-java/copyright),)
APT_PACKAGES += libmaven-deploy-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libmaven-shade-plugin-java/copyright),)
APT_PACKAGES += libmaven-shade-plugin-java
endif
ifeq ($(wildcard /usr/share/doc/libsurefire-java/copyright),)
APT_PACKAGES += libsurefire-java
endif
endif

# Python tools - used for python plugin integration tests.
ifneq ($(NO_PYTHON),1)
ifeq ($(wildcard /usr/share/doc/python3-poetry/copyright),)
APT_PACKAGES += python3-poetry
endif
ifeq ($(wildcard /usr/share/doc/python3-dev/copyright),)
APT_PACKAGES += python3-dev
endif
# Poetry 2+ removes the export subcommand and requires you to get a plugin for it
# However, jammy uses an older poetry version that still has that subcommand
ifneq ($(VERSION_CODENAME),jammy)
ifeq ($(wildcard /usr/share/doc/python3-poetry-plugin-export/copyright),)
APT_PACKAGES += python3-poetry-plugin-export
endif
# On Jammy, we can use pip to install meson. Everywhere else we install it through apt.
ifeq ($(wildcard /usr/share/doc/meson/copyright),)
APT_PACKAGES += meson
endif
endif
endif

# Tools needed for plugin integration tests that aren't java or python
ifneq ($(NO_PLUGIN),1)
ifeq ($(wildcard /usr/share/doc/automake/copyright),)
APT_PACKAGES += automake
endif
ifeq ($(wildcard /usr/share/doc/autopoint/copyright),)
APT_PACKAGES += autopoint
endif
ifeq ($(wildcard /usr/share/doc/cargo/copyright),)
APT_PACKAGES += cargo
endif
ifeq ($(wildcard /usr/share/doc/cmake/copyright),)
APT_PACKAGES += cmake
endif
# We'll check for any dotnet SDK, but install dotnet 8 since that version is common to
# 22.04 -> 25.10 (and possibly 26.04).
# On focal, we'll get the snap instead.
ifeq ($(wildcard /usr/share/doc/dotnet-sdk-*/copyright),)
ifneq ($(UBUNTU_CODENAME),focal)
APT_PACKAGES += dotnet-sdk-8.0
endif
endif
ifeq ($(wildcard /usr/share/doc/gcc/copyright),)
APT_PACKAGES += gcc
endif
ifeq ($(wildcard /usr/share/doc/meson/copyright),)
APT_PACKAGES += meson
endif
ifeq ($(wildcard /usr/share/doc/pkg-config/copyright),)
APT_PACKAGES += pkg-config
endif
ifeq ($(wildcard /usr/share/doc/ninja-build/copyright),)
APT_PACKAGES += ninja-build
endif
ifeq ($(wildcard /usr/share/doc/scons/copyright),)
APT_PACKAGES += scons
endif
# Specifically used by the autotools plugin tests.
ifeq ($(wildcard /usr/share/doc/gperf/copyright),)
APT_PACKAGES += gperf
endif
ifeq ($(wildcard /usr/share/doc/help2man/copyright),)
APT_PACKAGES += help2man
endif
ifeq ($(wildcard /usr/share/doc/texinfo/copyright),)
APT_PACKAGES += texinfo
endif
# Used by the autotools plugin itself.
ifeq ($(wildcard /usr/share/doc/libtool/copyright),)
APT_PACKAGES += libtool
endif
endif

.PHONY: install-chisel
install-chisel:
ifneq ($(shell which chisel),)
else ifeq ($(shell which snap),)
	$(warning Cannot install chisel without snap. Please install it yourself.)
else
	sudo snap install chisel --channel latest/candidate
endif

.PHONY: install-go
install-go:
ifneq ($(shell which go),)
else ifeq ($(shell which snap),)
	$(warning Cannot install go without snap. Please install it yourself.)
else
	sudo snap install go --classic
endif

.PHONY: install-core20
install-core20:
ifneq ($(wildcard /snap/core20/),)
else ifeq ($(shell which snap),)
	$(warning Cannot install core20 without snap. Please install it yourself.)
else
	sudo snap install core20
endif

.PHONY: install-build-snaps
install-build-snaps: install-chisel install-go install-core20 install-dotnet install-rustup

# Used for installing build dependencies in CI.
.PHONY: install-build-deps
install-build-deps: _gh-runner-clean install-lint-build-deps install-build-snaps
ifeq ($(APT_PACKAGES),)
else ifeq ($(shell which apt-get),)
	$(warning Cannot install build dependencies without apt.)
	$(warning Please ensure the equivalents to these packages are installed: $(APT_PACKAGES))
else
	sudo $(APT) install $(APT_PACKAGES)
endif

# If additional build dependencies need installing in order to build the linting env.
.PHONY: install-lint-build-deps
install-lint-build-deps:

.PHONY: install-rustup
install-rustup:
ifeq ($(shell which rustup),)
else ifeq ($(shell which snap),)
	$(warning Cannot install rustup without snap. Install it yourself.)
else
	sudo snap install rustup --classic
endif

# A temporary override to the lint-docs directive to ignore the sphinx-docs-starter-pack git submodule.
.PHONY: lint-docs
lint-docs:  ##- Lint the documentation
ifneq ($(CI),)
	@echo ::group::$@
endif
	uv run $(UV_DOCS_GROUPS) sphinx-lint --max-line-length 88 --ignore docs/reference/commands --ignore docs/_build --ignore docs/sphinx-docs-starter-pack --enable all $(DOCS) -d missing-underscore-after-hyperlink,missing-space-in-hyperlink
	uv run $(UV_DOCS_GROUPS) sphinx-build -b linkcheck -W $(DOCS) docs/_linkcheck
ifneq ($(CI),)
	@echo ::endgroup::
endif

.PHONY: install-dotnet
install-dotnet:
ifeq ($(UBUNTU_CODENAME),focal)
ifeq ($(wildcard /snap/dotnet),)  # Skip if we already have dotnet
ifeq ($(shell which snap),)
	$(warning Cannot install dotnet without snap.)
else
	sudo snap install dotnet --classic
endif
endif
endif

.PHONY: install-rustup
install-rustup:
ifeq ($(shell which snap),)
	$(warning Cannot install rustup without snap.)
else
	sudo snap install rustup --classic
endif

.PHONY: _gh-runner-clean
_gh-runner-clean:
# Prepare and fix issues on Github-hosted runners.
ifeq ($(CI)_$(RUNNER_ENVIRONMENT),true_github-hosted)
	# Delete the (huge) Android SDK in the background.
	nohup sudo rm -rf /usr/local/lib/android/ > /dev/null &
	# Remove the github-installed cmake 4 because it breaks the cmake tests.
	# See: https://github.com/actions/runner-images/issues/13023
	nohup sudo rm -rf /usr/local/bin/cmake /usr/local/bin/cmake-gui /usr/local/bin/ccmake /usr/local/bin/ctest /usr/local/bin/cpack > /dev/null &
	nohup sudo rm -rf /usr/local/share/cmake-4* > /dev/null &
	# Remove Github-installed JDK 25 that's not in the repos.
	# https://github.com/actions/runner-images/issues/13138
	sudo $(APT) purge temurin-*-jdk || true
	echo "JAVA_HOME=" >> "${GITHUB_ENV}"
	# Delete the adoptium repository:
	# https://github.com/actions/runner-images/blob/6fd5896f04e572647774996a7b292b854e6e8bc0/images/ubuntu/scripts/build/install-java-tools.sh#L67
	sudo rm -f /etc/apt/sources.list.d/adoptium.list
endif
