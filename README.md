# WEditor (some fork)
[//]: [![image](https://img.shields.io/pypi/v/weditor.svg?style=flat-square)](https://pypi.python.org/pypi/weditor)
[//]: [![image](https://img.shields.io/github/stars/alibaba/web-editor.svg?style=social&label=Star&style=flat-square)](https://github.com/alibaba/web-editor)
[//]: [![image](https://travis-ci.org/alibaba/web-editor.svg?branch=master)](https://travis-ci.org/alibaba/web-editor)

[English README.md](README.md)

[//]: 编辑器能够提供辅助编写脚本，查看组件信息，调试代码等功能。

Screenshot

![screenshot](./screenshot.jpg)

## Installation
Dependencies

- Python3.6+
  - [uiautomator2](https://github.com/openatx/uiautomator2)
  - [facebook-wda](https://github.com/openatx/facebook-wda)


> Only tested in `Google Chrome`, _IE_ seems not working well.

```bash
pip3 install -U weditor, uiautomator2, facebook-wda
```

For developers

```bash
git clone https://github.com/vonhacht/web-editor
pip3 install -e web-editor
```

## Instructions
```bash
weditor 
```

Make a desktop shortcut（only Windows）

```bash
weditor --shortcut
```

More options: `weditor --help` 

If the web browser not automatically opens: <http://localhost:17310>

> 17310 is in honor of the projects creation and refeers to the date 2017/03/10

## Pathways

**Mac**

- Command+Enter: Runs all code in the editor
- Command+SHIFT+Enter: Runs the chosen code on the marker

**Windows**

- CTRL+Enter: Runs all code in the editor
- CTRL+SHIFT+Enter: Runs the chosen code on the marker

## Developer documentation
See [DEVELOP.md](DEVELOP.md)

## LICENSE
[MIT](LICENSE)
