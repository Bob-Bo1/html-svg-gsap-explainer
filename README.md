# HTML + SVG + GSAP 科普动画技能

用于 Codex 的点击式科普动画技能。把知识点或流程拆成关键阶段，以 SVG 对象和 GSAP 动画演示；每次点击推进一步，完成后停住。

## 功能

- 生成可离线打开的单文件 HTML，内嵌场景数据和 GSAP。
- 支持下一步、上一步、重置、章节跳转和全屏。
- 先写讲解分镜，再构建场景，最后检查动画和几何状态。
- 按需导出可编辑 PPTX，使用平滑切换连接关键状态。

## 安装

下载或克隆本仓库，然后运行：

```sh
python scripts/install_skill.py
```

默认安装到 Codex 的技能目录。如果同名目录已经存在，安装会停止，避免覆盖。可用 `--destination` 指定自定义技能父目录。安装后重启 Codex 或新开会话。

## 使用

在 Codex 中输入：

```text
$html-svg-gsap-explainer 帮我制作一份大语言模型后训练的科普动画
```

默认交付分镜和可点击的 HTML 动画。需要 PPTX 时请明确说明。本技能没有 MP4 导出或配音功能。

## 文件

- `SKILL.md`：技能流程和使用约定。
- `references/`：分镜、场景格式和 PowerPoint 转换说明。
- `scripts/`：依赖检查、构建、验证、导出和安装脚本。
- `assets/`：HTML 播放器模板和 GSAP。
- `agents/`：Codex 技能显示信息。

完整操作流程见 [SKILL.md](SKILL.md)。

## 第三方组件

`assets/gsap.min.js` 为 GSAP 3.15.0，保留原版权声明，适用 [GSAP 标准许可](https://gsap.com/standard-license)。本仓库不更改其许可。
