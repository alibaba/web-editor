window.LOCAL_URL = 'http://localhost:17310/';
window.LOCAL_VERSION = '0.0.2'

/* Image Pool */
function ImagePool(size) {
  this.size = size
  this.images = []
  this.counter = 0
}

ImagePool.prototype.next = function() {
  if (this.images.length < this.size) {
    var image = new Image()
    this.images.push(image)
    return image
  } else {
    if (this.counter >= this.size) {
      // Reset for unlikely but theoretically possible overflow.
      this.counter = 0
    }
  }

  return this.images[this.counter++ % this.size]
}

function b64toBlob(b64Data, contentType, sliceSize) {
  contentType = contentType || '';
  sliceSize = sliceSize || 512;

  var byteCharacters = atob(b64Data);
  var byteArrays = [];

  for (var offset = 0; offset < byteCharacters.length; offset += sliceSize) {
    var slice = byteCharacters.slice(offset, offset + sliceSize);

    var byteNumbers = new Array(slice.length);
    for (var i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }

    var byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }

  return new Blob(byteArrays, {
    type: contentType
  });
}

var app = new Vue({
  el: '#app',
  data: {
    fs: {
      folder: {
        current: '/',
        items: [{
          path: '/',
        }, {
          path: '/images',
        }]
      },
      file: {
        name: '',
        path: '',
        sha: '',
        changed: false,
      },
      fileSelected: '',
      files: [{
        name: 'hello.txt',
        path: 'notes/hello.txt',
      }, {
        name: 'world.py',
        path: 'notes/world.py'
      }],
    },
    console: {
      content: '',
    },
    error: '',
    debugCode: '',
    codeRunning: false,
    wsBuild: null,
    editor: null,
    nodeSelected: null,
    nodeHovered: null,
    originNodes: [],
    platform: 'Android',
    serial: '',
    codeShortFlag: true, // generate short or long code
    imagePool: null,
    loading: false,
    canvas: {
      bg: null,
      fg: null,
    },
    canvasStyle: {
      opacity: 0.5,
      width: 'inherit',
      height: 'inherit'
    },
    lastScreenSize: {
      screen: {},
      canvas: {
        width: 1,
        height: 1
      }
    },
  },
  computed: {
    nodes: function() {
      return this.originNodes
    },
    elem: function() {
      return this.nodeSelected || {};
    },
    elemXpath: function() {
      var xpath = '//' + (this.elem.className || '*');
      if (this.elem.text) {
        xpath += "[@text='" + this.elem.text + "']";
      }
      return xpath;
    },
    deviceUrl: function() {
      if (this.platform == 'Android' && this.serial == '') {
        return 'default';
      }
      if (this.platform == 'iOS' && this.serial == '') {
        return 'http://localhost:8100';
      }
      return this.serial;
    }
  },
  created: function() {
    this.imagePool = new ImagePool(100);
  },
  mounted: function() {
    var URL = window.URL || window.webkitURL;
    var currentSize = null;
    var self = this;

    this.canvas.bg = document.getElementById('bgCanvas')
    this.canvas.fg = document.getElementById('fgCanvas')
      // this.canvas = c;
    window.c = this.canvas.bg;
    var ctx = c.getContext('2d')

    $(window).resize(function() {
      self.resizeScreen();
    })

    $('.selectpicker').selectpicker('val', this.platform);

    var editor = this.editor = ace.edit("editor");
    editor.resize()
    window.editor = editor;
    this.initEditor(editor);
    this.initDragDealer();

    this.activeMouseControl();
    this.fileLoad()
      .fail(function() {
        self.editor.insert("# coding: utf-8\n\nimport atx\nd = atx.connect()")
      })

    function setError(msg) {
      self.error = msg;
      self.loading = false;
    }

    this.loading = true;
    $.ajax({
        url: LOCAL_URL + "api/v1/version",
        type: "GET",
        //contentType: "application/json; charset=utf-8"
      })
      .done(function(ret) {
        console.log("version", ret.name);
        if (ret.name !== LOCAL_VERSION) {
          self.showError("Expect local server version: " + LOCAL_VERSION + " but got " + ret.name + ", Maybe you need upgrade 'weditor'");
        }
      })
      .fail(function(ret) {
        self.showError("<p>Local server not started, start with</p><pre>$ python -m weditor</pre>");
      })
      .always(function() {
        self.loading = false;
      })

    // this.screenRefresh()
    // this.loadLiveScreen();
  },
  methods: {
    keyeventHome: function() {
      var self = this;
      return this.codeRunDebug('d.home()').then(function() {
        return self.codeInsert(code);
      }).then(function() {
        this.screenRefresh()
      })
    },
    loadCurrentFile: function() {
      this.fileLoad(this.fs.file.path)
    },
    showError: function(error) {
      this.loading = false;
      this.error = error;
      $('.modal').modal('show');
    },
    showAjaxError: function(ret) {
      if (ret.responseJSON && ret.responseJSON.description) {
        this.showError(ret.responseJSON.description);
      } else {
        this.showError("<p>Local server not started, start with</p><pre>$ python -m weditor</pre>");
      }
    },
    initDragDealer: function() {
      var self = this;

      var updateFunc = null;


      function dragMoveListener(evt) {
        evt.preventDefault();
        updateFunc(evt);
        self.resizeScreen();
        self.editor.resize();
      }

      function dragStopListener(evt) {
        document.removeEventListener('mousemove', dragMoveListener);
        document.removeEventListener('mouseup', dragStopListener);
        document.removeEventListener('mouseleave', dragStopListener);
      }

      $('#vertical-gap1').mousedown(function(e) {
        e.preventDefault();
        updateFunc = function(evt) {
          $("#left").width(evt.clientX);
        }
        document.addEventListener('mousemove', dragMoveListener);
        document.addEventListener('mouseup', dragStopListener);
        document.addEventListener('mouseleave', dragStopListener)
      });

      $('.horizon-gap').mousedown(function(e) {
        updateFunc = function(evt) {
          var $el = $("#console");
          var y = evt.clientY;
          $el.height($(window).height() - y)
        }

        document.addEventListener('mousemove', dragMoveListener);
        document.addEventListener('mouseup', dragStopListener);
        document.addEventListener('mouseleave', dragStopListener)
      })
    },
    initEditor: function(editor) {
      var self = this;
      editor.getSession().setMode("ace/mode/python");
      editor.getSession().setUseSoftTabs(true);
      editor.getSession().setUseWrapMode(true);

      editor.commands.addCommands([{
        name: 'save',
        bindKey: {
          win: 'Ctrl-S',
          mac: 'Command-S'
        },
        exec: function(editor) {
          if (self.fs.file.path) {
            self.fileSave(self.fs.file);
          } else {
            self.fileCreate(editor.getValue());
          }
        },
      }, {
        name: 'build',
        bindKey: {
          win: 'Ctrl-B',
          mac: 'Command-B'
        },
        exec: function(editor) {
          self.codeRun(editor.getValue())
        },
      }, {
        name: 'create',
        bindKey: {
          win: 'Alt-N',
          mac: 'Alt-N'
        },
        exec: function(editor) {
          self.fileCreate();
        },
      }]);

      // editor.setReadOnly(true);
      // editor.setHighlightActiveLine(false);

      editor.$blockScrolling = Infinity;
      editor.on('input', function(e) {
        self.fs.file.changed = !self.editor.session.getUndoManager().isClean();
        // self.editor.getValue() !== self.fs.file.content;
        // self.editor.session.getUndoManager().isClean();
      })

      // FIXME(ssx): maybe websocket is better  
      editor.on('focus', function() {
        if (!self.fs.file.changed) {
          self.loadCurrentFile();
        }
      })

      // Auto save file
      // setInterval(function() {
      //   self.fileSave(self.fs.file)
      // }, 1000)
    },
    fileLoad: function(path) {
      var self = this;
      path = path || 'main.py';
      return $.ajax({
          method: 'GET',
          url: LOCAL_URL + 'api/v1/contents/' + path,
          success: function(ret) {
            self.fs.file.name = ret.name;
            self.fs.file.sha = ret.sha;
            self.fs.file.path = ret.path;
            self.fs.file.content = ret.content;
            self.fs.file.changed = false;
            self.editor.setValue(ret.content);
            self.editor.clearSelection();
            self.editor.getSession().setUndoManager(new ace.UndoManager())
          }
        }).done(function() {
          this.editor.focus();
        }.bind(this))
        .fail(function(ret) {
          console.log(ret);
        })
    },
    fileSave: function(file) {
      var self = this;
      $.ajax({
        method: 'PUT',
        url: LOCAL_URL + 'api/v1/contents/' + file.path,
        data: JSON.stringify({
          content: self.editor.getValue(),
          sha: file.sha,
        }),
        success: function(ret) {
          self.editor.session.getUndoManager().markClean()
          self.fs.file.path = ret.content.path;
          self.fs.file.changed = !editor.session.getUndoManager().isClean()
          self.fs.file.sha = ret.content.sha;
        },
        error: function(ret) {
          if (ret.status == 422) {
            if (confirm("File has changed on disk, Do you want to reload it?")) {
              self.loadCurrentFile();
            }
          }
        }
      })
    },
    fileCreate: function(code) {
      var self = this;
      var filename = window.prompt('Input file name?')
      if (!filename) {
        return;
      }
      $.ajax({
          method: 'PUT',
          url: LOCAL_URL + 'api/v1/contents/' + filename,
          data: JSON.stringify({
            content: code || '# coding: utf-8'
          })
        })
        .then(function(ret) {
          self.fileLoad(ret.content.path);
        })
        .fail(function(ret) {
          alert("File " + filename + " already exists");
        })
    },
    resizeScreen: function(img) {
      // check if need update
      if (img) {
        if (this.lastScreenSize.canvas.width == img.width &&
          this.lastScreenSize.canvas.height == img.height) {
          return;
        }
      } else {
        img = this.lastScreenSize.canvas;
        if (!img) {
          return;
        }
      }
      var screenDiv = document.getElementById('screen');
      this.lastScreenSize = {
        canvas: {
          width: img.width,
          height: img.height
        },
        screen: {
          width: screenDiv.clientWidth,
          height: screenDiv.clientHeight,
        }
      }
      var canvasRatio = img.width / img.height;
      var screenRatio = screenDiv.clientWidth / screenDiv.clientHeight;
      if (canvasRatio > screenRatio) {
        Object.assign(this.canvasStyle, {
          width: Math.floor(screenDiv.clientWidth) + 'px', //'100%',
          height: Math.floor(screenDiv.clientWidth / canvasRatio) + 'px', // 'inherit',
        })
      } else {
        Object.assign(this.canvasStyle, {
          width: Math.floor(screenDiv.clientHeight * canvasRatio) + 'px', //'inherit',
          height: Math.floor(screenDiv.clientHeight) + 'px', //'100%',
        })
      }
    },
    screenDumpUI: function() {
      var self = this;
      this.loading = true;
      this.canvasStyle.opacity = 0.5;
      return this.screenRefresh()
        .fail(function(ret) {
          self.showAjaxError(ret);
        })
        .then(function() {
          return $.getJSON(LOCAL_URL + 'api/v1/devices/' + encodeURIComponent(self.deviceUrl) + '/uiview')
        })
        .fail(function(ret) {
          self.showAjaxError(ret);
        })
        .then(function(ret) {
          self.originNodes = ret.nodes;
          self.drawAllNode();
          self.loading = false;
          self.canvasStyle.opacity = 1.0;
        })
    },
    screenRefresh: function() {
      return $.getJSON(LOCAL_URL + 'api/v1/devices/' + encodeURIComponent(this.deviceUrl) + '/screenshot')
        .then(function(ret) {
          var blob = b64toBlob(ret.data, 'image/' + ret.type);
          this.drawBlobImageToScreen(blob);
        }.bind(this))
    },
    drawBlobImageToScreen: function(blob) {
      // Support jQuery Promise
      var dtd = $.Deferred();
      var bgcanvas = this.canvas.bg,
        fgcanvas = this.canvas.fg,
        ctx = bgcanvas.getContext('2d'),
        self = this,
        URL = window.URL || window.webkitURL,
        BLANK_IMG = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==',
        img = this.imagePool.next();

      img.onload = function() {
        console.log("image")
        fgcanvas.width = bgcanvas.width = img.width
        fgcanvas.height = bgcanvas.height = img.height


        ctx.drawImage(img, 0, 0, img.width, img.height);
        self.resizeScreen(img);

        // Try to forcefully clean everything to get rid of memory
        // leaks. Note self despite this effort, Chrome will still
        // leak huge amounts of memory when the developer tools are
        // open, probably to save the resources for inspection. When
        // the developer tools are closed no memory is leaked.
        img.onload = img.onerror = null
        img.src = BLANK_IMG
        img = null
        blob = null

        URL.revokeObjectURL(url)
        url = null
        dtd.resolve();
      }

      img.onerror = function() {
        // Happily ignore. I suppose this shouldn't happen, but
        // sometimes it does, presumably when we're loading images
        // too quickly.

        // Do the same cleanup here as in onload.
        img.onload = img.onerror = null
        img.src = BLANK_IMG
        img = null
        blob = null

        URL.revokeObjectURL(url)
        url = null
        dtd.reject();
      }
      var url = URL.createObjectURL(blob)
      img.src = url;
      return dtd;
    },
    loadLiveScreen: function() {
      var self = this;
      var BLANK_IMG =
        'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='
      var protocol = location.protocol == "http:" ? "ws://" : "wss://"
      var ws = new WebSocket('ws://10.240.184.233:9002');
      var canvas = document.getElementById('bgCanvas')
      var ctx = canvas.getContext('2d');
      var lastScreenSize = {
        screen: {},
        canvas: {}
      };

      ws.onopen = function(ev) {
        console.log('screen websocket connected')
      };
      ws.onmessage = function(message) {
        console.log("New message");
        var blob = new Blob([message.data], {
          type: 'image/jpeg'
        })
        var img = self.imagePool.next();
        img.onload = function() {
          canvas.width = img.width
          canvas.height = img.height
          ctx.drawImage(img, 0, 0, img.width, img.height);
          self.resizeScreen(img);

          // Try to forcefully clean everything to get rid of memory
          // leaks. Note self despite this effort, Chrome will still
          // leak huge amounts of memory when the developer tools are
          // open, probably to save the resources for inspection. When
          // the developer tools are closed no memory is leaked.
          img.onload = img.onerror = null
          img.src = BLANK_IMG
          img = null
          blob = null

          URL.revokeObjectURL(url)
          url = null
        }

        img.onerror = function() {
          // Happily ignore. I suppose this shouldn't happen, but
          // sometimes it does, presumably when we're loading images
          // too quickly.

          // Do the same cleanup here as in onload.
          img.onload = img.onerror = null
          img.src = BLANK_IMG
          img = null
          blob = null

          URL.revokeObjectURL(url)
          url = null
        }
        var url = URL.createObjectURL(blob)
        img.src = url;
      }

      ws.onclose = function(ev) {
        console.log("screen websocket closed")
      }
    },
    codeRunDebug: function(code) {
      var fullCode = ['# coding: utf-8', 'import atx', 'd = atx.connect()', code].join('\n');
      return this.codeRun(fullCode);
    },
    codeRun: function(code) {
      var dtd = $.Deferred();
      this.console.content = '';
      var ws = new WebSocket('ws://localhost:17310/ws/v1/build')
      this.wsBuild = ws;
      ws.onclose = function() {
        console.log("ws closed");
        this.codeRunning = false;
      }.bind(this);
      ws.onmessage = function(ret) {
        var j = JSON.parse(ret.data);
        this.console.content += (j.buffer || "");
        if (j.result) {
          ws.close()
          if (!/\n$/.test(this.console.content)) {
            this.console.content += '\n';
          }
          if (j.result.exitCode == 0) {
            this.console.content += '[Finished in ' + j.result.duration / 1000 + 's]'
            dtd.resolve();
          } else {
            this.console.content += '[Finished in ' + j.result.duration / 1000 + 's with exit ' + j.result.exitCode + ']'
            dtd.reject()
          }
        }
      }.bind(this);
      ws.onopen = function() {
        console.log("ready to send")
        this.codeRunning = true;
        ws.send(JSON.stringify({
          content: code,
          deviceUrl: this.deviceUrl,
        }))
      }.bind(this)
      return dtd;
    },
    codeStopRun: function() {
      this.wsBuild && this.wsBuild.send('"stop"'); // any code can stop it
    },
    codeInsertPrepare: function(line) {
      if (/if $/.test(line)) {
        return;
      }
      if (/if$/.test(line)) {
        this.editor.insert(' ');
        return;
      }
      if (line.trimLeft()) {
        // editor.session.getLine(editor.getCursorPosition().row)
        var indent = editor.session.getMode().getNextLineIndent("start", line, "    ");
        this.editor.navigateLineEnd();
        this.editor.insert("\n" + indent); // BUG(ssx): It does't work the first time.
        return;
      }
    },
    codeInsert: function(code) {
      var editor = this.editor;
      var currentLine = editor.session.getLine(editor.getCursorPosition().row);
      this.codeInsertPrepare(currentLine);
      editor.insert(code);
    },
    getNodeIndex: function(id, kvs) {
      var skip = false;
      return this.nodes.filter(function(node) {
        if (skip) {
          return false;
        }
        var ok = kvs.every(function(kv) {
          var k = kv[0],
            v = kv[1];
          return node[k] == v;
        })
        if (ok && id == node.id) {
          skip = true;
        }
        return ok;
      }).length - 1;
    },
    generatePythonCode: function(code) {
      return ['# coding: utf-8', 'import atx', 'd = atx.connect()', code].join('\n');
    },
    doSendKeys: function(text) {
      // self.codeInsert()
      if (!text) {
        text = window.prompt("Input text?")
      }
      if (!text) {
        return;
      }
      var code = 'd.type("' + text + '")'
      this.loading = true;
      this.codeRun(this.generatePythonCode(code))
        .then(this.screenDumpUI)
        .then(function() {
          return this.codeInsert(code);
        }.bind(this))
    },
    doClear: function() {
      var code = 'd.clear_text()'
      this.codeRun(this.generatePythonCode(code))
        .then(this.screenDumpUI)
        .then(function() {
          return this.codeInsert(code);
        }.bind(this))
    },
    codeGenNodeSelector: function(node) {
      var self = this;

      function combineKeyValue(key, value) {
        return key + '=' + '"' + value + '"';
      }
      var index = 0;
      var params = [];
      var kvs = [];
      // iOS: name, label, className
      // Android: text, description, resourceId, className
      ['label', 'name', 'text', 'description', 'resourceId', 'className'].some(function(key) {
        if (!node[key]) {
          return false;
        }
        params.push(combineKeyValue(key, node[key]));
        kvs.push([key, node[key]]);
        index = self.getNodeIndex(node.id, kvs);
        return self.codeShortFlag && index == 0;
      });
      if (index > 0) {
        params.push('instance=' + index);
      }
      return 'd(' + params.join(', ') + ')';
    },
    codeInsertNode: function(node) {
      var self = this;
      var code = this.codeGenNodeSelector(node);
      // FIXME(ssx): put into a standalone function
      code += ".click()"
      self.codeInsert(code);

      this.loading = true;
      this.codeRun(this.generatePythonCode(code))
        .then(function() {
          self.screenDumpUI();
        })
        .fail(function() {
          self.loading = false;
        })
    },
    drawNode: function(node, color, dashed) {
      if (!node) {
        return;
      }
      var x = node.bounds[0],
        y = node.bounds[1],
        w = node.bounds[2] - x,
        h = node.bounds[3] - y;
      color = color || 'black';
      var ctx = this.canvas.fg.getContext('2d');
      var rectangle = new Path2D();
      rectangle.rect(x, y, w, h);
      if (dashed) {
        ctx.lineWidth = 1;
        ctx.setLineDash([8, 10]);
      } else {
        ctx.lineWidth = 5;
        ctx.setLineDash([]);
      }
      ctx.strokeStyle = color;
      ctx.stroke(rectangle);
    },
    drawAllNode: function() {
      var self = this;
      var canvas = self.canvas.fg;
      var ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      self.nodes.forEach(function(node) {
        self.drawNode(node, 'black', true);
      })
    },
    drawHoverNode: function(pos) {
      var self = this;
      var canvas = self.canvas.fg;
      self.nodeHovered = null;
      var minArea = Infinity;

      function isInside(node, x, y) {
        var lx = node.bounds[0],
          ly = node.bounds[1],
          rx = node.bounds[2],
          ry = node.bounds[3];
        return lx < x && x < rx && ly < y && y < ry;
      }
      var activeNodes = self.nodes.filter(function(node) {
        if (!isInside(node, pos.x, pos.y)) {
          return false;
        }
        var bs = node.bounds;
        var area = (bs[2] - bs[0]) * (bs[3] - bs[1]);
        if (area < minArea) {
          minArea = area;
          self.nodeHovered = node;
        }
        return true;
      })
      activeNodes.forEach(function(node) {
        self.drawNode(node, "blue")
      })
      self.drawNode(self.nodeHovered, "green");
    },
    activeMouseControl: function() {
      var self = this;
      var element = this.canvas.fg;

      var screen = {
        bounds: {}
      }

      function calculateBounds() {
        var el = element;
        screen.bounds.w = el.offsetWidth
        screen.bounds.h = el.offsetHeight
        screen.bounds.x = 0
        screen.bounds.y = 0

        while (el.offsetParent) {
          screen.bounds.x += el.offsetLeft
          screen.bounds.y += el.offsetTop
          el = el.offsetParent
        }
      }

      function activeFinger(index, x, y, pressure) {
        var scale = 0.5 + pressure
        $(".finger-" + index)
          .addClass("active")
          .css("transform", 'translate3d(' + x + 'px,' + y + 'px,0)')
      }

      function deactiveFinger(index) {
        $(".finger-" + index).removeClass("active")
      }

      function mouseMoveListener(event) {
        var e = event
        if (e.originalEvent) {
          e = e.originalEvent
        }
        // Skip secondary click
        if (e.which === 3) {
          return
        }
        e.preventDefault()

        var x = e.pageX - screen.bounds.x
        var y = e.pageY - screen.bounds.y
        var pressure = 0.5
        activeFinger(0, e.pageX, e.pageY, pressure);
        // that.touchMove(0, x / screen.bounds.w, y / screen.bounds.h, pressure);
      }

      function mouseUpListener(event) {
        var e = event
        if (e.originalEvent) {
          e = e.originalEvent
        }
        // Skip secondary click
        if (e.which === 3) {
          return
        }
        e.preventDefault()

        // that.touchUp(0);
        stopMousing()
      }

      function stopMousing() {
        element.removeEventListener('mousemove', mouseMoveListener);
        element.addEventListener('mousemove', mouseHoverListener);
        document.removeEventListener('mouseup', mouseUpListener);
        deactiveFinger(0);
      }

      function mouseDownListener(event) {
        var e = event;
        if (e.originalEvent) {
          e = e.originalEvent
        }
        // Skip secondary click
        if (e.which === 3) {
          return
        }
        e.preventDefault()

        fakePinch = e.altKey
        calculateBounds()
          // startMousing()

        var x = e.pageX - screen.bounds.x
        var y = e.pageY - screen.bounds.y
        var pressure = 0.5
        activeFinger(0, e.pageX, e.pageY, pressure);

        if (self.nodeHovered) {
          self.nodeSelected = self.nodeHovered;
          self.drawAllNode()
            // self.drawHoverNode(pos);
          self.drawNode(self.nodeSelected, "red");
          self.debugCode = self.codeGenNodeSelector(self.nodeSelected);
        }
        // self.touchDown(0, x / screen.bounds.w, y / screen.bounds.h, pressure);

        element.removeEventListener('mousemove', mouseHoverListener);
        element.addEventListener('mousemove', mouseMoveListener);
        document.addEventListener('mouseup', mouseUpListener);
      }

      function coord(event) {
        var e = event;
        if (e.originalEvent) {
          e = e.originalEvent
        }
        calculateBounds()
        var x = e.pageX - screen.bounds.x
        var y = e.pageY - screen.bounds.y
        return {
          x: Math.floor(x / screen.bounds.w * element.width),
          y: Math.floor(y / screen.bounds.h * element.height),
        }
      }

      function mouseHoverListener(event) {
        var e = event;
        if (e.originalEvent) {
          e = e.originalEvent
        }
        // Skip secondary click
        if (e.which === 3) {
          return
        }
        e.preventDefault()
          // startMousing()

        var x = e.pageX - screen.bounds.x
        var y = e.pageY - screen.bounds.y
        var pos = coord(event);

        self.drawAllNode()
        self.drawHoverNode(pos);
        if (self.nodeSelected) {
          self.drawNode(self.nodeSelected, "red");
        }
      }

      /* bind listeners */
      element.addEventListener('mousedown', mouseDownListener);
      element.addEventListener('mousemove', mouseHoverListener);
    }
  }
})