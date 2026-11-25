# 像素宠物制作管线（dsh-go）

做一只新宠物的完整流程。按顺序执行，每步都有验收点。

## 0. 目录与依赖

```sh
mkdir -p ~/workspace/<pet>/assets/poses ~/workspace/<pet>/assets/future
cp ~/workspace/xiadie/build.py ~/workspace/xiadie/pack_build.py ~/workspace/<pet>/
```

- 参考工程：`/root/workspace/xiadie/`（遐蝶，22 动画，可整份对照）
- 依赖：Pillow、numpy（已装）；生图用 `imagegen` 技能
- 校验器：`~/.dsh/skills/pet-theme/scripts/pet_pack_check.py`
- 打包底层：`~/.dsh/skills/pet-theme/scripts/make_pet_pack.py`（提供 `write_anim` / `measure` / `hit_boxes`）

## 1. 角色设定与姿势图

生图统一走 GPT 通道（构图和一致性最稳）：

```sh
python3 ~/.dsh/skills/imagegen/scripts/gen.py "<提示词>" \
  --provider gpt --model gpt-image-2.6-flare \
  --ref <设定图> [--ref <另一张参考>] \
  --size 1024x1536 --n 2 --background transparent \
  --out ~/workspace/<pet>/poses-new
```

提示词骨架：

> 沿用参考图中同一个像素小人角色的全部设定：<发型/眼睛/耳朵/发饰/服装/鞋袜>；完全相同的配色、像素颗粒大小和硬边像素画风。姿势：<动作>。全身正面朝向观众，人物四周留白，背景完全透明 alpha，不要地面、不要文字。

- **每次 n=2**，从两张里挑构图最好的一张
- 走路单独出一张「横向 4 帧精灵图」，再切分，四帧尺度天然一致
- 道具（笔电、扫帚、纸箱、球、爱心）必须让模型画，不要手绘——手绘像素道具一定丑
- 挑完的图存成 `assets/poses/<pose>.png`，命名用英文短词（stand / think / work …）

验收：每张图都是真透明（RGBA，alpha 有 0 和 255）、人物完整、头顶不贴边。

## 2. 像素化与对齐

`build.py` 里的规则，不要改：

| 参数 | 值 | 说明 |
|---|---|---|
| 逻辑高 `H` | 160 | 站立帧 |
| 画布 | 113×170 | 所有帧统一，脚底基线对齐 |
| 下采样 | `Image.BOX` | 压到 160 高，保持硬边 |
| alpha | ≥110 → 255，否则 0 | crisp 通道要求只有 0/255 |
| 对齐 | 底部 6% 象素质心当身体中轴 | 长发摆动不影响 |

- `pixelize(path, h)`：裁 alpha bbox → BOX 缩放 → alpha 二值化
- `place(im, width, anchor)`：底部（站姿）或顶部（跳跃/悬空）对齐
- `shift` / `shift_x` / `halo`：整帧或局部平移，空出来的地方保持透明交给下层

验收：任意两个动画切换时，脚底在同一水平线，中轴不跳。

## 3. 动画表

12 个状态 + 5 个反应 + 待机小剧场，名字必须命中关键词（见第 6 节）。

在 `build.py` 的 `anims` 字典里定义：`{动画名: (帧列表, 每帧毫秒列表, 是否循环)}`。

常用帧构造：

```python
# 呼吸：整帧上下 1-2px
[shift(pose, dy) for dy in (0, -1, -2, -1)]
# 左右摆：整帧横移
[shift_x(pose, dx) for dx in (0, 1, 2, 1, 0, -1)]
# 眨眼：从待机帧序列里插入闭眼帧，闭眼帧 90ms
```

节奏建议（逐帧 ms，不要全用一个值）：

| 动画 | 帧数 | 时长风格 |
|---|---|---|
| idle | 16 | 呼吸 220，眨眼 90/90 |
| thinking | 8 | 260 匀速 |
| working | 8 | 100/70 交替，快 |
| done（完成） | 8 | 60/70/200/90，起跳-滞空-落地 |
| error | 8 | 90/280，一下一下耷拉 |
| tap（被戳） | 4 | 70/90/260/110 |
| walk | 4 | 130-140 |
| sleep | 2 | 700 |

循环标记：idle / thinking / working / error / walk 等要 loop；waking、完成、反应类是一次性。

验收：`frames/meta.json` 里每个动画的 durs 总数合理（待机 3 秒左右，反应 0.5 秒左右）。

## 4. 打包

**不要**用 `pet_theme_convert.py` 的逐帧模式（它会丢掉 bonus/timings，且固定 144 画布）。
用工程里的 `pack_build.py`，它复用官方 `make_pet_pack` 的精灵表写入与锚点测量，再补上：

- `bonus`：完成彩蛋（`{'attention': {'anims': ['cheer2'], 'chance': 0.3}}`）
- `timings`：`minDisplay`（error 1600 / notification 1800 / attention 1200）+ `autoReturn` + `wakeMs`

```sh
cd ~/workspace/<pet>
python3 build.py        # 生成 frames/ 和 preview/
python3 pack_build.py   # 生成 out/<id>/
python3 ~/.dsh/skills/pet-theme/scripts/pet_pack_check.py out/<id> --compat-reactions
```

**必须 PASS 才能交付。** 校验器镜像 App 的导入规则（schema、引用、sheet 尺寸、锚点、碰撞框）。

注意：`pack_build.py` 里的 `STATES` / `REACTIONS` / `IDLE_POOL` / `BONUS` / `TIMINGS` 要按新宠物改。

验收：`pack.json` 里 states 12 个都在、reactions 5 个、idlePool 有 3-4 个、canvas 是 113×170、`pixelArt: true`。

## 5. 交付

```sh
cd out/<id> && python3 -m zipfile -c /sdcard/Download/DSH-Go/<pet>/<id>.zip pack.json *.png
```

目录结构：

```
/sdcard/Download/DSH-Go/<pet>/
  <id>.zip          # 导入 & 投稿用
  总览.png          # 所有动画首帧，2x 放大，带中文标签
  previews/*.gif    # 每个动画一个，2x，按 durs 播放
  说明.md           # 动画清单、重建命令、命名坑
```

再复制一份到 `/sdcard/魔门-DSH/`（用户自己的归档习惯）。交付目录写 `.nomedia`，避免进相册。

导入：设置 → 宠物 → 导入 → 选 zip（同 id 覆盖旧包）。
投稿：创意工坊 → 我的投稿 → 投稿；选“自己导入的宠物”最稳，避免 zip 解析报 `pet_no_pack`。

## 6. 命名规则（踩过的坑）

转换/打包按**动画名**匹配状态关键词，命中错了会归错类：

| 动画名 | 实际状态 | 坑 |
|---|---|---|
| `idle` | idle | — |
| `thinking` | thinking | — |
| `working` | working | — |
| `done` | attention（完成） | 不能用 `attention`（不含关键词） |
| `notification` | notification | — |
| `juggling` | juggling | — |
| `error` | error | — |
| `sweeping` | sweeping | — |
| `carrying` | carrying | — |
| `sleep` | sleeping | — |
| `waking` | waking | — |
| `walk` | roam | — |
| `praise` | tapRight（点赞） | 不能用 `tapRight`（含 `tap` 会被认成 tapLeft） |
| `gaze` | idlePool | 不能用 `look`（含 `ok` → 被认成 tapRight） |
| `yawn` / `flower` / `smile` | idlePool | 不含关键词，自动进小剧场 |
| `tap` | tapLeft | — |
| `tickle` | tickle | — |
| `annoyed` | annoyed | — |
| `drag` | drag | — |

## 7. 已知限制（别重复踩）

1. **AI 逐帧重绘会漂**：两张同角色姿势之间常有 20% 像素差异，不能直接交替做动作。
2. **113 宽下手部只有 3-6px**：真正的手部动作（敲键盘、摆手）读不出来；别在“只动手”上浪费时间。
3. **道具遮挡**：正面抱大件道具时，手和键盘朝里，看不到操作。
4. **分层/骨骼**试过：拆件 → 位移能跑通（1-2px 接缝可接受），但肩口、遮挡处会露洞，且动作仍像“硬位移”；要做骨骼得加大画布并重做全部素材。
5. 宠物包无跨状态过渡，切换是硬切；只能让每个动画首帧尽量接近待机。

## 8. 新宠物（一只卡斯兰娜）的起手清单

- 角色：白发、蓝瞳、活泼可爱漂亮，名字「一只卡斯兰娜」（崩坏系列二创，简介写明非官方同人）
- 建议先出 1 张正面全身设定图，再按状态出姿势：待机开眼/闭眼、思考、干活、完成（跳起来）、提醒（举手）、报错（耷拉）、打扫、搬运、抛接、睡觉、醒来、被戳、点赞、摸头、生气、被拎、张望、打哈欠
- 活泼的角色：动作幅度可以比遐蝶大一点（跳跃 4-6px、挥手幅度大），但脚底基线必须稳
- 起手命令：

```sh
mkdir -p ~/workspace/kaslana/assets/poses
cp ~/workspace/xiadie/build.py ~/workspace/xiadie/pack_build.py ~/workspace/kaslana/
# 生成第一张设定图 → 挑定 → 按第 1 节批量出姿势
```

做完验收：`pet_pack_check.py out/<id> --compat-reactions` PASS，导入 App 跑一轮，确认待机、完成、被拎正常。
