# coding: utf-8

import re
import xml.dom.minidom

sample_android_page_xml = '''<?xml version="1.0" ?>
<hierarchy rotation="0">
  <node bounds="[0,0][720,1280]" checkable="false" checked="false" class="android.widget.FrameLayout" clickable="false" content-desc="" enabled="true" focusable="false" focused="false" index="0" long-clickable="false" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text="">
    <node bounds="[0,0][720,1280]" checkable="false" checked="false" class="android.view.View" clickable="false" content-desc="第 1 屏，共 4 屏" enabled="true" focusable="false" focused="false" index="0" long-clickable="false" package="com.huawei.android.launcher" password="false" resource-id="com.huawei.android.launcher:id/workspace" scrollable="true" selected="false" text="">
      <node bounds="[0,0][720,1110]" checkable="false" checked="false" class="android.view.View" clickable="true" content-desc="" enabled="true" focusable="false" focused="false" index="0" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="com.huawei.android.launcher:id/workspace_screen" scrollable="false" selected="false" text="">
        <node bounds="[8,66][184,270]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="" enabled="true" focusable="true" focused="false" index="1" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text="梦幻西游"/>
        <node bounds="[184,66][360,270]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="" enabled="true" focusable="true" focused="false" index="2" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text="梦幻西游"/>
        <node bounds="[360,66][536,270]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="" enabled="true" focusable="true" focused="false" index="3" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text="梦幻西游"/>
      </node>
    </node>
    <node NAF="true" bounds="[0,1083][720,1155]" checkable="false" checked="false" class="android.widget.ImageView" clickable="true" content-desc="" enabled="true" focusable="true" focused="false" index="1" long-clickable="false" package="com.huawei.android.launcher" password="false" resource-id="com.huawei.android.launcher:id/dock_divider" scrollable="false" selected="false" text=""/>
    <node bounds="[0,1110][720,1280]" checkable="false" checked="false" class="android.widget.FrameLayout" clickable="false" content-desc="" enabled="true" focusable="false" focused="false" index="2" long-clickable="false" package="com.huawei.android.launcher" password="false" resource-id="com.huawei.android.launcher:id/hotseat" scrollable="false" selected="false" text="">
      <node bounds="[16,1110][176,1280]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="拨号" enabled="true" focusable="true" focused="false" index="0" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text=""/>
      <node bounds="[192,1110][352,1280]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="联系人" enabled="true" focusable="true" focused="false" index="1" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text=""/>
      <node bounds="[368,1110][528,1280]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="信息" enabled="true" focusable="true" focused="false" index="2" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text=""/>
      <node bounds="[544,1110][704,1280]" checkable="false" checked="false" class="android.widget.TextView" clickable="true" content-desc="浏览器" enabled="true" focusable="true" focused="false" index="3" long-clickable="true" package="com.huawei.android.launcher" password="false" resource-id="" scrollable="false" selected="false" text=""/>
      <node NAF="true" bounds="[0,1110][720,1280]" checkable="false" checked="false" class="android.widget.ImageView" clickable="true" content-desc="" enabled="true" focusable="true" focused="false" index="4" long-clickable="false" package="com.huawei.android.launcher" password="false" resource-id="com.huawei.android.launcher:id/bg_dock" scrollable="false" selected="false" text=""/>
    </node>
  </node>
</hierarchy>
'''

def parse_bounds(text):
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', text)
    if m is None:
        return None
    return m.groups()

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def str2int(v):
    return int(v)

def convstr(v):
    return v
    # return v.encode('utf-8')

__alias = {
    'class': 'className',
    'resource-id': 'resourceId',
    'content-desc': 'description',
    'long-clickable': 'longClickable',
}

__parsers = {
    # Android
    'bounds': parse_bounds,
    'text': convstr,
    'className': convstr,
    'resourceId': convstr,
    'package': convstr,
    'checkable': str2bool,
    'scrollable': str2bool,
    'focused': str2bool,
    'clickable': str2bool,
    'selected': str2bool,
    'longClickable': str2bool,
    'focusable': str2bool,
    'password': str2bool,
    'index': int,
    'description': convstr,
    # iOS
    'name': convstr,
    'label': convstr,
    'x': str2int,
    'y': str2int,
    'width': str2int,
    'height': str2int,
    # iOS && Android
    'enabled': str2bool,
}

def parse_node(node):
    ks = {}
    for key, value in node.attributes.items():
        key = __alias.get(key, key)
        f = __parsers.get(key)
        if value is None:
            ks[key] = None
        elif f:
            ks[key] = f(value)
    return ks

def node2json(node, scale):
    ret = {}
    for (k, v) in node.attributes.items():
        ret[k] = v
    x, y, w, h = map(int, (ret['x'], ret['y'], ret['width'], ret['height']))
    ret['bounds'] = map(lambda x: x*scale, [x, y, x+w, y+h])
    ret['className'] = ret['type'][len('XCUIElementType'):]
    return ret

def travel_dom(root, scale, result=[]):
    # print root.nodeName
    for node in root.childNodes:
        if not node.nodeName.startswith('XCUIElementType'):
            continue
        result.append(node2json(node, scale))
        travel_dom(node, scale, result)
    return result

        
def get_uiview(d):
    is_android = d.platform == 'android'
    if is_android:
        page_xml = d.dump(compressed=False, pretty=False).encode('utf-8')
    else:
        page_xml = d.dump_view().encode('utf-8')

    # page_xml = sample_android_page_xml
    with open('debug.xml', 'wb') as f:
        f.write(page_xml)
        
    dom = xml.dom.minidom.parseString(page_xml)
    root = dom.documentElement

    ui_nodes = []
    if is_android:
        nodes = root.getElementsByTagName('node')
        n = 0
        for node in nodes:
            json_node = parse_node(node)
            json_node['id'] = n
            n += 1
            ui_nodes.append(json_node)
    else:
        ui_nodes = travel_dom(root, d.scale, [])
        for (idx, un) in enumerate(ui_nodes):
            un['id'] = idx
    return ui_nodes
