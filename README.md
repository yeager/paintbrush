# PaintBrush 🎨

A simple painting and drawing application for Linux, built with GTK4 and libadwaita.

## Features

- Multiple drawing tools: brush, eraser, line, rectangle, circle, star, polygon, text, fill
- Color palette with custom color picker
- Adjustable brush size
- Undo/Redo support
- Zoom in/out
- Open and save images (PNG, JPEG, GIF)
- Keyboard shortcuts for all tools
- Modern Adwaita UI with welcome screen

## Install

### From APT repository
```bash
wget -qO- https://yeager.github.io/debian-repo/yeager-repo-key.asc | sudo tee /usr/share/keyrings/yeager-repo.asc > /dev/null
sudo tee /etc/apt/sources.list.d/yeager.sources << 'SOURCES'
Types: deb
URIs: https://yeager.github.io/debian-repo/
Suites: stable
Components: main
Signed-By: /usr/share/keyrings/yeager-repo.asc
SOURCES
sudo apt update
sudo apt install paintbrush
```

### Dependencies
- Python 3
- GTK 4
- libadwaita 1
- GdkPixbuf 2.0

## Translate

Help translate PaintBrush: https://app.transifex.com/danielnylander/paintbrush

## License

GPL-3.0 — see [LICENSE](LICENSE)
