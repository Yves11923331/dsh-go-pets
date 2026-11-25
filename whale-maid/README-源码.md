# 嫌弃の鲸鱼女仆 · 源码归档

宠物包画布 **200 × 200**，id `whale-maid`，21 个动画。
成品在 `out-whale-maid/whale-maid.zip`。

## 目录

```
gen_faces.py      生成 12 张透明表情（gpt-image-2.6-flare，同构图只改脸）
gen_symbols.py    生成 17 张带符号表情（代码符号/汗滴/怒气/Zzz/星星…由模型画）
build_all.py      表情帧 -> 状态 GIF（呼吸/眨眼/抖动），输出 gifs/ 和 pack-src/
pack.py           调转换器打包 + 补 timings/bonus + 校验 + 打 zip
scripts-200canvas/  官方 pet-theme 脚本副本，只把 SMOOTH_CANVAS 改成 200
trans/            透明表情（17 张）
symbols/          带符号表情（17 张）
gifs/             21 个状态 GIF
ref/ref.jpg       角色参考图
out-whale-maid/   成品包（pack.json + 精灵表 + zip）
```

## 重建

```sh
pip install Pillow numpy
python3 gen_faces.py        # 需要 imagegen 技能的 config.json
python3 gen_symbols.py
python3 build_all.py
python3 pack.py             # 200 画布打包，需要 scripts-200canvas/
```

`pack.py` 会优先用同目录的 `scripts-200canvas/`，不存在时退回 `/tmp/scripts200`。

## 命名坑

转换器按文件名匹配状态：`done`→attention、`walk`→roam、`sleep`→sleeping、`praise`→tapRight、`tap`→tapLeft；`yawn/pout/gaze/smile` 进待机小剧场。
