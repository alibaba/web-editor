// Copies a string to the clipboard. Must be called from within an
// event handler such as click. May return false if it failed, but
// this is not always possible. Browser support for Chrome 43+,
// Firefox 42+, Safari 10+, Edge and IE 10+.
// IE: The clipboard feature may be disabled by an administrator. By
// default a prompt is shown the first time the clipboard is
// used (per session).
function copyToClipboard(text) {
  if (window.clipboardData && window.clipboardData.setData) {
    // IE specific code path to prevent textarea being shown while dialog is visible.
    return clipboardData.setData("Text", text);

  } else if (document.queryCommandSupported && document.queryCommandSupported("copy")) {
    var textarea = document.createElement("textarea");
    textarea.textContent = text;
    textarea.style.position = "fixed"; // Prevent scrolling to bottom of page in MS Edge.
    document.body.appendChild(textarea);
    textarea.select();
    try {
      return document.execCommand("copy"); // Security exception may be thrown by some browsers.
    } catch (ex) {
      console.warn("Copy to clipboard failed.", ex);
      return false;
    } finally {
      document.body.removeChild(textarea);
    }
  }
}

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

// convert to blob data
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

var dumplib = {
  parseIosJson: function(json, screenshotWidth) {
    var node = JSON.parse(json);
    // get 414, 736 from {{0, 0}, {414, 736}}
    var windowSize = /\{\{(.+)\}, \{(.+)\}\}/.exec(node.frame)[2].split(',').map(v => parseInt(v, 10))
    var scale = screenshotWidth ? screenshotWidth / windowSize[0] : 1

    function travel(node) {
      node['_id'] = node['_id'] || uuidv4();
      node['_type'] = node['type'] || null;
      if (node['rect']) {
        let rect = node['rect'];
        let nrect = {};
        for (let k in rect) {
          nrect[k] = rect[k] * scale;
        }
        node['rect'] = nrect;
      }

      if (node['children']) {
        node['children'].forEach(child => {
          travel(child);
        });
      }
      return node;
    }

    return {
      jsonHierarchy: travel(node),
      windowSize
    }
  },
  parseAndroidJson: function(json) {

  }
}