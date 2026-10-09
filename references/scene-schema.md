# 场景契约

`scene.json` 是 HTML 和 PPTX 共用的完整状态数据。转换器可从生成的 HTML 中提取它。

```json
{
  "version": 1,
  "title": "对象变化过程", "width": 1600, "height": 900,
  "palette": {"background": "#F5F2EA", "ink": "#253D3F", "accent": "#167D8D"},
  "font": "Microsoft YaHei",
  "objects": [{"id": "token-a", "width": 180, "height": 90, "children": [
    {"kind": "rect", "x": 0, "y": 0, "w": 180, "h": 90, "rx": 14, "fill": "#DDECEF", "stroke": "#167D8D", "strokeWidth": 2},
    {"kind": "text", "x": 8, "y": 8, "w": 164, "h": 74, "text": "今天", "fontSize": 40, "fontWeight": 700, "fill": "#167D8D", "align": "center"}
  ]}],
  "states": [
    {"id": "start", "chapter": "认识对象", "title": "观察文字卡片", "narration": "看一个可以独立移动的对象。", "note": "示意", "objects": {"token-a": {"x": 300, "y": 300}}},
    {"id": "move", "chapter": "认识对象", "title": "接到另一个位置", "narration": "对象的身份保持不变。", "duration": 0.8, "objects": {"token-a": {"x": 950, "y": 450, "scale": 1.15, "rotation": 10}}}
  ]
}
```

## 坐标

对象内容位于局部框 `(0,0,width,height)`。状态 `x/y` 是局部原点在画布上的位置，旋转和缩放以此为中心：

```text
sx = scale * scaleX; sy = scale * scaleY
a = cos(rotation) * sx; b = sin(rotation) * sx
c = -sin(rotation) * sy; d = cos(rotation) * sy
e = x; f = y
```

某状态没有列出的对象不可见。可见对象默认 `opacity=1, scale=scaleX=scaleY=1, rotation=0`。目标是完整快照，不依赖先前状态遗留的缩放。对象 ID 不带 `!!`，转换器会自动加前缀。

## children

- `rect`：`x,y,w,h,rx,fill,stroke,strokeWidth`。
- `circle`：`cx,cy,r,fill,stroke,strokeWidth`。
- `ellipse`：`cx,cy,rx,ry,fill,stroke,strokeWidth`。
- `text`：`x,y,w,h,text,fontSize,fontWeight,fill,align`，`text` 可用换行。字体继承场景的 font，align 为 left/center/right。
- `line`：`x1,y1,x2,y2,stroke,strokeWidth,arrowEnd`。
- `path`：`d,stroke,strokeWidth,fill,arrowEnd`，使用绝对 `M L H V C Q Z` 命令，点位在对象框内。弧线转换成三次贝塞尔。
- `polygon/polyline`：`points` 为 `[[x,y],...]`，以及 `fill,stroke,strokeWidth,arrowEnd`。

`arrowEnd=true` 表示终点箭头。颜色为六位十六进制，fill/stroke 可为 none。子元素可有 opacity。不能包含任意 HTML、滤镜、外链资源或执行脚本。

标题区域 y=40–125，主要视觉区域 y=155 到 height-160，底部放说明。为文字和笔画留余量。可选 sources 为 `[{"title":"名称","url":"https://..."}]`。状态 duration 是本次点击的动画时长，默认 0.8 秒，note 说明简化，narration 放在讲解区。

更复杂的动作可增加关键状态或扩展模板，但保留可供 PPT 使用的关键状态，并保持每阶段点击推进。
