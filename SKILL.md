---
name: html-svg-gsap-explainer
description: 将知识点、机制或流程制作成 HTML + SVG + GSAP 点击式科普动画，先形成讲解逻辑与动画分镜，再生成可离线打开的 HTML。用户要求 PowerPoint 时，将关键状态转换为使用平滑切换的 PPTX。适用于演示知识过程，不用于普通静态文稿或纯视频剪辑。
---

# 点击式科普动画

自主完成知识理解、视觉设计、几何构造、分镜、动画编排和制作。默认输出 **HTML + SVG + GSAP**，每次点击只推进一个阶段，动作完成后停住。每个阶段是连续过程的关键状态。

## 1. 检查并补齐依赖

把本 Skill 的真实目录记为 `SKILL_ROOT`，先执行：

```text
python <SKILL_ROOT>/scripts/doctor.py --mode html --install
```

已有依赖直接复用。缺失时脚本在 Skill 的 `.venv` 内安装官方包。根据返回的 `python` 路径执行后续脚本。生成 HTML 和转换 PPTX 只需 Python 标准库，GSAP 随包保留。浏览器验证需要 Playwright 和可用的 Chromium/Chrome/Edge。

安装只补缺失项，重复执行不做额外修改。浏览器访问被拒绝是运行权限阻塞，不是依赖缺失；不得反复安装或绕过。Python 本身缺失时选择官方安装途径，说明无法自动处理的阻塞。

## 2. 先生成讲解逻辑与分镜

读取 [references/storyboard.md](references/storyboard.md)。根据目标观众理解知识，必要时核对可信来源，区分原理、示意和假设。自主选择主题适合的配色、字体和视觉层级，默认 16:9。

先写完整 `storyboard.md`，包含每阶段讲解文字、动作、起止视觉状态、沿用对象 ID 和停留条件，再制作 HTML。用户要求先确认时，停在分镜处等待；已经确认或授权自主制作时，写完分镜后继续，不追加确认关卡。阶段数量由知识过程决定。

## 3. 构建可持续追踪的视觉对象

按 [references/scene-schema.md](references/scene-schema.md) 编写 `scene.json`，作为 HTML 和 PowerPoint 共用的关键状态数据。用 SVG 精确构建对象，通过移动、旋转、缩放、拆分、连接、重组演出知识过程。文字也可以是视觉对象。同一概念沿用稳定 ID；需要拆分的部分从开始就定义为独立对象。

```text
python <SKILL_ROOT>/scripts/build_html.py scene.json --out explainer.html
```

可以扩展模板，但保留这些约定：

- 打开停在初始状态。禁止自动播放、自动翻页和无限循环。
- 点击画面、下一步或空格推进一阶段，支持上一步、重置、章节跳转和全屏。
- 动作中忽略重复推进，完成后等待下一次输入。
- GSAP **只插值普通数值对象**，由其直接写入 SVG `matrix(a b c d e f)`。不混用 CSS transform、svgOrigin、transformOrigin 或原点补偿。
- 对象局部原点固定；每次动作结束精确写回完整目标状态，回退和重置不能积累偏移。
- HTML 内嵌 GSAP 与场景数据，可离线直接打开。
- 保留 `window.explainer` 的状态与跳转接口，以及 `explainer-data` JSON，使转换可复现。

## 4. 检查并修复

```text
python <SKILL_ROOT>/scripts/verify.py explainer.html --out qa
```

检查初始停留、点击后停留、回退、快速连点、重置、全部状态矩阵和截图。实际查看画面，修复溢出、遮挡和箭头错位。无法启动浏览器或访问被拒绝时记录 `blocked`，做可执行的静态与坐标检查，并说明实际浏览器验证未完成。模拟 DOM 或静态检查不能冒称为浏览器验证。

## 5. 按需输出 PowerPoint

只有用户要求 PowerPoint/PPTX 时执行，保留 HTML 源文件。读取 [references/powerpoint.md](references/powerpoint.md)：

```text
python <SKILL_ROOT>/scripts/doctor.py --mode pptx --install
python <SKILL_ROOT>/scripts/export_pptx.py explainer.html --out explainer.pptx
```

每个关键状态是一张幻灯片。文字与矢量图形保持独立、可编辑。同一对象使用稳定 `!!对象ID` 名称，通过原生 **平滑 / Morph** 衔接位置、大小和旋转。只设置点击推进，不设置计时翻页。

PPT 重建关键状态间的运动，不能声称逐项复现 GSAP 时间线、缓动或任意 SVG 特效。需要中途形态时增加关键状态。遇到转换器不支持的元素，指出限制再扩展，不静默丢弃。

## 交付

交付分镜和最终 HTML；要求 PPTX 时同时交付 PPTX。遵循当前环境的文件保存方式，说明点击、回退、重置的操作以及影响使用的限制。Skill 的安装目录与生成作品分开管理。
