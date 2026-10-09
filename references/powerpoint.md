# 平滑 PowerPoint

从本 Skill 生成 HTML 的 `explainer-data` 读取场景，不猜测任意网页语义。既有 HTML 需整理成场景契约或提供独立对象和关键状态接口。

每个可见对象转换为原生文字、图形或形状组，按同一坐标重建位置、尺寸与旋转。对应对象在所有幻灯片中使用稳定且唯一的 `!!对象ID` 名称。第二张开始加入原生 `p159:morph option="byObject"`，并提供 fade 兼容后备。设置 advClick=1，不写 advTm，故只在点击时推进。

基本元素可编辑，语义组合保留为形状组。复杂拆分从最初就保留独立子对象。新出现或离开的对象通常淡入淡出。PPT 平滑不逐项复现 GSAP 缓动、滤镜、实时按钮和嵌套时间线，需要中途形态时增加关键状态。

转换器支持文字、矩形、圆、椭圆、线、多边形和贝塞尔路径。遇到不支持元素必须报错，不能丢弃后继续宣称完成。字体替换可能改变排版，检查中文文本框。HTML 页外的操作按钮和讲解区不转换为幻灯片按钮；分镜中的讲解文字保留在分镜文件中。

结构自检应核对 XML、关系引用、状态数量、独立对象、稳定名称、Morph 和点击推进。结构通过不等于已在 PowerPoint 播放验证。支持 Morph 的 PowerPoint 应进行实际播放检查；旧版可能使用 fade 后备。

官方说明：
- https://support.microsoft.com/en-us/powerpoint/morph-transition-tips-and-tricks
- https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/68d26d78-f7f5-47ab-835d-4e6c82ff39f0
