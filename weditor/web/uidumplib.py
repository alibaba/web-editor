# coding: utf-8

import re
import xml.dom.minidom
import uuid

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
    (lx, ly, rx, ry) = map(int, m.groups())
    return dict(x=lx, y=ly, width=rx - lx, height=ry - ly)


def safe_xmlstr(s):
    return s.replace("$", "-")


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def str2int(v):
    return int(v)


def convstr(v):
    return v


__alias = {
    'class': '_type',
    'resource-id': 'resourceId',
    'content-desc': 'description',
    'long-clickable': 'longClickable',
    'bounds': 'rect',
}

__parsers = {
    '_type': safe_xmlstr, # node className
    # Android
    'rect': parse_bounds,
    'text': convstr,
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


def _parse_uiautomator_node(node):
    ks = {}
    for key, value in node.attributes.items():
        key = __alias.get(key, key)
        f = __parsers.get(key)
        if value is None:
            ks[key] = None
        elif f:
            ks[key] = f(value)
    if 'bounds' in ks:
        lx, ly, rx, ry = map(int, ks.pop('bounds'))
        ks['rect'] = dict(x=lx, y=ly, width=rx - lx, height=ry - ly)
    return ks


def get_android_hierarchy(d):
    page_xml = d.dump_hierarchy(compressed=False, pretty=False).encode('utf-8')
    return android_hierarchy_to_json(page_xml)


def android_hierarchy_to_json(page_xml: bytes):
    """
    Returns:
        JSON object
    """
    dom = xml.dom.minidom.parseString(page_xml)
    root = dom.documentElement

    def travel(node):
        """ return current node info """
        if node.attributes is None:
            return
        json_node = _parse_uiautomator_node(node)
        json_node['_id'] = str(uuid.uuid4())
        if node.childNodes:
            children = []
            for n in node.childNodes:
                child = travel(n)
                if child:
                    # child["_parent"] = json_node["_id"]
                    children.append(child)
            json_node['children'] = children
        return json_node

    return travel(root)


def get_ios_hierarchy(d, scale):
    sourcejson = d.source(format='json')

    def travel(node):
        node['_id'] = str(uuid.uuid4())
        node['_type'] = node.pop('type', "null")
        if node.get('rect'):
            rect = node['rect']
            nrect = {}
            for k, v in rect.items():
                nrect[k] = v * scale
            node['rect'] = nrect

        for child in node.get('children', []):
            travel(child)
        return node

    return travel(sourcejson)


def get_webview_hierarchy(d):
    pass