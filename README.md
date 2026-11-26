# dsh-go 像素宠物合集

三只给 **dsh-go**（DeepSeek Harness 手机版）用的宠物包，含制作源码、成品 zip 和全部动画预览。

| 目录 | 宠物 | 画布 | 动画 | 成品 |
|---|---|---|---|---|
| [`whale-maid/`](whale-maid/) | 嫌弃の鲸鱼女仆 | 200×200（平滑绘制） | 22 | [`whale-maid.zip`](whale-maid/out/whale-maid.zip) |
| [`astral-pixel/`](astral-pixel/) | 遐蝶 | 113×170（像素画） | 25 | [`遐蝶.zip`](astral-pixel/out/遐蝶.zip) |
| [`naughty-gemini/`](naughty-gemini/) | 顽皮的Gemini | 200×200（平滑绘制） | 25 | [`naughty-gemini.zip`](naughty-gemini/out/naughty-gemini.zip) |

## 安装

1. 下载对应目录 `out/` 里的 zip
2. 打开 dsh-go → 设置 → 宠物 → 导入，选择 zip（同 id 会覆盖旧包）

三只包的 id 分别是 `whale-maid`、`astral-pixel`、`naughty-gemini`，互不冲突，可以同时装。

## 能力对比

- **分档**：三只都支持 `tiers`——1 个会话播 `working`，≥2 个子代理切到 `working2`；遐蝶另有 `juggling` / `juggling2` 两档。
- **反应**：被戳、点赞、挠痒、嫌弃、被拎；遐蝶多一段 `tickle2`（摸头第二段）。
- **彩蛋**：遐蝶、Gemini 完成时都有 30% 概率播专属 `cheer2`；Gemini 的彩蛋是长大成成年形态的透明立绘。
- **时长**：都写了 `timings.minDisplay` / `autoReturn`，避免报错一闪而过、庆祝卡住。

## 结构

```
whale-maid/      源码 + ref + previews + out/whale-maid.zip + README
astral-pixel/    源码 + assets + previews + out/遐蝶.zip + NOTES/PIPELINE
naughty-gemini/  源码 + ref + previews + out/naughty-gemini.zip + README
```

每个子目录的 `README.md` 有该只宠物的动画清单、脚本说明和重建命令。
打包脚本复用 dsh-go 自带的 `pet-theme` 技能脚本（`~/.dsh/skills/pet-theme/scripts/`），
需要本机装有 dsh-go 才能从零重建；只导入成品则不需要。

原始大图（`trans/`、`assets/poses/`、`symbols/`）因体积未收录，可用各目录的生成脚本重新产出。

## 授权

- 代码（`*.py`）：MIT，见 [LICENSE](LICENSE)。
- 角色与美术素材：**同人二创**，角色版权归原权利人（如《崩坏：星穹铁道》/ 米哈游），
  仅供学习交流，**禁止商用**；权利人如有异议，我会立即删除相关内容。
