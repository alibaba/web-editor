## Doc for Developers
```bash
# clone
git clone https://github.com/vonhacht/web-editor
pip install -e weditor
```

Where the `-e` option is for installing web-editor in `site-packages`


When done editing，run `python -m weditor`

## The default layout of the site
```
----------------------------
NAV
----------------------------
Screen | Properties | Tree
----------------------------
```

The following code is written in pug (renamed from jade)

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

## References
- https://www.jstree.com/
- fontawesome icons: https://fontawesome.com/v4.7.0/icons/
- element-ui component：https://element.eleme.cn
- bootstrap v3: https://v3.bootcss.com/

# LocalStorage
store keys:

- windowHierarchy: JSON.stringified data
- screenshotBase64
- code
