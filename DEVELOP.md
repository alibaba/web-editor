## Doc for Developers
```bash
# clone
git clone https://github.com/openatx/weditor
cd weditor

# install with -e
pip install -e weditor
```

`-e`这个选项可以将weditor目录下的代码直接关联到python的`site-packages`中。


修改完后，直接运行`python -m weditor`调试

## 网页的基本布局
```
----------------------------
NAV
----------------------------
Screen | Properties | Tree
----------------------------
FOOTER
----------------------------
```

See example: https://codepen.io/codeskyblue/pen/mYdjGb

## 发布到PYPI
目前先打`git tag`, push到github之后，再通过travis发布到pypi上