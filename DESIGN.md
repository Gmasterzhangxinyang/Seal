<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: MEC202 文档核验盖章系统
description: 学校行政场景的自动文档核验与盖章机器人操作界面
---

# Design System: MEC202 文档核验盖章系统

## 1. Overview

**Creative North Star: "The Quiet Control Room"**

一个安静、克制、信息清晰的操作指挥界面。没有多余的装饰，没有花哨的动画，每一个像素都在服务操作者的判断效率。灵感来自 Linear 的极简哲学：灰白底色上，唯一的有色元素是当前需要你注意的东西。

这不是一个需要"看起来科技感"的系统。它面对的是一个真实的物理机器人、一堆需要判断的文档、以及一条不可中断的审批链路。界面的任务是把复杂流程压平成清晰的视觉层级，让操作者一眼看到状态，两步完成操作。

它明确拒绝传统政务系统的蓝白模板和表格堆砌，也拒绝 SaaS 产品的渐变 hero 和指标卡片。安静本身就是这个系统的专业感。

**Key Characteristics:**
- 信息层级通过字重和灰度传达，不依赖颜色
- 大量留白，内容密度适中，不拥挤
- 状态色只在需要判断时出现（通过/驳回/待审）
- 交互反馈克制，只有状态切换时的微动效

## 2. Colors

**The Restrained Rule.** 界面由灰色系主导，单一强调色占比不超过 10%。强调色的稀少是重点，它的出现意味着"这里需要你操作"。

色相待定，方向为冷色调蓝或蓝紫（致敬 Linear），但需避免落入"蓝白政务模板"的陷阱。饱和度偏低，灰度感强，带一点冷色调的灰比纯灰更有品质。

### Primary
- [主强调色]：用于需要操作的关键按钮、选中态、链接。`[to be resolved during implementation]`

### Neutral
- 深灰（文字主色）：接近黑但不是纯黑，oklch 轻微带暖
- 中灰（次要文字、标签）：`[to be resolved]`
- 浅灰（背景、卡片底色）：带极轻冷色调的白
- 边框灰：`[to be resolved]`

### Status
- 通过/成功：偏冷的绿色
- 驳回/错误：沉稳的红色，不刺眼
- 待审/警告：内敛的琥珀/黄色
- 信息：与主强调色同色系，降低饱和度

### Named Rules
**The One Accent Rule.** 任何单屏上，强调色只出现在需要用户行动的元素上（按钮、选中态、关键链接）。如果一屏上到处都是强调色，那说明信息层级出了问题。

## 3. Typography

单一无衬线体路线。中文环境优先使用系统字体栈（PingFang SC / Microsoft YaHei / Noto Sans SC），西文可考虑 Inter 或类似几何无衬线体。不追求加载自定义字体，系统字体栈的体验已经足够好。

**Character:** 冷静、清晰、不抢戏。字重对比是层级的主要工具，而非字号跳跃。需兼容中英文双语环境，英文界面选用与中文系统字体搭配和谐的西文字体。

### Hierarchy
- **Display** (700, `[to be resolved]`, 1.1): 仅用于页面大标题，如"操作台""审计日志"
- **Headline** (600, `[to be resolved]`, 1.2): 卡片标题、区块标题
- **Title** (500, `[to be resolved]`, 1.4): 列表项标题、表格头
- **Body** (400, 14-15px, 1.6): 正文内容，最大行宽 65-75ch
- **Label** (500, 12-13px, 1, tracking 0.02em): 状态标签、辅助说明、时间戳

### Named Rules
**The Weight, Not Size Rule.** 同一层级内的区分靠字重（400 vs 500 vs 600），不靠大跳的字号。相邻层级的字号比值不超过 1.25。

## 4. Elevation

以 tonal layering（色调分层）为主，shadow 为辅。卡片和面板通过微妙的背景灰度差异区分层级，而非投影。只在 hover 和 focus 状态引入极轻的阴影作为交互反馈。

**The Flat-By-Default Rule.** 静态状态下所有表面是平的。阴影仅作为状态响应出现（hover、focus、drag）。

## 5. Components

`[待实现后补充，运行 /impeccable document 提取实际组件模式]`

## 6. Do's and Don'ts

### Do:
- **Do** 用灰度梯度建立信息层级，深灰主文字 → 中灰次文字 → 浅灰辅助
- **Do** 给操作按钮和关键交互元素保留充足的点击区域和呼吸空间
- **Do** 用字重对比（而非颜色）区分标题和正文
- **Do** 状态色只在需要用户判断的场景出现，其余全部灰度系
- **Do** 保持中文排版节奏，行高 1.5-1.6，段落间距适中

### Don't:
- **Don't** 使用传统政务风格的蓝白配色和密布表格布局
- **Don't** 使用渐变背景、hero 区大图、指标卡片堆叠（SaaS 营销模板风格）
- **Don't** 给卡片加粗边框或彩色侧边条纹
- **Don't** 使用 bounce、elastic 等弹性动效曲线，只用 ease-out
- **Don't** 在同一屏上过度使用强调色，它的稀少是设计的一部分
- **Don't** 堆砌企业 ERP 风格的功能菜单和嵌套导航
