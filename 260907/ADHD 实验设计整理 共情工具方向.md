# ADHD项目·实验设计整理（共情工具方向）

> 背景：项目方向从"效率提升工具"转回"共情工具"（让ADHD/非ADHD人群互换体验对方的感官处境），本文档整理配套的两个前期实验的具体设计方案，对应会议纪要中"多感官量化实验"与"社交场景身份切换调研"两条并行线。

---

## 一、方向说明：实验目的的调整

原方案（效率导向）的实验目的是"找到干扰与专注的最优边界，为产品干预策略提供数据支撑"。

调整后（共情导向），实验目的变为：**采集ADHD人群在不同感官干扰下的真实客观表现与主观体验数据，与非ADHD对照组做差异比对，这份差异数据将作为后续视觉/感官转译装置的素材基础**——即先搞清楚"体验差异具体是什么样子"，再决定怎么把这种差异转译给另一群人体验。

---

## 二、实验一：多感官量化实验

### 2.1 任务设计：为什么放弃"整理桌面"

"整理桌面"存在监督缺失下的核心问题：**"完成"的判定标准主观、软性**（叠没叠整齐、摆放算不算到位，无法脱离主观评判），在无法一手监督的邮寄实验条件下，这个任务无法被客观量化核验。

**替代方案：划消任务（Cancellation Task）**

认知心理学中用于测量注意力/警觉度的经典范式（如临床常用的 d2 注意力测试）。

**任务形式**：打印一张随机排列的字符矩阵（如满页字母），其中混杂固定数量的目标字符（如所有"F"和"E"），要求受试者"尽快划掉所有目标字符"。

**为什么适合无监督邮寄实验**：
- 目标字符总量和位置是实验者提前设定的已知量，纸张寄回后可直接、客观核验，不依赖现场监督
- 时间可用随包寄送的机械沙漏/计时器自行记录（避免用手机计时，因为手机本身要用于视觉干扰条件）
- 认知警觉任务本身较少受个人生活习惯差异影响（不像整理任务受"是否天生喜欢整洁"影响），干扰变量更纯粹

**需要控制的实验细节**：
- 每个条件使用内容不同但字符总量、目标出现频率、排列随机性一致的卷子版本，避免练习效应混入干扰效应
- 卷子/信封编号需在受试者间做顺序随机化，避免"永远第一个做基线组"造成的顺序效应

### 2.2 受试者分组

- A组：疑似/确诊ADHD受试者
- B组：非ADHD受试者（对照组）
- 两组执行完全相同的任务与干扰条件，用于计算差异

### 2.3 多感官对照实验矩阵（单一→融合）

采用 2×2×2 析因设计，视觉(V)/听觉(A)/触觉(T) 三通道各分"有/无"两档，共8种条件：

| 条件编号 | 视觉(V) | 听觉(A) | 触觉(T) | 说明 |
|---|---|---|---|---|
| 0 | — | — | — | 基线组（无任何干扰，必做，作为对照锚点） |
| 1 | ✓ | — | — | 纯视觉干扰（手机播放短视频） |
| 2 | — | ✓ | — | 纯听觉干扰（分心音乐） |
| 3 | — | — | ✓ | 纯触觉干扰（震动手机/毛绒逗猫棒放在手边可摸） |
| 4 | ✓ | ✓ | — | 视觉+听觉融合 |
| 5 | ✓ | — | ✓ | 视觉+触觉融合 |
| 6 | — | ✓ | ✓ | 听觉+触觉融合 |
| 7 | ✓ | ✓ | ✓ | 三感官全融合 |

**精简版（若8条件对邮寄实验负荷过大）**：基线 + 3个单一感官 + 1个三感官全融合，共5条件。牺牲交互效应的完整分析，但仍可回答"单一 vs 完全融合"的核心问题，操作难度更低。

### 2.4 每种条件统一记录的数据

**客观数据**：
- 完成总时长（计时器读数）
- 遗漏错误数（该划未划的目标字符数）
- 误判错误数（划错的字符数）

**主观数据（为共情转译服务，新增）**：
- 自评干扰强度（1-5分，任务结束在卷子背面填写）
- 每次被干扰打断后的当下感受（简单量表：从"很难拉回来"到"很容易拉回来"）
- 开放式简短记录："被打断的那一刻，你脑子里在想什么？"（一句话即可）
- 生理感受描述（自愿）：心跳变化、烦躁/愧疚感等主观体感

### 2.5 物料包设计

延续"邮寄规则手册+胶卷相机"方案：
- 规则手册：说明8（或5）个条件的具体操作步骤、每个信封对应的干扰工具
- 胶卷相机：仅在几个关键节点拍照（如"第一次分心的瞬间""完成瞬间"），控制拍摄成本，同时让照片本身成为关键节点标记
- 新增"感受记录卡"：在拍照的关键节点，额外写一两个词描述当下感受——这些原始词汇本身可作为后续装置转译的语言素材
- 机械沙漏/计时器：替代手机计时，避免与视觉干扰条件冲突

### 2.6 数据分析的核心价值

析因设计能够检验"单一感官干扰效果之和"是否等于"融合条件的实际效果"——如果单一视觉/听觉干扰各自造成约10%效率下降，但三感官融合时效率暴跌40%（而非预期的30%左右），说明感官融合存在**超加性放大效应**。这组数据可直接验证/挑战"多维完成度不能简单相加"这一核心理论，是作品集中具有实证分量的支撑材料。

---

## 三、实验二：社交场景身份切换调研

按会议纪要要求收集3-5个案例，围绕三个具体理论支点展开调研，而非漫无目的搜集：

### 3.1 空间维度 · 阈限空间（Liminal Space）

由人类学家范热内普（Arnold van Gennep）1909年在《过渡礼仪》中提出，描述仪式中"脱离旧状态→中间过渡→进入新状态"的三段结构。中间的"阈限"阶段被认为是身份最松动、最容易被重塑的阶段。可用此框架分析教室 vs 咨询室的空间差异，或走廊、候诊室等"阈限空间"的建筑学案例。

### 3.2 服装维度 · 穿衣认知（Enclothed Cognition）

Adam 与 Galinsky 2012年的经典实验：受试者穿白大褂后，在注意力测试（Stroop test）中错误率显著降低（约减半），但**关键前提是受试者相信这是"医生的白大褂"**——若被告知只是"画家的罩衫"，效果消失。说明触发身份切换的不只是"穿了什么"，还有"如何理解自己穿的这件东西"，对装置的仪式感设计（形式+被赋予的意义）具有直接参考价值。

### 3.3 产品端/线上线下维度 · 假通勤（Fake Commute）

远程办公者因失去通勤这一物理过渡，难以完成"下班"心理切换，因而主动发明"戴耳机出门走一圈再回家"等仪式性替代行为，人为制造身份切换缓冲带。证明**身份切换需要物理/时间缓冲带，一旦被技术压缩掉，人会本能地自行发明仪式补上**——与产品"人工触发身份切换"的逻辑同构。

---

## 四、资料链接

**阈限空间 / Liminal Space**
- Meridian University《Liminal Space Meaning: The Psychology of In-Between》：https://meridianuniversity.edu/content/liminal-space-meaning-the-psychology-of-in-between
- First In Architecture《What is Liminal Space?》：https://www.firstinarchitecture.co.uk/what-is-liminal-space/
- ResearchGate论文《Looking for Liminality in Architectural Space》：https://www.researchgate.net/publication/326675016_Looking_for_Liminality_in_Architectural_Space
- Satyori Glossary《Liminal Space》：https://satyori.com/glossary/liminal-space/

**穿衣认知 / Enclothed Cognition**
- Wikipedia《Enclothed cognition》：https://en.wikipedia.org/wiki/Enclothed_cognition
- 原始论文PDF（Adam & Galinsky, 2012）：https://utstat.utoronto.ca/reid/sta2201s/2012/labcoatarticle.pdf
- BPS Research Digest 解读（含具体实验数据）：https://www.bps.org.uk/research-digest/introducing-enclothed-cognition-how-what-we-wear-affects-how-we-think
- ScienceDirect原文摘要：https://www.sciencedirect.com/science/article/abs/pii/S0022103112000200

**假通勤 / Fake Commute**
- Washington Post《Fake commute: A way to carve out transition time around work》：https://www.washingtonpost.com/lifestyle/wellness/fake-commute-home-work-transition-/2021/02/22/49f79d56-6cb7-11eb-9f80-3d7646ce1bc0_story.html
- Fast Company《Want to be more productive? Try a fake commute》：https://www.fastcompany.com/90703258/want-to-be-more-productive-try-a-fake-commute
- Forbes《How Fake Commuting Can Improve Your Remote Workday》：https://www.forbes.com/sites/ashiraprossack1/2021/01/30/how-fake-commuting-can-improve-your-remote-workday/365610

---

## 五、待决定事项

1. 8条件完整析因矩阵 vs 5条件精简版，需结合可招募的受试者数量和邮寄周期决定
2. 划消任务的具体字符设计（目标字符类型、矩阵密度）需要小范围预测试校准难度，确保任务本身不会太简单（天花板效应）或太难（地板效应）
3. ADHD组与对照组的招募渠道和样本量需要进一步落实
4. 身份切换调研的3-5个案例，除以上三个理论支点外，是否需要结合 Masking（伪装）现象做进一步的案例筛选

---

*整理说明：本文档整合了实验设计讨论的最新版本，此前"整理桌面"任务方案和纯效率导向的实验目的已被本文档的方案取代。*
