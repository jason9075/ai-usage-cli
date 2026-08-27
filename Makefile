.PHONY: all install dev test run tray clean

all: install

install:
	./install.sh

dev:
	uv sync

run:
	uv run ai-usage

tray:
	uv run ai-usage-tray

status:
	systemctl --user status ai-usage-tray

restart:
	systemctl --user restart ai-usage-tray

clean:
	./uninstall.sh
