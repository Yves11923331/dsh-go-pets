# 遐蝶 · 像素宠物工程

dsh-go 宠物包「遐蝶」的制作工程。所有帧由 `build.py` 从 `assets/poses` 的姿势图重新生成，
可随时改姿势、改帧数、加动画。

## 目录

```
xiadie/
  build.py              # 组装器：姿势图 -> 统一像素格 -> 动画帧 -> 预览 GIF
  make_overview.py      # 拼 out/总览.png（中文标签 + 帧数）
  assets/
    poses/              # 每个姿势一张 GPT 原图（160 逻辑高，透明底）
      stand.png         # 待机站立
      closed.png        # 闭眼（眨眼用）
      poke.png          # 被戳缩身
      think.png         # 托腮思考
      work.png          # 抱笔记本打字
      error.png         # 垂肩低头（原图带汗滴）
      cheer.png         # 跳跃庆祝
      notify.png        # 举手提醒
      wake.png          # 揉眼伸懒腰
      sweep.png         # 拿扫帚
      carry.png         # 抱纸箱
      juggle.png        # 抛三个球
      praise.png        # 竖大拇指
      tickle.png        # 捂嘴笑
      annoyed.png       # 嘟嘴皱眉
      drag.png          # 被拎起来
      look.png          # 转头张望
      yawn.png          # 打哈欠
      flower.png        # 摸花饰
      smile.png         # 捧心
      sleep.png         # 坐睡
    walk-sheet.png      # 4 帧走路精灵图（横向四格）
    ref.jpg             # 原始参考图
    chosen.png          # 选定的小人设定图（右上角那版）
  frames/               # 生成的动画帧（可随时重建）
  preview/              # 预览 GIF
  out/astral-pixel/     # 打包后的宠物包（pack.json + 每个动画一张精灵表）
  out/总览.png           # 25 个动画总览
  NOTES.md
```

## 动画清单

| 动画 | 状态/反应 | 帧数 | 触发 |
|---|---|---|---|
| idle | 待机 | 16 | 空闲（呼吸 + 眨眼） |
| thinking | 思考 | 8 | agent 思考中 |
| working | 干活 | 8 | 工具运行中（1 个会话） |
| working2 | 干活·双代理 | 4 | ≥2 个子代理（`tiers`） |
| done | 完成 | 8 | 回合完成 |
| notification | 提醒 | 8 | 等你确认/回答 |
| error | 报错 | 8 | 回合级错误（工具失败不会触发） |
| juggling | 抛接 | 4 | 多子代理 |
| juggling2 | 抛接·双代理 | 6 | ≥2 个子代理（`tiers`） |
| sweeping | 打扫 | 6 | 上下文压缩 |
| carrying | 搬运 | 4 | 上传/搬运 |
| sleeping | 睡觉 | 2 | 长时间无操作 |
| waking | 醒来 | 6 | 从睡到醒过渡 |
| roam (walk) | 走路 | 4 | 桌面上游走 |
| tapLeft | 被戳 | 4 | 点左半身 |
| tapRight (praise) | 点赞 | 4 | 点右半身 |
| tickle | 摸头 | 6 | 摸头 |
| tickle2 | 摸头第二段 | 6 | 连点摸头（`reactions.tickle2`） |
| annoyed | 生气 | 5 | 惹烦 |
| drag | 被拎 | 8 | 拖拽 |
| gaze / yawn / flower / smile | 小剧场 | 5/4/4/4 | 空闲 45–300 秒随机 |

## 重建

```sh
cd /root/workspace/xiadie
python3 build.py        # 生成 frames/（带逐帧时长）与 preview/
python3 pack_build.py   # 打包，并写入 tiers / bonus / timings
python3 make_overview.py  # 重拼 out/总览.png
python3 ~/.dsh/skills/pet-theme/scripts/pet_pack_check.py out/astral-pixel --compat-reactions
cd out/astral-pixel && python3 -m zipfile -c /sdcard/Download/DSH-Go/遐蝶/遐蝶.zip pack.json *.png
```

注意：`pack_build.py` 是自定义打包器，复用官方 `make_pet_pack` 的精灵表写入与锚点/碰撞测量，
额外写入 `bonus` 与 `timings`（官方逐帧目录模式不生成这两个字段）。不要用 `pet_theme_convert.py`
的逐帧模式重新打包，否则会丢彩蛋与最短显示时长。

## 2026-11-24 升级（轻量三件套）

- **逐帧时长**：每个动画的每一帧单独设 ms（眨眼 90ms、完成起跳 60/滞空 200/落地 90），
  取代原来的统一值；`frames/meta.json` 保存时长与循环标记。
- **完成彩蛋**：`attention` 状态 30% 概率播 `cheer2`（带星星彩带的跳跃），主播放 `done`。
- **最短显示**：`timings.minDisplay` 给 error 1600ms、notification 1800ms、attention 1200ms，
  配合 `autoReturn.attention` 4000ms，避免报错一闪而过、庆祝卡住。
- 画布保持 113×170 不变。
- 备用姿势在 `assets/future/`（伸懒腰、看蝴蝶、理头发、另一版彩带庆祝），留给下一轮做小剧场。

校验必须 PASS 再交付。

## 2026-11-25 升级（分档 / 摸头二段 / 分档时长）

- **working 分档**：`working` 抱笔记本（1 个会话）→ `working2` 用 `assets/future/side-work.png` 桌前打字（≥2 个会话），
  `tiers.working` 写入 `[{min:2,anim:working2},{min:1,anim:working}]`。
- **juggling 分档**：`juggling` 4 帧 → `juggling2` 6 帧（抛更高 + 左右摇），`tiers.juggling` 同理。
- **摸头二段**：`tickle2` 由 tickle 姿势整体压扁（0.94→0.85，脚底不动）做出"笑到弯腰"；
  `reactions.tickle2` 用平铺字符串键（与官方 convert 的主题模式一致），`--compat-reactions` 实测仍 PASS。
- **时长补全**：`timings.minDisplay` 补 sweeping 5600 / carrying 3200；`autoReturn` 补 sweeping 300000（安全上限）/ carrying 3200。
- working2 的构图含桌子、整体比 working 宽，`place(center='content')` 按内容居中，避免贴右边缘被裁。

## 2026-11-26 working2 降抖

- 原 `working2` 8 帧、每帧 80–100ms，同时叠 `dx ±1` 与 `dy 0→-2`，整张桌子跟着左右/上下跳。
- 改为 4 帧 `dy (0,-1,-1,0)`、每帧 200–220ms、`dx=0`：人物和桌子不再左右移，只保留 1px 慢呼吸。
- 帧数 8→4，打包后精灵表合并成 2 帧，`tiers` / `states` 不变，`pet_pack_check.py --compat-reactions` PASS。

## 2026-11-26 技能对照补项（pet-theme）

- 补 `timings.minDisplay.working/thinking = 1000`：短暂状态防抖，避免一闪而过（技能参考值）。
- 补 `timings.autoReturn.error = 4800`：报错 4.8s 后自动回待机；原来没写 `autoReturn`，error 只能等下一个状态覆盖。
- `author / license / source` 保持 null：作者信息走创意工坊投稿，不写进包里（已投稿，避免与投稿信息冲突）。
- `pet_pack_check.py --compat-reactions` 仍 PASS；成品 zip md5 `c5126dec…`。
- 动画 22 → 25，zip 约 1.05 MB；旧 astral-pixel 草稿目录已移到 `魔门-DSH/CC-临时/astral-pixel-旧版-20261125/`。

## 命名规则（踩过的坑）

转换脚本按**文件夹名**匹配状态关键词，命名不当会归错：

- `look` 含 `ok` → 会被认成 tapRight，所以张望动画叫 `gaze`
- `tapRight` 含 `tap` → 会被认成 tapLeft，所以点赞动画叫 `praise`
- `attention` 不含关键词 → 完成动画叫 `done`
- `walk` → roam，`sleep` → sleeping，`think*/work*/error/notify*/wake*/sweep*/carry*/juggle*` 都能直接命中
- 没命中的（`gaze/yawn/flower/smile`）自动进待机小剧场

## 改法

- **换姿势**：把新图放进 `assets/poses/`，改 `build.py` 里 `POSES` 的路径；统一压到 160 逻辑高。
- **调节奏**：改 `main()` 里 `seqs` 的毫秒数。
- **加帧**：在对应动画的列表里加 `shift(pose, dy)` 或 `shift_x(pose, dx)`。
- **加动画**：新建 `seqs['名字']`，名字要命中状态关键词，否则进小剧场。
- **改尺寸**：`H = 160` 是逻辑高，crisp 通道要求 ≤256 且 alpha 只有 0/255。

## 素材与授权

角色设定来自用户提供的同人图（`assets/ref.jpg`），姿势图用 GPT 图像模型按该设定生成，
像素化后人工对齐。仅作自用；若要投稿创意工坊，注意同人素材的授权问题。

## 2026-11-24 分层拆件试做（未通过，留待下次）

结论：拆件可行，"手臂独立动"成立，但当时效果用户不通过。

做了什么：
- 生成 A-pose 基准（手臂与身体分开），像素化后按矩形切出左右袖臂层，`(24,86,40,120)` / `(64,86,80,120)`。
- 身体层在手臂位置用内侧列补洞，手臂层上移 2-3px，配合上身 1px 呼吸，输出动图。
- 结果：1-2px 位移接缝可接受，3-4px 时肩口露白。

下次继续要改的：
1. 沿袖子轮廓切，不要矩形切；肩口补 1 帧连接过渡。
2. 拆后发层、眼睛层，才能做"头发延迟摆"和"眨眼"。
3. 所有姿势（思考/干活/睡觉等）都按同一套部件重做，量大（估 2-3 天）。

素材已存 `assets/future/`：`apose1/apose2.png`（分层基准）、`side-work.png`（侧身打字）、
`stretch/butterfly/hair.png`（待机小剧场）、`cheer2-alt.png`。

working 最终仍用整帧起伏（100/70ms），不要再用这次试做的版本。
