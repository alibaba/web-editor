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
  this.size = size;
  this.images = [];
  this.counter = 0
}

ImagePool.prototype.next = function() {
  if (this.images.length < this.size) {
    var image = new Image();
    this.images.push(image);
    return image
  } else {
    if (this.counter >= this.size) {
      // Reset for unlikely but theoretically possible overflow.
      this.counter = 0
    }
  }

  return this.images[this.counter++ % this.size]
};

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

var MiniTouch = {
  createNew: function(ws) {
      // ws: Websocket connection communication with minitouch
    var control = {};

    function sendJSON(obj) {
        ws.send(JSON.stringify(obj))
    }

    control.touchDown = function(index, xP, yP, pressure) {
        sendJSON({
            operation: 'd',
            index: index,
            pressure: pressure,
            xP: xP,
            yP: yP,
        })
    };

    control.touchWait = function(mseconds) {
        sendJSON({ operation: 'w', milliseconds: mseconds })
    };

    control.touchCommit = function() {
        sendJSON({ operation: 'c' })
    };

    control.touchMove = function(index, xP, yP, pressure) {
        sendJSON({
            operation: 'm',
            index: index,
            pressure: pressure,
            xP: xP,
            yP: yP,
        })
    };

    control.touchUp = function(index) {
        sendJSON({ operation: 'u', index: index })
    };

    return control;
  }
};
function coords(boundingW, boundingH, relX, relY, rotation) {
  var w, h, x, y;

  switch (rotation) {
    case 0:
        w = boundingW;
        h = boundingH;
        x = relX;
        y = relY;
        break;
    case 90:
        w = boundingH;
        h = boundingW;
        x = boundingH - relY;
        y = relX;
        break;
    case 180:
        w = boundingW;
        h = boundingH;
        x = boundingW - relX;
        y = boundingH - relY;
        break;
    case 270:
        w = boundingH;
        h = boundingW;
        x = relY;
        y = boundingW - relX;
        break
  }

  return {
    xP: x / w,
    yP: y / h,
  }
}