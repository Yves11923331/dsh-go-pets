# 顽皮的Gemini · 源码归档

宠物包画布 **200 × 200**，id `naughty-gemini`，25 个动画。
成品：`out-naughty-gemini/naughty-gemini.zip`

## 目录

```
gen2.py            生成 26 张透明表情/动作（gpt-image-2.6-flare，同角色改表情）
                   干活两张 work1/work2 含笔记本与键盘
build2.py          表情 -> 状态 GIF，输出 gifs/ 和 pack-src/（工作帧放大 1.18 对齐人物）
pack2.py           打包 + timings/bonus + 校验 + zip
scripts-200canvas/ 官方 pet-theme 脚本副本，SMOOTH_CANVAS 改成 200
trans/             透明表情（26 张）
gifs/              25 个状态 GIF（400 画布）
out-naughty-gemini/ 成品包
ref/ref.jpg        角色参考图
```

## 重建

```sh
pip install Pillow numpy
python3 gen2.py
python3 build2.py
python3 pack2.py
```

## 设计要点

- 基准构图 400 画布（人物 360 + 20 边距），转换到 200 画布
- 干活帧 work 比其它帧人物小，build2.py 用 zoom_bottom 放大 1.18 对齐
- 命名：`done`→attention、`walk`→roam、`sleep`→sleeping、`praise`→tapRight、`tap`→tapLeft；`happy/pout/yawn/gaze` 进待机小剧场
- 完成：`done2` 姿势（双手比耶 + 大星星）做蓄力/起跳/滞空/落地/停住；`cheer2` 是长大版彩蛋（成年立绘，透明背景），30% 概率替换完成
- 分档：`working2` / `juggling2` 进 `tiers`，按子代理数切换；`tickle2` 由 tickle 压扁（笑到弯腰），连点摸头进第二段
