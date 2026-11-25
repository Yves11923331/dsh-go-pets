#!/usr/bin/env python3
"""生成带符号的透明表情图（符号由模型画，与人物同一画风）。

输出：symbols/<name>.png
"""
import base64
import json
import pathlib
import sys
import time
import urllib.request
import uuid

REF = pathlib.Path('/root/workspace/maid-pet-test/ref/ref.jpg')
OUT = pathlib.Path('/root/workspace/maid-pet-test/symbols')
CFG = json.loads(pathlib.Path('/root/.dsh/skills/imagegen/config.json').read_text())
G = CFG.get('gpt') or {}
KEY = G.get('api_key')
BASE = (G.get('base_url') or 'https://zdxjl.com').rstrip('/')

COMMON = (
    "保持参考图中同一角色全部细节与构图：深蓝色长卷发、蓝宝石色眼睛、白灰色蕾丝女仆头饰、"
    "两侧蓝色小蝴蝶结、白色羽翼状发饰、白色蕾丝衣领、深蓝领结与金边蓝宝石胸针。"
    "同一张半身胸像、相同位置大小和视角。背景换成完全透明的 alpha 通道，人物之外没有任何颜色，"
    "发丝、白色羽翼与白色蕾丝边缘干净完整。人物表情："
)

ITEMS = {
    'working1': ("眉头微微下压，眼睛专注地盯着前方，嘴唇抿成一条平线，认真干活。"
                 "在人物右侧的空白处漂浮着四五个发光的白色代码符号「{ }」「</>」「#」，"
                 "半透明浅蓝色辉光，像漂浮的代码碎片，与人物同一动漫画风。"),
    'working2': ("眉头微微下压，眼睛专注地盯着前方，嘴唇抿成一条平线，认真干活。"
                 "在人物右侧漂浮着发光的白色代码符号「01」「;」「=>」，半透明浅蓝辉光，"
                 "像漂浮的代码碎片，与人物同一动漫画风。"),
    'thinking': ("眉毛微皱，眼神飘向右上方，嘴唇轻抿，若有所思。"
                 "头顶右上方漂浮着三个发光的白色省略号「…」，半透明浅蓝辉光，与人物同一画风。"),
    'error': ("眉毛呈八字形下垂，嘴角向下撇，眼神失焦发蔫，委屈又沮丧。"
              "脸颊旁有一滴蓝色的动漫汗滴，头顶右上方有一个发光的白色感叹号，与人物同一画风。"),
    'done': ("眼睛笑成弯弯的，嘴角明显上扬，下巴微微抬起，得意又开心。"
             "头顶周围有两三颗发光的白色四角星星闪光，浅蓝辉光，与人物同一画风。"),
    'notification': ("眼睛睁大发亮，视线看向右上方，嘴巴微张，像在期待什么。"
                     "头顶右上方有一个发光的白色感叹号，浅蓝辉光，与人物同一画风。"),
    'sleep': ("双眼闭合，嘴唇微微张开，面部放松，睡得很沉。"
              "头顶右上方漂浮着三个由小到大的白色字母「Z」，浅蓝辉光，与人物同一画风。"),
    'tap': ("双眼瞪大，眉头上扬，嘴巴张开，惊讶。"
            "脸颊旁有一滴蓝色动漫汗滴，头顶右上方有一个发光的白色感叹号，与人物同一画风。"),
    'praise': ("眼睛笑成弯弯的，嘴角上扬，得意开心。"
               "头顶周围有两颗发光的白色四角星，浅蓝辉光，与人物同一画风。"),
    'tickle': ("抿着嘴憋笑，眼睛弯起来，脸颊鼓起。"
               "头顶周围漂浮着两个发光的白色音符「♪」，浅蓝辉光，与人物同一画风。"),
    'annoyed': ("眉头紧皱、眼神不耐烦地斜视、嘴角明显下撇，一脸不爽。"
                "头顶右上方有一个红色漫画怒气符号（十字青筋），与人物同一画风。"),
    'drag': ("双眼瞪大，眉头上扬，嘴巴张开，慌张又无奈。"
             "脸颊两侧各有一滴蓝色的动漫汗滴，与人物同一画风。"),
    'sweeping': ("眉头微压，眼神认真，嘴唇抿平，像在用力清理。"
                 "人物右侧有一个小小的白色半透明旋风符号，与人物同一画风。"),
    'carrying': ("眉头微压，嘴唇抿紧，像在用力搬东西。"
                 "画面下方有一个小小的浅棕色包裹符号，白色十字胶带，与人物同一画风。"),
    'juggling': ("眼睛睁大，视线左右游移，有点手忙脚乱。"
                 "头顶周围有三颗小星星在绕圈，浅蓝辉光，与人物同一画风。"),
    'pout': ("脸颊鼓起，嘴角向下撇，眼神向旁边飘，赌气撅嘴。"
             "头顶右上方漂浮着三个白色省略号「…」，浅蓝辉光，与人物同一画风。"),
    'waking': ("眼皮半睁，眼神迷迷糊糊，嘴角松垮，刚睡醒。"
               "头顶右上方有一个小小的浅黄色太阳符号，与人物同一画风。"),
}


def gen(name, desc):
    body = {"model": "gpt-image-2.6-flare", "prompt": COMMON + desc, "n": 1,
            "size": "1024x1024", "quality": "high", "background": "transparent"}
    boundary = "----t" + uuid.uuid4().hex
    outb = b""
    for k, v in body.items():
        outb += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    outb += (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="ref.jpg"\r\n'
             f'Content-Type: image/jpeg\r\n\r\n').encode() + REF.read_bytes() + b"\r\n"
    outb += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + "/v1/images/edits", data=outb,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(d['data'][0]['b64_json']))
    print(f"{name} {time.time()-t0:.0f}s", flush=True)


if __name__ == '__main__':
    todo = list(ITEMS.items())
    only = sys.argv[1:]
    if only:
        todo = [(k, v) for k, v in todo if k in only]
    for name, desc in todo:
        for attempt in range(2):
            try:
                gen(name, desc)
                break
            except Exception as e:
                print(f"{name} 失败({attempt+1}): {e}", flush=True)
                time.sleep(5)
