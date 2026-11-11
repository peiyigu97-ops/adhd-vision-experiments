ADHD 视角转换产品
│
├── 01｜PROJECT CORE 项目核心
│   │
│   ├── 核心问题
│   │   ├── ADHD 与 Non-ADHD 对环境信息的注意优先级可能不同
│   │   ├── 同一个现实场景
│   │   └── 不同用户 → 不同视觉信息处理方式
│   │
│   ├── 核心概念
│   │   ├── Perspective Transformation
│   │   ├── Visual Attention
│   │   ├── Distractor / Non-distractor
│   │   └── Selective Visual Transformation
│   │
│   └── 最终目标
│       └── REAL WORLD
│             ↓
│         Perception
│             ↓
│         Interpretation
│             ↓
│         Relevance
│             ↓
│         Visual Transformation
│             ↓
│         DIFFERENT VISUAL PERSPECTIVES
│
│
├── 02｜PHASE 1：EDGE AI 实验基础
│   │
│   ├── Hardware
│   │   ├── ESP32-CAM
│   │   ├── 3MP Camera
│   │   ├── Download Board
│   │   └── Output Board
│   │
│   ├── Edge Impulse
│   │   ├── Image Collection
│   │   ├── 每个物体约 30 张
│   │   ├── Training
│   │   └── Deployment
│   │
│   ├── 实验结果
│   │   ├── 已训练物体 → 可以识别
│   │   ├── 未训练物体 → 容易识别失败
│   │   └── 同类别但外观差异大的物体 → 泛化能力有限
│   │
│   └── 得出的 Research Question
│       └── Closed-set recognition
│           是否足以应对开放现实环境？
│
│
├── 03｜PHASE 2：OPEN-WORLD VISION
│   │
│   ├── 为什么升级
│   │   ├── 不可能把世界上每一个物体都加入训练集
│   │   ├── 不能只识别“训练过的具体物品”
│   │   └── 需要理解“类别”而非记忆单个物体
│   │
│   ├── ESP32-CAM 的职责
│   │   ├── Camera
│   │   ├── Image Capture
│   │   ├── Wi-Fi
│   │   └── Image / Video Stream
│   │
│   ├── Computer / Local AI
│   │   ├── Python
│   │   ├── OpenCV
│   │   └── Vision Model
│   │
│   ├── 第一版
│   │   └── YOLO
│   │       ├── Pre-trained Model
│   │       ├── Object Detection
│   │       ├── Bounding Box
│   │       └── Confidence
│   │
│   └── 第二版
│       └── Open-Vocabulary Detection
│           ├── YOLO-World
│           ├── Grounding DINO
│           └── OWLv2 / OWL-ViT
│
│
├── 04｜OBJECT PERCEPTION
│   │
│   ├── 输入
│   │   └── ESP32-CAM 实时画面
│   │
│   ├── 输出
│   │   ├── Object
│   │   ├── Label
│   │   ├── Bounding Box
│   │   └── Confidence
│   │
│   ├── 示例
│   │   ├── Phone
│   │   ├── Book
│   │   ├── Cup
│   │   ├── Headphones
│   │   ├── Earphone Case
│   │   └── Unknown Object
│   │
│   └── 核心变化
│       └── 从
│           “我有没有训练过它？”
│           ↓
│           转变为
│           “它在现实世界中是什么？”
│
│
├── 05｜PHASE 3：RELEVANCE ENGINE
│   │
│   ├── ★ 项目的真正核心
│   │
│   ├── Object ≠ Distractor
│   │
│   ├── 为什么？
│   │   ├── 同一个物体在不同任务下意义不同
│   │   ├── Phone 可能是干扰物
│   │   ├── Phone 也可能是当前任务工具
│   │   └── “干扰物”是 Context-dependent
│   │
│   ├── 输入
│   │   ├── Object
│   │   ├── User Type
│   │   ├── Current Task
│   │   └── Context
│   │
│   ├── 输出
│   │   ├── Relevance Score
│   │   ├── Distractor
│   │   └── Non-distractor
│   │
│   └── 示例
│       │
│       ├── Task = Reading
│       │   │
│       │   ├── Book
│       │   │   └── Relevant
│       │   │
│       │   ├── Phone
│       │   │   └── Distractor
│       │   │
│       │   ├── Headphones
│       │   │   └── Distractor
│       │   │
│       │   └── Laptop
│       │       └── 根据任务判断
│       │
│       └── 核心逻辑
│           Object
│             ↓
│           Context
│             ↓
│           Relevance
│
│
├── 06｜USER MODEL
│   │
│   ├── ADHD
│   │   ├── Distractor
│   │   │   ↓
│   │   │   Visual Suppression
│   │   │
│   │   └── Non-distractor
│   │       ↓
│   │       Maintain
│   │
│   └── Non-ADHD
│       ├── Distractor
│       │   ↓
│       │   Maintain
│       │
│       └── Non-distractor
│           ↓
│           Attention Enhancement
│
│
├── 07｜PHASE 4：VISUAL TRANSFORMATION
│   │
│   ├── ADHD Perspective
│   │   │
│   │   ├── Distractor
│   │   │   ├── Pixelation
│   │   │   ├── Melting
│   │   │   ├── Blur
│   │   │   ├── Fade
│   │   │   └── Visual Distortion
│   │   │
│   │   └── Non-distractor
│   │       └── Normal
│   │
│   └── Non-ADHD Perspective
│       │
│       ├── Distractor
│       │   └── Normal
│       │
│       └── Non-distractor
│           ├── Highlight
│           ├── Glow
│           ├── Edge Enhancement
│           ├── Slight Scale
│           ├── Color Enhancement
│           └── Motion Emphasis
│
│
├── 08｜REAL-TIME VISUAL SYSTEM
│   │
│   ├── Python
│   │   ├── Camera Input
│   │   ├── Object Detection
│   │   ├── Relevance Calculation
│   │   └── Data Transmission
│   │
│   ├── Communication
│   │   └── WebSocket / JSON
│   │
│   └── Unity
│       ├── Real-time Image
│       ├── Bounding Box
│       ├── Shader
│       ├── Pixelate
│       ├── Melt
│       ├── Blur
│       ├── Highlight
│       └── Distortion
│
│
├── 09｜PHASE 5：VISION API
│   │
│   ├── 作用
│   │   └── Semantic Understanding
│   │
│   ├── 触发条件
│   │   └── Vision Model
│   │       ↓
│   │       Unknown / Low Confidence
│   │       ↓
│   │       Vision API
│   │
│   ├── API
│   │   ├── OpenAI Vision
│   │   ├── Gemini Vision
│   │   └── Claude Vision
│   │
│   ├── 示例
│   │   └── Unknown Object
│   │         ↓
│   │       Vision API
│   │         ↓
│   │       “Silicone earphone case”
│   │
│   └── 注意
│       └── API 是 semantic fallback
│           不是最终的视觉处理器
│
│
├── 10｜PHASE 6：VISUAL MEMORY
│   │
│   ├── Image
│   │   ↓
│   ├── Vision Encoder
│   │   ↓
│   ├── Embedding
│   │   ↓
│   └── Vector Database
│
│   ├── 功能
│   │   ├── Remember
│   │   ├── Similarity Search
│   │   ├── Distinguish
│   │   └── Previously Seen Object
│   │
│   ├── 示例
│   │   ├── 第一次看到 A 耳机套
│   │   │   └── Object #01
│   │   │
│   │   ├── 第二次看到 A 耳机套
│   │   │   └── Previously Seen #01
│   │   │
│   │   └── 第一次看到 B 耳机套
│   │       └── New Object
│   │           Category = Earphone Case
│   │
│   └── 目的
│       └── 从
│           Recognition
│           ↓
│           Understanding
│           ↓
│           Memory
│
│
├── 11｜最终完整系统
│   │
│   │                   REAL WORLD
│   │                       ↓
│   │                 ESP32-CAM
│   │                       ↓
│   │                     Wi-Fi
│   │                       ↓
│   │              OpenCV / Python
│   │                       ↓
│   │          Open-Vocabulary Detection
│   │                       ↓
│   │              Object + Bounding Box
│   │                       ↓
│   │               Context / Task
│   │                       ↓
│   │                Relevance Engine
│   │                       ↓
│   │              ┌────────┴────────┐
│   │              ↓                 ↓
│   │            ADHD            Non-ADHD
│   │              ↓                 ↓
│   │        Distractors       Non-distractors
│   │              ↓                 ↓
│   │          Suppress          Enhance
│   │              ↓                 ↓
│   │              └────────┬────────┘
│   │                       ↓
│   │                    Unity
│   │                       ↓
│   │              Real-time Shader
│   │                       ↓
│   │          TRANSFORMED VISUAL WORLD
│   │
│   └── Optional
│       ├── Vision API
│       └── Visual Memory
│
│
├── 12｜RESEARCH / EVALUATION
│   │
│   ├── Experiment A
│   │   └── Edge Impulse
│   │       └── Closed-set baseline
│   │
│   ├── Experiment B
│   │   └── Open-Vocabulary Model
│   │       └── Open-world generalization
│   │
│   ├── Experiment C
│   │   └── Relevance Engine
│   │       └── Distractor / Non-distractor
│   │
│   ├── Experiment D
│   │   └── Perspective Transformation
│   │       ├── ADHD
│   │       └── Non-ADHD
│   │
│   └── Metrics
│       ├── Object Detection Accuracy
│       ├── Relevance Classification Accuracy
│       ├── Transformation Accuracy
│       ├── False Positive / False Negative
│       └── End-to-End Latency
│
│
└── 13｜PORTFOLIO NARRATIVE
    │
    ├── Problem
    │   └── How different attentional priorities
    │       shape perception of the same environment?
    │
    ├── Research
    │   └── ADHD / Attention / Distraction
    │
    ├── Phase 1
    │   └── Edge AI
    │
    ├── Limitation
    │   └── Closed-set recognition
    │
    ├── Iteration
    │   └── Open-world vision
    │
    ├── Intelligence
    │   └── Object → Context → Relevance
    │
    ├── Interaction
    │   └── Relevance → Visual Transformation
    │
    ├── Personalization
    │   └── ADHD / Non-ADHD
    │
    ├── Advanced AI
    │   ├── Vision LLM
    │   ├── Embedding
    │   └── Visual Memory
    │
    └── Final Concept
        └── “The system does not normalize attention.
            It visualizes different attentional perspectives.”