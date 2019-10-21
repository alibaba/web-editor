## Doc for Developers
```bash
# clone
git clone https://github.com/openatx/weditor
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
```

The following code is written in pug(rename from jade)

```pug
body
  nav
  #upper
    #left
      section#screen
      section#footer
      #horizon-gap
      #console
    #vertical-gap1
  #middle
    .panel
      .panel-body
      table
      input(type="text")
      pre.editor-container
  .vertical-gap
  #right
    .panel
      .panel-heading
    div(class=["input-group", "input-group-sm"])
      .input-group-btn
      input#jstree-search
      span.input-gropu-btn
    .box
      #jstree-hierarchy

```


See example: https://codepen.io/codeskyblue/pen/mYdjGb

## 发布到PYPI
目前先打`git tag`, push到github之后，再通过travis发布到pypi上

## References
- https://www.jstree.com/
- fontawesome icons: https://fontawesome.com/v4.7.0/icons/
- element-ui 组件：https://element.eleme.cn
- bootstrap v3: https://v3.bootcss.com/

# LocalStorage
store keys:

- windowHierarchy: JSON.stringified data
- screenshotBase64
- code
