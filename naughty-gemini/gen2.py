#!/usr/bin/env python3
"""顽皮的Gemini：透明表情/动作差分生成（gpt-image-2.6-flare）。

用法：python3 gen2.py [名字…]
"""
import base64
import json
import pathlib
import sys
import time
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).parent
REF = ROOT / 'ref' / 'ref.jpg'
CFG = json.loads(pathlib.Path('/root/.dsh/skills/imagegen/config.json').read_text())
G = CFG.get('gpt') or {}
KEY, BASE = G.get('api_key'), (G.get('base_url') or 'https://zdxjl.com').rstrip('/')

STYLE = (
    "保持参考图中同一个Q版猫耳少女的全部设定：紫蓝色大波浪长发、发梢粉色渐变、一对猫耳（内耳粉白色）、"
    "头顶紫色呆毛、一侧有金色描边的彩色大星星发饰与一颗小星星、异色瞳（一只粉色眼睛、一只琥珀金色眼睛）、"
    "脸颊斜线腮红、深紫蓝色露肩上衣、胸前星星吊坠、手腕星星手链、厚涂卡通画风、明快配色。"
    "同一张半身胸像、相同位置大小和视角。背景换成完全透明的 alpha 通道，人物之外没有任何颜色，"
    "发丝和衣服边缘干净完整。"
)

ITEMS = {
    # 基础表情（无符号）
    'neutral': STYLE + "表情：安静地睁着眼，嘴角带一点笑意，像随时要闹起来。",
    'closed': STYLE + "表情：双眼轻轻闭合，睫毛可见，嘴角上扬，闭着眼也在笑。",
    'surprised': STYLE + "表情：双眼瞪圆，眉毛扬起，嘴巴张成惊讶的圆形，像被吓了一跳。",
    'happy': STYLE + "表情：眼睛笑成弯弯的月牙，嘴巴张大开心地笑，脸颊更红。",
    # 干活：电脑/键盘
    'work1': STYLE + "表情：专注地盯着屏幕，嘴角抿着，有点认真。画面下方有一台打开的迷你笔记本电脑，"
             "屏幕发出蓝紫色光，双手放在键盘上敲击，身体微微前倾。",
    'work2': STYLE + "表情：盯着屏幕眼睛发亮，嘴角翘起，敲得更起劲。画面下方是打开的迷你笔记本电脑，"
             "屏幕发光，双手在键盘上，旁边漂浮着几个发光的代码符号「{ }」「</>」「#」。",
    # 带符号
    'thinking': STYLE + "表情：歪着头，眼睛往上看，手指点着下巴，若有所思。头顶右侧漂浮三个发光的白色省略号「…」。",
    'error': STYLE + "表情：八字眉，嘴角向下撇，眼睛发蔫。脸颊旁有一滴蓝色汗滴，头顶右侧一个发光感叹号。",
    'done': STYLE + "表情：眼睛笑成月牙，开心得跳起来。头顶周围有两三颗发光的四角星星。",
    'notification': STYLE + "表情：眼睛睁大发亮，看向右上方，嘴巴微张期待。头顶右上方一个发光感叹号。",
    'sleep': STYLE + "表情：闭着眼，嘴巴微张，睡得很香。头顶右上方漂浮三个由小到大的白色字母「Z」。",
    'waking': STYLE + "表情：眼皮半睁，迷糊，头发有点乱。头顶右上方一个浅黄色小太阳。",
    'tap': STYLE + "表情：被戳到，双眼瞪大，嘴巴张开，然后鼓脸。脸颊旁一滴蓝色汗滴，头顶一个感叹号。",
    'praise': STYLE + "表情：得意地笑，眼睛弯弯，下巴微抬。头顶周围两颗发光四角星。",
    'tickle': STYLE + "表情：憋笑，抿着嘴，眼睛弯起来，肩膀缩着。头顶周围两个发光音符「♪」。",
    'annoyed': STYLE + "表情：鼓着脸，眉毛拧起，嘴角下撇。头顶右上方一个红色漫画怒气符号（十字青筋）。",
    'drag': STYLE + "表情：被拎起来，四肢僵住，眼睛瞪大，慌张。两侧各有一滴蓝色汗滴。",
    'walk': STYLE + "表情：身体前倾，像在跑，一只脚迈出去，头发和裙摆被风吹起，速度线在身后。嘴巴张开笑着。",
    'pout': STYLE + "表情：鼓起腮帮子，嘴角下撇，眼神飘向一边，赌气。头顶右侧三个白色省略号。",
    'yawn': STYLE + "表情：闭着眼，嘴巴张得很大打哈欠，眼角有点泪花。",
    'gaze': STYLE + "表情：眼珠转向一侧，眉毛放松，好奇地张望，嘴角带笑。",
    'juggling': STYLE + "表情：有点手忙脚乱，眼睛左右看，但笑得很开心。头顶周围三颗小星星在绕圈。",
    'carrying': STYLE + "表情：抱着东西用力，抿着嘴，脸鼓起来。画面下方有一个小包裹。",
    'sweeping': STYLE + "表情：认真又用力的样子，抿嘴。身体旁有一道白色半透明小旋风。",
}


def gen(name, desc):
    body = {"model": "gpt-image-2.6-flare", "prompt": desc, "n": 1,
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
    out = ROOT / 'trans' / f'{name}.png'
    out.write_bytes(base64.b64decode(d['data'][0]['b64_json']))
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
