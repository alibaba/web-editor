# WEditor
[![image](https://img.shields.io/pypi/v/weditor.svg?style=flat-square)](https://pypi.python.org/pypi/weditor)
[![image](https://img.shields.io/github/stars/alibaba/web-editor.svg?style=social&label=Star&style=flat-square)](https://github.com/alibaba/web-editor)
[![image](https://travis-ci.org/alibaba/web-editor.svg?branch=master)](https://travis-ci.org/alibaba/web-editor)

[中文文档](README_ZH.md)

This project is subproject for smart phone test framework [openatx](https://github.com/openatx)
for easily use web browser to edit UI scripts.

Screenshot

![screenshot](./screenshot.jpg)

## Installation
Dependencies

- Python3.6+
  - [uiautomator2](https://github.com/openatx/uiautomator2)
  - [facebook-wda](https://github.com/openatx/facebook-wda)


> Only tested in `Google Chrome`, _IE_ seems not working well.

```
pip3 install -U weditor
```

For developers

```bash
git clone https://github.com/openatx/weditor
pip3 install -e weditor
```

## Usage
Create Shortcut in Desktop (Only windows)

```
weditor --shortcut
```

By click shortcut or run in command line

```
weditor
```

This command will start a local server with port 17310,
and then open a browser tab for you to editor you code.

Port 17310 is to memorize the created day -- 2017/03/10

To see more usage run `weditor -h`

## Hotkeys(Both Mac and Win)
- Right click screen: `Dump Hierarchy`

### Hotkeys(only Mac)
- Command+Enter: Run the whole code
- Command+Shift+Enter: Run selected code or current line if not selected

### Hotkeys(only Win)
- Ctrl+Enter: Run the whole code
- Ctrl+Shift+Enter: Run selected code or current line if not selected

## For Developers
See [DEVELOP.md](DEVELOP.md)

## LICENSE
[MIT](LICENSE)
