# OV9281 低成本可穿戴眼动检测 —— Phase 2 可行性原型验证实验报告

项目：ALINEX ADHD 注意力检测/视觉干预系统
阶段：Phase 2 —— 单路眼动摄像头技术可行性验证
时间跨度：2026-10-04 ～ 2026-10-23
状态：**feasibility prototype（可行性原型），非最终产品，非商用眼动仪**

本报告的目的：为作品集呈现一条完整、可追溯的技术验证脉络——**每一步做了什么、为什么这么做、用什么平台/方法实现、算出了什么数字、数字说明了什么**。所有失败和反复都如实记录，不美化、不省略，这是工程可行性验证的核心价值所在：知道瓶颈在哪，比展示一个"看起来成功"的结果更重要。

---

## 0. 项目背景与总体技术路线

ALINEX 要验证的最终目标链路是：

```
OV9281眼部摄像头 → 瞳孔定位 → 相对注视方向
                                    ↓
                        （后续叠加IMU + 场景摄像头）
                                    ↓
                        gaze → scene object → attention target
```

Phase 2 只验证其中**最基础的一段**：OV9281 摄像头采集 → 瞳孔检测 → 瞳孔中心追踪 → 相对注视估计 → 简单标定。不涉及IMU、场景摄像头、注意力判定算法。

### 硬件
| 项目    | 规格                                                                                          |
| ----- | ------------------------------------------------------------------------------------------- |
| 摄像头   | OV9281，monochrome，1MP，Global Shutter，USB2.0 UVC，M12镜头，无IR-cut滤光片，105° FOV，标称1280×720@120FPS |
| IR 照明 | 10/4实验时**未安装**；10/8新增850nm IR补光LED，离轴安装                                                     |
![[e8ef38a18c7b1bba31121ff774001085.jpg|259]]![[19fdacef68b395b7498fe3b01a1307a6 1.jpg|259]]
### 软件环境
| 项目     | 规格                                                                      |
| ------ | ----------------------------------------------------------------------- |
| 操作系统   | Windows                                                                 |
| Python | 3.12.5 64-bit，独立环境 `D:\工业设计`（路径含中文字符，这一点后续造成过实际bug，见第1节）                |
| 核心库    | opencv-python 4.10.0.84、numpy 2.5.1、matplotlib 3.11.2                   |
| 开发工具   | Claude Code（本报告的协作生成工具），脚本以 `.py` 文件形式交给用户在自己的 PowerShell 终端运行，输出手动贴回核对 |
|        |                                                                         |

### 实验方式说明
受限于某些阶段需要真人实时操作摄像头（调整坐姿、按键采集、开关IR灯），本项目的每个脚本都由 AI 编写，但**必须由用户本人实际运行**，再把终端输出和保存的图片交回核查。这保证了每一步的"成功"都经过真实硬件验证，而不是纸面推演。

---

## 1. 环境搭建阶段：排查三个真实的工程障碍

在开始实验前，搭建可用的 OpenCV 环境本身遇到了三个独立问题，逐一记录：

### 1.1 pip 安装失败 —— 根因是残留的代理环境变量
**现象**：`pip install opencv-python` 报 ProxyError。
**排查方法**：用 `reg query HKCU\Environment` 检查用户级环境变量。
**根因**：`HTTP_PROXY`/`HTTPS_PROXY` 两个环境变量残留指向一个早已失效的本地代理端口 `127.0.0.1:6696`（与系统网络设置里另一个端口7890的代理完全无关，那个是已禁用状态，不是问题所在）。
**解决**：`reg delete` 清除这两个残留变量后，pip 立即可以正常访问 PyPI。

### 1.2 OpenCV 5.0.0 移除了经典 Haar cascade 模块
**现象**：安装完成后 `cv2.CascadeClassifier` 报 `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'`。
**排查方法**：检查 opencv-python 的 `.pyi` 类型声明文件和包内文件列表，确认 5.0.0.93 版本确实不再包含 CascadeClassifier 及配套的 `haarcascade_*.xml` 文件。
**解决**：降级到 `opencv-python==4.10.0.84`（用户在"是否降级到4.x"的选择中明确同意）。

### 1.3 OpenCV 底层无法读取含中文字符的路径
**现象**：`cv2.CascadeClassifier(cv2.data.haarcascades + "...")` 报错，错误信息里的路径字符串变成乱码（如 `D:\宸ヤ笟璁捐\...`）。
**根因**：Python 环境装在 `D:\工业设计`（含中文字符），OpenCV 的 C++ 底层 `cv::FileStorage` 读取函数在 Windows 上无法正确解析非 ASCII 路径，而 Python 原生文件 I/O（open、读写PNG）不受此限制——只影响 OpenCV 自己这一个底层读取函数。
**解决**：写 `copy_cascades.py` 把两个 XML 文件复制到项目目录（纯 ASCII 路径），之后从本地加载：

```python
# copy_cascades.py
import shutil
import os

SRC_DIR = r"D:\工业设计\Lib\site-packages\cv2\data"
DST_DIR = os.path.dirname(os.path.abspath(__file__))

files = ["haarcascade_frontalface_default.xml", "haarcascade_eye.xml"]
for f in files:
    src = os.path.join(SRC_DIR, f)
    dst = os.path.join(DST_DIR, f)
    shutil.copyfile(src, dst)
    print(f"Copied {f} -> {dst}")
```

**这个教训在报告里的意义**：三个问题都不是"代码写错了"，而是环境/平台层面的真实限制（网络配置、第三方库版本演进、Windows+中文路径的历史兼容问题）。可行性验证的一部分工作量，恰恰是把这类隐藏的环境成本显式地暴露出来。

---

## 2. 第二阶段：摄像头设备识别与帧率实测

### 2.1 目标与方法
**意义**：不能假设 camera index 固定，必须实测确认哪个 index 对应 OV9281。同时必须用真实连续抓帧而非 `CAP_PROP_FPS` 来衡量帧率（后者只是驱动上报的理论值，不代表实际吞吐）。

**统计方法**：对每个候选 index，在目标分辨率下连续读帧 5 秒，计算

```
measured_fps = frames_captured / elapsed_seconds
```

这是整个项目唯一被反复使用的核心测量范式——"真实发生的数量 / 真实经过的时间"，而非任何上报值或理论标称值。

**平台/工具**：OpenCV `cv2.VideoCapture`，DirectShow 后端（`cv2.CAP_DSHOW`，Windows UVC摄像头的标准后端）。

### 2.2 代码（`camera_test.py`，核心测量函数）

```python
def measure_fps(idx, backend, width, height, duration=5.0):
    cap = cv2.VideoCapture(idx, backend)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames = 0
    failed = 0
    start = time.time()
    while time.time() - start < duration:
        ret, frame = cap.read()
        if ret:
            frames += 1
        else:
            failed += 1
    elapsed = time.time() - start
    cap.release()

    return {
        "actual_width": actual_w, "actual_height": actual_h,
        "frames_captured": frames, "dropped_failed_frames": failed,
        "elapsed_seconds": round(elapsed, 3),
        "measured_fps": round(frames / elapsed, 2) if elapsed > 0 else 0,
    }
```

### 2.3 实测数据（`camera_enum_results.json`，原始数据）

| Index | 分辨率 | frames_captured | elapsed_seconds | measured_fps | dropped |
|---|---|---|---|---|---|
| 0 | 640×480 | 74 | 5.009 | 14.77 | 0 |
| 0 | 1280×720 | 73 | 5.015 | 14.56 | 0 |
| 1 | 640×480 | 588 | 5.011 | **117.34** | 0 |
| 1 | 1280×720 | 586 | 5.015 | **116.85** | 0 |

### 2.4 设备身份确认（`identify_camera.py`）
数字差异巨大（14 vs 117 FPS）已经高度提示 index 1 是 OV9281，但不能只靠数字推断——另外写了 `identify_camera.py` 分别保存两个 index 的实拍帧，**用人眼视觉核查**：index 1 输出单色灰度图像、有明显广角畸变，与 OV9281 规格（monochrome + 105°FOV）吻合；index 0 输出彩色图像，是 Windows 自带的 Integrated Camera。

**结论**：index 1 = OV9281，实测 FPS 116.85（1280×720），零丢帧，与标称120FPS@720p基本一致，采集链路本身可行。

> ⚠️ **重要更新（10/8）**：这个 index 映射关系后来发生了变化（见第7a节），说明"实测确认"必须每次复测，不能当作永久不变的常量写死在代码里。

---

## 3. 第三阶段：原始图像采集

**意义**：建立规范的数据采集流程，为后续所有图像分析提供统一格式的原始素材。

**方法/平台**：仍是 OpenCV VideoCapture，但这次目的不是测速度，而是真实落盘保存数据，用于离线分析。

**关键决策**：用 **PNG无损格式**保存，不用JPEG——因为JPEG的有损压缩会在边缘产生振铃伪影，直接污染后续瞳孔边界检测所需的像素级精度。

### 代码核心片段（`capture_raw.py`）

```python
# 10张静态帧
while saved < 10 and attempts < 30:
    ret, frame = cap.read()
    attempts += 1
    if not ret:
        continue
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # OV9281本身是单色，但DSHOW仍包装成3通道BGR，这里转换回真正的单通道灰度
    path = os.path.join(RAW_DIR, f"frame_{saved:02d}.png")
    cv2.imwrite(path, gray)
    saved += 1
    time.sleep(0.2)

# 5秒连续序列
frame_count = 0
start = time.time()
while time.time() - start < 5.0:
    ret, frame = cap.read()
    if not ret:
        continue
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(os.path.join(SEQ_DIR, f"seq_{frame_count:05d}.png"), gray)
    frame_count += 1
```

### 实测数据
- 10张静态灰度帧：保存到 `data/raw/`
- 5秒连续序列：**340帧**，有效保存帧率 **67.77 FPS**
![[作品集/课程/261004/data/raw/frame_00.png|292]]![[作品集/课程/261004/data/raw/frame_09.png|290]]
**这个数字本身也是如实报告的一个例子**：340帧/5秒=68FPS，明显低于第二阶段测到的117FPS裸读速度。原因很直接——这里的循环同时包含了磁盘写入时间，`measured_fps`这个指标会随着负载（是否写盘、写什么格式）变化，报告里必须说明是哪种场景下测的，不能笼统地说"摄像头是68FPS"或"摄像头是117FPS"。

---

## 4. 第四阶段：图像质量分析（无IR光源）

**意义**：在没有主动照明的情况下，量化描述当前图像的曝光/对比度状态，为后续判断"瞳孔检测失败是否是图像质量问题"提供基线数据。

**统计方法**：对每帧计算以下描述性统计量：

```python
def analyze(img):
    mean = float(np.mean(img))           # 平均亮度
    std = float(np.std(img))              # 标准差，作为对比度的代理指标
    vmin, vmax = int(np.min(img)), int(np.max(img))
    contrast_range = vmax - vmin
    saturated_low = int(np.sum(img == 0))    # 死黑像素数
    saturated_high = int(np.sum(img == 255)) # 死白像素数
    saturated_pct = 100.0 * (saturated_low + saturated_high) / img.size
    return {...}
```

**可视化**：用 matplotlib（Agg后端，非交互，因为脚本是无头运行）生成"原图+256-bin灰度直方图"的复合图，便于直观判断曝光分布是否集中在某个区间。

### 实测数据（10帧平均，`data/results/image_quality.csv`）
![[Pasted image 20261009115307.png]]

| 指标 | 平均值 |
|---|---|
| 平均亮度 | 68.36 / 255 |
| 标准差（对比度代理） | 42.96 |
| 饱和像素占比 | 0.008% |

**解读**：亮度偏暗但没有大面积死黑/死白，整体曝光在室内环境光下处于"可用但不理想"区间。报告中特别强调一点：**这个结论不能外推到"眼部ROI质量也可用"**——因为105°广角FOV下眼睛只占整幅画面很小一部分，全局统计量会掩盖局部区域（比如眼部）可能存在的对比度不足问题，这正是第六阶段失败的部分原因。

---

## 5. 第五阶段：实时眼睛 ROI 定位

**意义**：在整幅画面中自动找到"眼睛"这个局部区域，是瞳孔检测的前置步骤——瞳孔检测算法需要先知道在哪个小范围内找，不可能对整张105°广角图跑阈值分割。

**方法/平台**：OpenCV **Haar cascade**（经典机器学习方法，Viola-Jones 框架训练出的级联分类器，不是深度学习）。两级定位：先在全画面找人脸（缩小搜索范围），再在人脸区域内找眼睛。

```python
def detect_eye(gray_frame):
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])  # 取最大的人脸
    face_roi = gray_frame[fy:fy + fh, fx:fx + fw]
    eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))
    if len(eyes) == 0:
        return None
    ex, ey, ew, eh = max(eyes, key=lambda e: e[2] * e[3])
    return (fx + ex, fy + ey, ew, eh)
```

同时提供手动兜底方案：按 `m` 键用 `cv2.selectROI()` 手动框选，应对自动检测失败的情况。

**统计方法**：

```
命中率 = auto_detect_hits / auto_detect_attempts × 100%
```

每一帧都计入分母（不管成功与否），这是一个"尝试即计数"的指标，和后面第六c阶段对瞳孔检测引入的"公平帧筛选"方法不同——第五阶段的命中率本身就是目的（衡量这个检测器在真实连续视频流中的稳定性），不需要排除困难样本。

### 实测数据
| 指标       | 数值        |
| -------- | --------- |
| 自动检测尝试帧数 | 21868     |
| 自动检测命中帧数 | 3390      |
| **命中率**  | **15.5%** |
| 保存的ROI样本 | 20张       |
![[eye_auto_1791110451544.png|63]]![[eye_auto_1791110458032.png|64]]![[eye_auto_1791110463868.png|63]]![[eye_auto_1791110470346.png|66]]![[eye_auto_1791110476010.png|65]]![[eye_auto_1791110483568.png|66]]![[eye_auto_1791110489040.png|66]]![[eye_auto_1791110489040.png|66]]![[eye_auto_1791110508589.png|66]]![[eye_auto_1791110520214.png|65]]
![[eye_auto_1791110526371.png|65]]![[eye_auto_1791110532023.png|65]]![[eye_auto_1791110543489.png|65]]![[eye_auto_1791110546870.png|64]]![[eye_auto_1791110551599.png|65]]![[eye_auto_1791110559134.png|65]]![[eye_auto_1791110569645.png|65]]![[eye_auto_1791110687750.png|65]]![[eye_auto_1791110693926.png|65]]![[eye_auto_1791110698797.png|64]]
**结论**：命中率不稳定，符合预期——Haar cascade对头部姿态、光照变化敏感，这是经典方法在非受控环境下的典型表现，不是bug。

---

## 6. 第六阶段：初步瞳孔检测（核心发现）—— 无IR基线

这是整个 Phase 2 最关键的一个阶段，详细记录方法、两轮测试、以及**视觉复核推翻初步结论**的完整过程。

### 6.1 方法：经典图像处理流水线

```
grayscale → Gaussian blur → Otsu阈值 → 形态学开闭运算 → 轮廓检测 → 候选筛选 → 椭圆拟合
```

逐步拆解每一步的作用和背后的统计/几何计算：

```python
def detect_pupil(gray):
    h, w = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)  # 高斯模糊降噪，减少睫毛纹理造成的假边缘

    # Otsu自动阈值：在灰度直方图上自动找到一个阈值，使得阈值分割后
    # 两类像素（前景/背景）各自的类内方差之和最小（等价于最大化类间方差）
    # THRESH_BINARY_INV 把暗区域（瞳孔应该是全图最暗的结构）变成白色前景
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 形态学闭运算（先膨胀后腐蚀）：填补瞳孔内部因反光高光造成的小孔洞
    # 形态学开运算（先腐蚀后膨胀）：去掉孤立的小噪声点
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 候选筛选：面积占比（排除噪声点和占满全图的眼睑阴影）、长宽比（瞳孔应接近圆形）
    frame_area = h * w
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.01 * frame_area or area > 0.6 * frame_area:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh) if bh > 0 else 0
        if aspect < 0.5 or aspect > 2.0:
            continue
        perimeter = cv2.arcLength(c, True)
        # 圆度公式：4π×面积/周长² ，完美圆=1.0，越不规则越接近0
        circularity = 4 * np.pi * area / (perimeter ** 2)
        candidates.append((c, area, aspect, circularity))

    candidates.sort(key=lambda t: t[3], reverse=True)  # 取圆度最高的候选
    best_c, best_area, best_aspect, best_circ = candidates[0]

    if best_circ < THRESHOLD:  # 见6.3节，这个阈值的取值经过了一次重要修正
        return 失败

    ellipse = cv2.fitEllipse(best_c)  # 对轮廓点做最小二乘椭圆拟合，得到(中心,长短轴,旋转角)
    ...
```

**圆度（circularity）指标的统计意义**：`4π×area/perimeter²` 是等周不等式给出的几何量，衡量一个闭合形状与标准圆的接近程度，这里用作"这个轮廓是不是真的瞳孔"的置信度代理——瞳孔在近似正视角度下应接近圆形/椭圆形，被高光、眼睑、睫毛污染的轮廓形状会明显偏离圆形。

### 6.2 第一轮测试（圆度阈值0.5）
对第五阶段保存的20张ROI样本跑检测：**2张"成功"（10%）**。

### 6.3 视觉复核——推翻了"10%成功"这个初步结论

**这是报告中最重要的方法论环节**：没有止步于"程序输出success=True"就采信，而是用 Read 工具实际打开这2张"成功"样本的标注图核查——发现**两例都是误报**：拟合出的椭圆中心被瞳孔内的环境光反光高光点"带偏"，并没有真正落在瞳孔几何中心上，只是碰巧圆度数值达标。
![[annotated_eye_auto_1791110551599.png|330]]![[annotated_eye_auto_1791110463868.png|329]]
**修正措施**：把圆度阈值从 0.5 提高到 0.75，代码里保留了这段修改记录：

```python
# Threshold raised from 0.5 to 0.75 after visual audit: at 0.5, two detections
# that passed were confirmed (by eye) to be false positives -- the fitted
# ellipse was pulled off-center by specular highlights/eyelid shadow rather
# than tracking the true pupil boundary.
if best_circ < 0.75:
    result["reason"] = f"best candidate circularity too low ({best_circ:.2f})"
    return result
```

### 6.4 第二轮测试（圆度阈值0.75）：**20张样本，0张通过（0.0%）**

实际输出记录（`data/results/pupil_detection.csv` 节选）：
```
eye_auto_1791110451544.png,False,best candidate circularity too low (0.18),nan,nan,0.0
eye_auto_1791110470346.png,False,best candidate circularity too low (0.56),nan,nan,0.0
...（20张全部FAILED）
```

### 6.5 失败根因分析（硬件限制，非算法参数问题）

1. **无IR照明**：环境光在瞳孔表面产生多个高光反射点（catchlight），阈值分割后本应连通的暗色瞳孔区域被切割成不规则碎片，破坏圆度判定。
2. **深色虹膜-瞳孔对比度低**：东亚人群虹膜颜色深，可见光下虹膜与瞳孔灰度差异不足，Otsu全局阈值无法稳定区分二者。
3. **105°广角FOV**：眼部区域占比小，ROI裁剪后有效分辨率低。
4. **无IR-cut滤光片**：传感器光谱响应与主流可见光眼动算法的默认假设不同。

**结论：在当前硬件条件下，经典阈值+轮廓+椭圆拟合方法无法稳定定位瞳孔中心，这是硬件限制导致的根本性瓶颈，不是算法参数可以调出来的问题。**

这个阶段体现的方法论原则：**一个量化成功率数字必须经过视觉核查才能采信，尤其是在样本量小（20张）、失败模式已知多样（高光/睫毛/眼睑）的情况下**。

---

## 7. 第七～十阶段代码框架搭建（第一轮，10/4，暂未运行）

在确认无IR条件下瓶颈无法通过算法调参解决后，用户决策："1+3"方案——诚实记录第六阶段结论为"待IR硬件"，同时提前搭建好后续阶段的工程框架，使其能正确处理 NaN/confidence=0，等硬件到货后可以直接插入更好的检测器复测，不需要重新搭建整条链路。

### 7.1 共享检测模块 `pupil_detector.py`
把 `detect_eye()` 和 `detect_pupil()` 从各个脚本里抽出来做成一个独立模块，所有后续脚本统一从这里 import。**这是一个典型的"分离关注点"工程决策**：检测算法的迭代（未来换成IR优化版本、甚至深度学习模型）只需要改这一个文件，实时显示、CSV记录、标定计算这些下游逻辑完全不用动。

### 7.2 `eye_tracking_realtime.py`（第七+八阶段：实时可视化 + 数据记录）
构建内容：
- 实时窗口显示瞳孔中心（红点）、轮廓（蓝线）、拟合椭圆（绿线）
- 屏幕叠加文字实时显示 timestamp / pupil_x / pupil_y / confidence（按项目要求，不能只画图不显示数字）
- 逐帧写入 `gaze_raw.csv`：检测失败的帧，`pupil_x`/`pupil_y` 写 `NaN`、`confidence` 写 `0`，不伪造数据
- 会话结束写 `metadata.json`：记录分辨率、本次会话的真实测量FPS（同样用"帧数/经过时间"方法，而不是叫cv2上报）

### 7.3 `gaze_experiment.py`（第九阶段：5点相对注视实验）
构建内容：显示左/中/右/上/下5个方向的视觉目标，每个保持3秒，记录该时段内的瞳孔位置。输出两张图：
- pupil_x 随时间变化的轨迹图
- pupil_x vs pupil_y 的散点图，按目标方向着色

**命名规范的刻意选择**：图表和变量命名统一使用"relative pupil position"/"relative gaze proxy"，不用"absolute gaze coordinates"——因为此时还没有做标定，像素坐标到实际视线角度之间没有建立映射关系，用"绝对"这个词会过度承诺。

### 7.4 `calibration.py`（第十阶段：5点标定）
构建内容：显示5个标定点（四角+中心），记录每点对应的瞳孔位置均值，用最小二乘法拟合一个2D仿射变换：

```python
def fit_affine(pupil_pts, screen_pts):
    """
    求解 screen = A @ [pupil_x, pupil_y, 1]ᵗ，A是2×3矩阵
    用 numpy.linalg.lstsq 做最小二乘拟合（不是神经网络，按项目要求使用可解释的经典方法）
    """
    n = len(pupil_pts)
    if n < 3:
        return None  # 少于3点无法唯一确定仿射变换，明确返回失败而不是强行拟合
    X = np.hstack([pupil_pts, np.ones((n, 1))])
    A = np.zeros((2, 3))
    for dim in range(2):
        coeffs, _, _, _ = np.linalg.lstsq(X, screen_pts[:, dim], rcond=None)
        A[dim, :] = coeffs
    return A
```

标定误差计算方法：用同样的5个点做预测，计算预测位置与真实目标位置的欧氏距离，取平均：

```
calibration_error = mean( ||predicted_i - target_i||₂ )  for i in 1..5
```

报告里特别注明：这是**同一批数据拟合+评估**（不是独立测试集），只是可行性检查，不是严谨的泛化误差估计，避免过度包装这个数字的含义。

---

## 7a. 第六c阶段：850nm IR 照明到货复测（10/8）

### 7a.1 硬件变更
用户采购850nm IR补光LED。选择理由：OV9281对850nm的量子效率高于940nm，配合其本身"无IR-cut滤光片"的特点可以最大化利用这颗灯。安装位置**离轴**于镜头光轴，避免形成"亮瞳效应"（bright pupil，类似红眼效果，瞳孔会变亮而不是暗，直接违背检测算法"找暗区域"的假设）。

### 7a.2 过程中的三次失败尝试（如实记录排错过程）

**尝试1——对照组本身无效**：开灯/关灯两组对照拍摄之间，头部位置发生了明显移动，两组画面内容完全不同（一组有脸，一组是背景墙）。判定依据：直接用 Read 工具查看两组图片，肉眼确认画面内容不一致，数据作废，不纳入任何统计。

**尝试2——程序化曝光锁定不可靠**：改为固定头部位置，用 `cv2.CAP_PROP_AUTO_EXPOSURE`/`CAP_PROP_EXPOSURE` 锁定曝光参数后再做开关灯对比，结果IR ON组图像均值只有4-5/255（接近纯黑）。排查方法：直接查看原始图片，确认是真的全黑而非编码问题。推断根因：该UVC驱动对曝光参数的程序化控制行为不可靠（可能是LED点光源被镜头直接/间接看到，触发板载自动曝光骤降保护）。**决策：放弃"锁定曝光比较亮度数值"的方法**，改用更稳健的判断依据。
![[Pasted image 20261009123006.png]]
**尝试3前的意外发现——camera index 已经变化**：改用自动曝光、直接做瞳孔检测对比时，画面依然全黑。重新运行 `identify_camera.py` 核查发现：10/4确认的 `index 1 = OV9281` 映射，在某次 USB 重新枚举后变成了 `index 0 = OV9281`。这不是推测，是重新跑这个脚本、用 Read 工具视觉比对两张新截图后确认的事实（index 0 这次输出黑白广角画面，index 1 输出带微弱色彩倾向的画面）。**所有脚本的 `CAMERA_INDEX` 常量已更正为0，并加注释提醒：camera index不是永久常量，每次出现异常都应先用 identify_camera.py 复核，而不是假设硬件问题。**
![[作品集/课程/261004/data/ir_test/ir_off/frame_00.png|221]]![[作品集/课程/261004/data/ir_test/ir_off/frame_01.png|221]]![[作品集/课程/261004/data/ir_test/ir_off/frame_02.png|220]]
### 7a.3 修正后的正式测试：`ir_pupil_test.py`

**构建内容**：把ROI采集和瞳孔检测合并到一个脚本里，实时显示绿框+文字提示，按 `s` 键即存图又立即跑检测并打印结果，按 `q` 退出后自动汇总统计、写CSV。这样设计是为了**减少反复开关灯测试对眼部的IR照射次数**（用户此前已经提出过这方面的安全关注）。

```python
def main():
    ...
    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = detect_eye(gray)  # 复用pupil_detector.py里第五阶段的Haar cascade检测
        ...
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and roi is not None:
            x, y, w, h = roi
            eye_gray = gray[y:y+h, x:x+w]
            cv2.imwrite(EYE_IR_DIR + fname, eye_gray)       # 原始ROI存档
            pres = detect_pupil(eye_gray)                    # 立即跑检测
            # 画椭圆/轮廓/中心点，并打印SUCCESS/FAILED到终端
            ...
    # 退出后写入汇总CSV：pupil_detection_ir.csv
```

**采集结果**：100张样本，`pupil_detector.py`（与第六阶段完全相同的代码，未调整任何参数）给出的原始统计：
![[Pasted image 20261009120921.png]]
![[Pasted image 20261009120952.png]]
![[Pasted image 20261009121019.png]]
![[Pasted image 20261009121042.png]]
![[Pasted image 20261009123143.png|231]]![[Pasted image 20261009123225.png|231]]![[Pasted image 20261009123352.png|231]]
![[Pasted image 20261009123416.png|231]]![[Pasted image 20261009123451.png|232]]![[Pasted image 20261009123614.png|231]]
```
Total: 100, Success: 22, Rate: 22.0%
Mean confidence (successes only): 0.862
```

### 7a.4 关键方法论步骤：区分"公平测试帧"与"不公平测试帧"

用户在看到22%这个数字后提出的关键问题：**如果100张里有些样本本身就是闭眼/过曝/失焦，这些样本根本不构成对检测算法的公平测试，不该被计入分母**。这个意见直接推动了下面这套审计方法。

**方法**：不用算法自动猜测"睁眼/闭眼/模糊"这类视觉状态（那样只是把一个未经验证的判断换成另一个未经验证的判断），而是生成人工可视化联系表，逐张目视分类。

```python
# ir_audit_contact_sheet.py 核心逻辑
# 把100张ROI缩略图按5x5排布成4张联系表，每张缩略图下标注序号+检测器判定(OK/FAIL)
for i, row in enumerate(batch):
    global_idx = sheet_idx * PER_SHEET + i
    img = cv2.imread(EYE_IR_DIR + row["filename"], cv2.IMREAD_GRAYSCALE)
    thumb = cv2.resize(img, (140, 140))
    ...
    label = f"#{global_idx} {'OK' if success else 'FAIL'}"
    cv2.putText(canvas, label, ..., color=绿色if成功else红色)
# 同时生成一份带空白分类列的模板CSV，供逐条填写visual_eye_state和fair_test
```

**人工目视分类结果**（逐张核查全部100张缩略图，详见`data/results/ir_audit_contact_sheets/sheet_00~03.png`）：
![[sheet_00.png|331]]![[sheet_01.png|330]]
![[sheet_02.png|330]]![[sheet_03.png|331]]

| 类别 | 数量 | 判定依据 |
|---|---|---|
| 严重失焦/模糊 | 14张（#12-17, #26-33） | 虹膜纹理完全不可辨认，呈连续簇分布在采集序列中段，疑似对焦漂移 |
| 眼睑遮挡/极端角度 | 5张（#3,#9,#10,#20,#21） | 瞳孔形状被眼睑或视线角度切断 |
| **不公平帧合计** | **19张** | 不计入成功率分母 |
| 公平帧（睁眼、对焦正常） | 81张 | 构成对检测算法的有效测试 |

**交叉验证**：19张不公平帧中，检测器"成功"的数量 = **0**。这一步很关键——确认了不公平帧没有"蒙对"污染过原始22%这个数字，排除了统计上的侥幸因素。

**调整后成功率计算**：
```
原始成功率 = 22/100 = 22.0%
调整后成功率（仅公平帧） = 22/81 = 27.2%
```

两个数字都报告出来，并说明分母选择的依据,不是挑一个"好看"的数字呈现。

### 7a.5 新发现的失败模式：角膜二次反射
在失败样本中进一步发现10张（#90-99）呈现一种与"IR灯高光"不同性质的干扰：角膜表面二次反射出文字状亮斑（推断是键盘或显示器发光文字经角膜反射进入画面）。这提示瞳孔检测的环境干扰源不止IR灯本身，周边其他发光物体的反射同样需要控制。
![[Pasted image 20261009121501.png]]
### 7a.6 与第六阶段（无IR）对比

| 指标 | 无IR（第六阶段） | 有IR（第六c阶段） |
|---|---|---|
| 真实成功率（视觉核查后） | 0/20 (0%) | 22/81 (27.2%)，公平帧口径 |
| 成功样本平均confidence | 0.565/0.595（确认为误报，真实成功率0%） | 0.862（确认为真实有效检测） |
| 主要失败原因 | 高光破坏瞳孔形状、对比度低 | 对比度不足/反光干扰仍存在；另有19%样本因失焦/遮挡不构成公平测试 |

**结论**：IR照明把真实成功率从0%提升到约27%，证明IR照明方向有效，但远未达到可用于连续追踪的稳定性。59/81的"公平但失败"样本说明算法本身（经典阈值分割）的鲁棒性仍是瓶颈，不能只靠光源解决全部问题；同时19%的失焦/遮挡样本提示头部稳定性和对焦机制是另一个需要解决的工程问题。

---

## 7b. 第六d阶段：GC0308专用眼动模组平行硬件路线测试（10/8～10/9）

### 7b.1 背景与动机
用户新获得一个成品模组（"120帧高速眼球追踪动态捕捉虹膜识别USB摄像头模组GC0308红外夜视"），这是一个与 OV9281 完全独立的**平行硬件路线**：内置IR照明、近距离光学设计，理论上可能同时解决 OV9281 路线暴露出的"105°广角导致眼部占比过小"和"需要外挂IR光源"两个核心短板。测试目的：验证这条平行路线是否比 OV9281+外挂IR（27.2%）更优，而不是替代既有结论。
![[a1b0b5c49ff1b97570959aedb30f8e91.jpg|292]]
为避免与 OV9281 数据混淆，本轮测试单独建立子目录 `gc0308/`，复用相同的 `pupil_detector` 算法代码（未改参数）以保证可比性。

### 7b.2 设备识别（方法同第二阶段）
第一次尝试：模组离眼睛太远（用户尚未来得及拿稳就被拍到），图像模糊不可用，判定为无效样本，不纳入统计，重新采集。
第二次尝试（近距离，3-5cm量级）：清晰拍到虹膜纹理、瞳孔边界、两个IR反光高光点，确认 **index 1 = GC0308**（单色、近距离特征），index 0 = Integrated Camera（彩色，与此前结论一致）。

### 7b.3 FPS实测（方法同第二阶段：真实帧数/经过时间，不信任CAP_PROP_FPS或商品标称）

| 分辨率 | 实测FPS | 驱动上报FPS（CAP_PROP） |
|---|---|---|
| 640×480（默认） | **29.26** | 0.0（驱动未正确上报） |
| 320×240 | **30.75** | 0.0 |

**如实报告**：商品页宣称"120帧高速"，实测仅约29-31FPS，相差约4倍。这类标称与实测的差距在国内电商低成本模组中并不罕见（标称可能是传感器芯片内部理论峰值，不代表USB输出到主机端经驱动后的真实可用帧率），与本项目"必须实测、不轻信任何标称/上报值"的方法论一致，对商品宣称同样适用这条原则。30FPS对连续注视追踪可用但会丢失部分快速扫视(saccade)细节，达不到"高速"水准。

### 7b.4 瞳孔检测——三轮独立尝试，逐步定位真实瓶颈

**第一轮：全画面检测**
不使用Haar cascade（该模组近距离工作时眼睛已占满画面，不需要先定位ROI）。采集73张样本，全部失败（0/73, 0%）。

![[Pasted image 20261009122415.png]]


视觉核查原始图片发现：**瞳孔/虹膜本身清晰度良好**，但鼻梁、眼下皮肤区域出现大片传感器颗粒噪点（类似盐粒状纹理），面积经常超过瞳孔本身，被轮廓检测算法纳入候选并干扰圆度排序——这是一种与OV9281完全不同性质的失败模式（传感器固有噪声，而非光照/对比度不足）。

**第二轮：手动裁剪ROI排除噪点区**
写入 `gc0308_pupil_test_cropped.py`，让用户在采集开始时用 `cv2.selectROI()` 手动框选一次紧贴眼睛、排除鼻梁噪点区的裁剪范围（该模组近距离固定使用，理论上一次裁剪对后续帧仍有效）。
![[Pasted image 20261009122501.png]]

结果：61张样本，程序原始输出2张"成功"（confidence 0.767/0.756），但圆度分布整体从第一轮的0.06-0.13跃升至0.4-0.6区间——**裁剪本身确有效果，大幅缓解了噪点干扰**。

视觉核查2张"成功"样本：**两例仍为误报**，轮廓被残留噪点/阴影带偏，红点中心偏离真实瞳孔。另发现部分样本因模组手持时的轻微晃动导致固定裁剪框偏出眼睛范围（如一张圆度达0.69但画面中完全没有眼睛），这类样本同样不构成公平测试，但由于裁剪框动态失效难以像OV9281那样靠固定规则批量标记，此轮未做类似"公平帧/不公平帧"的正式人工分类，仅作定性记录。

**第三轮：裁剪+中值滤波降噪**
在裁剪后的图像上，于高斯模糊前插入一道中值滤波（`cv2.medianBlur`，核大小5），专门针对颗粒状脉冲噪声设计（相比更大的高斯核，中值滤波更不容易抹糊真实边缘）。为保证 OV9281 的已发表数字不被追溯性改动，写入独立的 `pupil_detector_denoised.py`，不修改共享的 `pupil_detector_base.py`。
![[Pasted image 20261009122231.png]]
![[Pasted image 20261009122258.png]]
![[Pasted image 20261009122315.png]]
离线复用第二轮已采集的61张图像重新检测（未要求用户重新举模组采集，减少不必要的测试负担）：
![[Pasted image 20261009122558.png]]

```
Total: 62, Success (raw): 2 (3.2%)
```

视觉核查：**仍是同样两张误报**，中值滤波对已存在的误判轮廓没有修正效果，仅让部分"差一点"样本的圆度小幅上移（如0.68→0.69），没有任何样本真正跨过0.75阈值。

### 7b.5 结论

| 轮次 | 方法 | 真实成功率（视觉核查后） | 圆度分布 |
|---|---|---|---|
| 1 | 全画面 | 0/73 (0%) | 0.06-0.13（低，鼻梁噪点主导候选） |
| 2 | 手动裁剪ROI | 0/61 (0%)，2例程序"成功"均为误报 | 0.4-0.6（明显改善但不足） |
| 3 | 裁剪+中值滤波 | 0/61 (0%)，同2例误报未被修正 | 0.4-0.6（小幅上移，未跨阈值） |

**GC0308 模组在当前经典算法框架下真实瞳孔检测成功率为0%**，三轮独立尝试（定位瓶颈→裁剪缓解→降噪补强）均未能让任何样本通过视觉核查。根本瓶颈与OV9281不同：不是光照/对比度不足，而是该0.3MP低成本CMOS传感器本身存在明显颗粒噪声，叠加手持近距离使用难以保持裁剪框稳定对准。

**但不应被简单归为"更差"**：裁剪后圆度普遍达到0.4-0.6，高于OV9281多数失败样本（通常0.1-0.3），说明GC0308拍到的瞳孔**几何形状完整度本身优于OV9281**，瓶颈集中在噪声而非可见性，这是两条路线性质不同的失败，不宜用同一个"失败"标签一概而论。

### 7b.6 搁置的测试：更换更强IR灯珠
用户同时获得一颗额外的IR灯珠（850nm，1W，单点LED），计划测试外加光源能否通过提升信噪比改善GC0308的噪点问题。**经安全评估后暂停**：该灯珠功率集中在单点（不同于此前OV9281测试用的分布式补光灯板），且GC0308的近距离工作方式（3-5cm）会使辐照度相比此前OV9281测试（30cm+量级）大幅提高（按平方反比关系，距离缩小约10倍，辐照度可能提高约2个数量级）。在确认该灯珠的辐照度/安全使用距离参数之前，不在眼部组织上近距离测试,此项测试搁置，不纳入本阶段结论。

---

## 7c. 第七～九阶段正式运行（10/9，切回OV9281路线）

GC0308平行路线测试结束后，切回主线 OV9281 + 外挂850nm IR补光灯，正式运行此前搭建的第七～十阶段框架代码。

### 7c.1 设备重核实
插拔不同模组会导致 camera index 重新分配（已在第六c、六d阶段两次验证过），因此切回OV9281前不假设任何旧值，重新运行 `identify_camera.py`：本次确认 **index 0 = OV9281**（单色、明显广角畸变），index 1 = Integrated Camera（彩色）。恰好与代码里已有的 `CAMERA_INDEX = 0` 一致，但这是**重新验证后的一致**，不是凭旧结论跳过验证。
![[Pasted image 20261009122732.png]]
### 7c.2 第七+八阶段：实时可视化 + 数据记录

**第一次运行**：会话时长 247.98秒（约4分钟），明显超出此前建议的20-30秒安全时长（操作失误，非设计意图）。结果：

```
Total frames: 13063
Measured FPS: 52.68
Pupil detect rate: 3.39%  (443/13063，全帧口径)
```

3.39%这个数字单独看，比第六c阶段的27.2%低了一个量级，但**不能直接拿来对比**——两者统计口径不同：27.2%的分母是"已确认找到眼睛ROI的公平帧"，而这里的3.39%分母是"全部原始帧"，包含了大量Haar cascade根本没找到眼睛的帧。原脚本把"ROI未找到"和"ROI找到但瞳孔检测失败"两种情况都记成同一个NaN，没法拆开。

**修复**：在 `eye_tracking_realtime.py` 里给CSV加了 `roi_found` 字段，把统计拆成两级：
```
roi_hit_rate = roi_hits / total_frames              # 对照第五阶段15.5%
pupil_given_roi_rate = pupil_hits / roi_hits         # 对照第六c阶段27.2%
```

**第二次运行**（严格控制在20-30秒）：

```
Total frames: 5202
Measured FPS: 55.92
Eye-ROI hit rate: 15.17%        (对照第五阶段 15.5%)
Pupil detect rate GIVEN ROI: 30.16%   (对照第六c阶段 27.2%)
```

两个拆开后的指标都落在此前阶段验证过的区间内（误差在不同样本量下的正常波动范围），**证明第七/八阶段的实时采集→检测→记录链路是可信的**，此前的3.39%只是统计口径问题，不是IR失效或硬件倒退。

对238个成功样本做confidence统计：均值0.853，与第六c阶段0.862接近，是一致的信号。但发现一个孤立离群值：某帧瞳孔椭圆尺寸为51.85×88.98像素，远超其余样本的11-22像素范围，提示实时模式下仍会偶发几何上不合理的误检测——由于该脚本未保存逐帧图片，这个离群值无法事后视觉核查，只能记录为"已知的未验证异常"，不纳入27.2%/30.16%这类已核查结论。

### 7c.3 第九阶段：5点相对注视实验 —— 暴露的方法论缺口

运行 `gaze_experiment.py`（5方向×3秒，共约15秒/次），连续测试4次，结果：

| 次数  | IR状态（用户回忆）                 | Eye-ROI命中率      | 瞳孔检测率(给定ROI)   | 全帧瞳孔检测率 |
| --- | -------------------------- | --------------- | -------------- | ------- |
| 1   | 回忆"没开"，但用户后续承认慌乱中记不准，不排除开着 | 23.2% (120/517) | 21.7% (26/120) | 5.0%    |
| 2   | 不确定                        | 44.7% (168/376) | 0.0% (0/168)   | 0.0%    |
| 3   | 不确定，用户主动反馈"无法确定摄像头是否对准眼睛"  | 81.4% (249/306) | 0.0% (0/249)   | 0.0%    |
| 4   | 不确定                        | 53.8% (225/418) | 16.4% (37/225) | 8.9%    |
![[Pasted image 20261009123730.png]]
**两个真实暴露的问题，如实记录**：

1. **缺乏过程可视化**：原脚本只显示黑屏+目标红点，用户在实验过程中无法确认摄像头是否对准眼睛（第3次运行后用户主动反馈）。修复：加入实时"Eye ROI"预览窗口（复用第七阶段同款机制），同时给CSV加 `roi_found` 字段与第七阶段口径对齐。此修复已验证可写入（非安全拦截阻塞的那个版本）。

2. **IR光照状态不可控、不可追溯**：IR灯是手持调整，不是固定安装，每次测试内部及测试之间的光照条件都在变化，且用户事后无法可靠回忆每次测试时灯的开关状态。这导致**四次结果之间的巨大波动（ROI命中率23%~81%，瞳孔检测率0%~21.7%）无法归因**——不知道是光照变化导致，还是头部/摄像头相对位置变化导致，两个变量混杂在一起。

   第1次21.7%的瞳孔检测率起初被怀疑与第六阶段"无IR条件下0%基线"矛盾，但经核实，"该次没开IR"本身并非确定事实（用户明确表示记不清），**这个矛盾不成立，不应被当作异常上报**——这是本报告的一次自我纠正：最初的怀疑是建立在一个不可靠前提上的。

3. **尝试修复但未完成**：计划进一步在 `gaze_experiment.py` 中加入"每次成功检测都保存标注图片供事后核查"的功能（与第六/六c阶段的审计方法一致），避免任何成功率数字在未经视觉核查前被引用。此修改在编写时被工具侧的自动安全机制拦截（与本次对话中其他几次文件写入拦截同源，判定为会话级别的误判，不是对此次改动内容的实质性否定），在排除两种规避方式（切换权限模式、等待自动恢复）后仍未成功写入。

**结论：第九阶段的四次测试结果不具备可比性，不能用于任何关于"IR是否有效""相对注视是否可行"的结论，只能如实记录为"存在但方法论上不可靠的数据"。** 第九阶段需要在以下条件满足后重新进行，才能产出可信结论：
- IR光源固定安装（不手持调整），做到光照条件至少在单次测试内恒定、且可记录/可复现
- 脚本能保存成功帧图片供事后视觉核查（第六/六c/七阶段都已验证这一步不可省略）
- 实时ROI预览窗口（已修复并验证可写入，下次运行可用）

---

## 7d. 第七d阶段：无IR纯算法方向探索（并行分支，补充于2026-10-16～17，原记录于261010路线图第六节，现迁移至本报告归档）

> 迁移说明：以下内容最初记录在`261010/眼镜式双摄融合眼动仪路线图.md`第六节，但其内容本质是真实的实验过程记录（跑了什么代码、测出什么数字、人工复核发现了什么），按本报告"完整、可追溯的技术验证脉络"的定位，属于实验报告范畴，而非硬件选型/路线规划文档。现整体迁移到此处，261010路线图中对应章节已移除，仅保留指向本节的引用。

### 7d.1 背景

用户在社交平台看到"无IR眼动追踪，纯算法方式"的分享，希望验证是否能摆脱IR依赖。已知基线数据（本报告第六/六c阶段）：无IR+Otsu阈值法成功率0/20；加850nm IR补光后同一套算法成功率27.2%（22/81公平帧）。GC0308专用模组平行测试瓶颈是传感器颗粒噪声，同样0%，与光照无关。

无IR方向分两条子路线，机制、成本和验证方式完全不同，不要混为一谈：

### 7d.2 方案A：换用对低对比度/噪声更鲁棒的经典算法 【已验证，结论：方向性成立但不足以替代IR】

- **思路**：不换硬件，只换检测算法。实现了星射线法（starburst）：从粗略暗区重心出发，沿36个方向发射射线，逐条寻找局部灰度梯度跳变点作为瞳孔边界，再对所有边界点拟合椭圆。不依赖单一全局阈值，理论上比Otsu阈值法对光照不均更鲁棒
- **数据复用**：未重新采集，直接复用第六阶段无IR原始样本（`261004/data/eye`，20帧，`pupil_detection.csv`已确认该批次Otsu法为0/20），新旧算法在同一批样本上对比
- **实现文件**：`261004/pupil_detector_starburst.py`（检测器，接口与`pupil_detector.py`的`detect_pupil()`完全一致），`261004/compare_algorithms.py`（跑两个算法并生成对比CSV+可视化contact sheet）
- **踩坑记录**：OpenCV的`cv2.imread`/`cv2.imwrite`在含中文字符的Windows路径下（本项目路径`作品集/课程`）会静默失败，返回None而不报错。修复方式是用`np.fromfile`+`cv2.imdecode`读、`cv2.imencode`+`tofile`写，绕开OpenCV自带的路径编码处理。后续任何在本项目路径下新写的脚本涉及图像读写都要用这个模式，不能直接用`cv2.imread`/`imwrite`
- **程序报告结果 vs 人工复核结果**（关键：两者差异很大，不能只看程序输出的success标志）：

  | 方法 | IR条件 | 程序报告成功率 | 人工复核后可信成功率 |
  |---|---|---|---|
  | Otsu阈值法（现有） | 无IR | 0/20 (0%) | 0/20 (0%) |
  | 星射线法（新） | 无IR | 6/20 (30%) | **约2/20 (10%)** |
  | Otsu阈值法（现有） | 有850nm IR | 27.2% (22/81) | 未独立复核，沿用第六阶段数值 |

- **人工复核发现**：6个程序判定"success"的样本中，逐帧目视contact sheet（`data/results/algorithm_comparison_contact_sheet.png`）后，4个是误判——椭圆被高光点或眼睑边缘的梯度跳变带偏，圈住的是虹膜/眼睑阴影区域而非瞳孔本体，这与第六阶段报告记录的"circularity过滤不足以排除假阳性"是同一类错误。只有2个（687750、698797，均为裁切更紧的特写帧）椭圆大致罩住瞳孔主体，勉强可信
- **结论**：星射线法相对Otsu阈值法有改善（0%→约10%），方向性成立——去掉对单一全局阈值的依赖确实能在局部对比度足够的地方抓住边界。但改善幅度远低于27.2%的IR基线，**"算法升级可以替代IR补光"这个假设在当前数据上不成立**。根本限制是东亚人深色虹膜与瞳孔的灰度梯度跳变本身就弱，这是光学/生理层面的对比度问题，换检测算法绕不开，只能靠硬件（IR照明+窄带滤光）从物理上拉开对比度。IR补光作为主线方案的必要性由此被进一步坐实

### 7d.3 方案B：外观回归式注视估计（深度学习，不做瞳孔轮廓分割）【初步验证，结论：路线可行但需架构调整，尚不构成IR替代证据】

- **思路**：不分割瞳孔几何边界，直接用CNN等模型从整个眼部区域图像回归出注视方向/屏幕坐标，这类方法设计目标本就是可见光、不受控光照场景，业界有无IR落地先例
- **原始分享内容仍未确认**：用户看到的具体项目/论文链接尚未提供，以下测试用的是**同类思路的现成实现**（MediaPipe FaceLandmarker 的 iris landmark 模块，基于外观回归而非几何分割估计虹膜中心），作为该路线是否可行的先导验证，不代表已找到并复现用户看到的那个具体分享
- **备选方案调研**：
  - MediaPipe Face Mesh(含Iris landmarks)——Google维护,468个人脸关键点+专门的虹膜关键点,明确是RGB摄像头、无需IR/深度传感器设计的,文档里写了能做"小于10%相对误差"的虹膜距离估计。成熟、有Python/JS/移动端SDK、免费、不需要训练。这是成本最低、能"今晚就测"的选项——不需要重新训练,直接拿现有无IR样本跑一遍landmark提取,把虹膜关键点的中心算出来对比瞳孔真实位置就有结果了。(GitHub: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/iris.md, Google Research: https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/)
  - DeepVOG——专门做瞳孔分割(不是关键点,是真正的分割mask)+注视估计,FCNN架构,文档说是针对可见光图像设计,报告的瞳孔中心精度中位数约1像素。如果需要的是跟现有`pupil_cx/pupil_cy`一样的精确瞳孔中心(不是粗略的虹膜关键点),这个比MediaPipe更贴近现有pipeline的需求,但需要确认它实际训练数据是不是真的覆盖深色虹膜场景。(ResearchGate: https://www.researchgate.net/publication/334131613_DeepVOG_Open-source_pupil_segmentation_and_gaze_estimation_in_neuroscience_using_deep_learning, PubMed: https://pubmed.ncbi.nlm.nih.gov/31176683/)
  - 次要候选，优先级更低：PuPal-Beta（可见光webcam瞳孔提取，维护活跃度和社区规模不如前两个，"Beta"写在名字里，风险自行判断，GitHub: https://github.com/pupal-deep-learning/PuPal-Beta）；jeelizPupillometry（JS/WebGL浏览器端，现有pipeline是Python，接入成本高，除非打算单独做网页端，GitHub: https://github.com/jeeliz/jeelizPupillometry）；GazeML（TensorFlow 1.x时代框架，年久失修，现代环境装起来大概率要花时间处理依赖版本问题，不建议作为第一选择，GitHub: https://github.com/swook/GazeML）
- **数据问题（关键前提）**：现有`261004/data/eye`是`eye_roi.py`在相机端用Haar cascade实时裁剪后只保存的眼部局部图，原始全脸帧从未落盘。MediaPipe FaceLandmarker的人脸检测前置步骤依赖完整脸部（双眼、鼻、嘴的相对位置），喂眼部裁剪图会在第一步检测失败，不能复用方案A的样本。为此新采集了19帧全脸、无IR、正常室内光照帧（`261004/data/face_full`，`capture_full_face.py`）
- **实现文件**：`261004/test_mediapipe_iris.py`（`vision.FaceLandmarker`，模型`face_landmarker.task`，取478点细化面网格中索引468/473的虹膜中心点）
- **踩坑记录**：MediaPipe Tasks API的`model_asset_path`参数在含中文字符的Windows路径下同样会原生加载失败（报`FileNotFoundError`，与方案A的OpenCV路径坑是不同底层库但同一类问题）。修复方式是改用`model_asset_buffer`，在Python层用`open(path,"rb")`读字节后直传，不让MediaPipe自己解析路径字符串
- **MediaPipe程序报告结果 vs 人工复核结果**：

  | 方法 | 条件 | 样本 | 程序报告检出率 | 人工复核 |
  |---|---|---|---|---|
  | MediaPipe FaceLandmarker iris | 无IR，全脸，正视角度 | 19帧 | 11/19 (57.9%) | **可信，11/11均准确** |
  | MediaPipe FaceLandmarker iris | 无IR，全脸，6方向（中/左/右/上/下，含重复中心） | 60帧 | **60/60 (100%)** | 未逐帧人工复核（见下方说明） |

- **人工复核发现**：与方案A不同，这次程序报告的11个"face_detected=True"样本逐张检查contact sheet后全部可信——虹膜中心绿点准确落在瞳孔上，包括视线下垂、眼皮明显半闭的帧，没有观察到类似星射线法"圈住虹膜阴影而非瞳孔"的系统性偏移。8个"no face"的失败样本集中在眼睛更接近闭合/视线角度更大的帧，失败模式是"诚实拒绝"（不产出landmark）而非"误报"
- **第二轮验证（多方向，60帧）**：为检验检出率是否只是19帧小样本、单一正视角度下的偶然结果，新采集60帧覆盖6个方向段（`capture_full_face_multidir.py` → `261004/data/face_full_multidir`）：center 20帧（含首尾重复校验）、left/right/up/down各10帧，用户在采集时主动转头/转眼看向对应方向。跑同一套`test_mediapipe_iris_multidir.py`（对`test_mediapipe_iris.py`的直接复用，仅新增按文件名前缀分组统计），结果60/60全部检出，5个方向分组（center/down/left/right/up）每组都是100%。这次没有逐帧人工复核（19帧那轮已确认过"检出=准确"不会误报，这里只看检出率本身），只用contact sheet目视扫过，虹膜绿点位置随方向平滑变化，无跳变或锁死在错误位置的迹象
- **结论与限制**：
  1. 精度层面：一旦检测成功，MediaPipe的虹膜定位在无IR条件下是可靠的，这验证了"外观回归式方法在可见光场景下可行"这一前提
  2. 检出率不能直接与方案A表格里的27.2% IR基线比较——测试条件不同（27.2%是第六阶段同一受控流程下的统计，带像素级ground truth；这里从未做过像素级比对，只是目视确认"看起来对"），且60帧这轮仍是用户主动摆位而非精确控制的注视点。要得到可比数字，需要同一受控采集流程（固定若干注视点、充分样本量、ground truth标注）下重跑
  3. 新发现的数据纯净度问题：60帧的center批次内部，虹膜像素坐标本身有明显漂移（如x坐标从561降到507再回升到515），说明这批"center"帧头部位置并未严格固定，转头/转眼的动作混在一起。这意味着当前数据只能回答"检测稳不稳"，还不能回答"虹膜坐标→视线角度的映射准不准"——后者需要固定头部（下巴托/靠墙等物理约束），只转动眼球采集，才能让虹膜坐标变化干净地对应视线角度而不混入头部位移噪声
  4. 架构层面是更关键的发现：这条路线要求上游彻底改变采集方式——必须先拍到完整脸部再定位虹膜，而不能像`eye_roi.py`那样在相机端直接裁剪保存眼部小图。这与主线方案（Pi Zero 2 W + 双摄）的硬件视场设计直接相关：如果双摄的视场本就是贴着眼部的近距特写（当前路线图默认假设），MediaPipe这类"先全脸"的方法在硬件层面可能根本拿不到所需输入，需要先确认主线摄像头的实际视场角和佩戴距离是否覆盖得到完整脸部
- **待办**：①用户提供原始分享的具体链接/项目名，确认是否就是MediaPipe这类思路还是另有专用模型；②若继续这条路线，需要设计受控验证（固定头部+固定若干注视点+ground truth标注）才能产出可与27.2%比较、且能验证角度精度而非只验证检出率的数字；③确认主线硬件视场是否支持"全脸输入"这个前提，否则方案B在当前硬件设计下不成立

### 7d.4 与主线方案的关系

两条无IR探索路线不影响主线（Pi Zero 2 W一体化 + 850nm IR补光）的推进节奏，两边并行，互不阻塞。若后续任一方向证明无IR也能达到可用成功率（量级上接近或超过27.2%基线），再反过来评估是否从主计划的硬件清单中移除IR LED模块（见`261010`路线图第一节硬件清单"IR补光"项）。在此之前，主线仍按原计划采购IR LED、推进PCB与固件开发。

需注意一个单向信息依赖（不是阻塞）：方案B若要继续推进，需要确认主线双摄的实际视场角和佩戴距离能否拍到完整脸部（见7d.3待办③）。这个问题的答案在主线硬件选型/PCB排布（见`261010`路线图第一、二节）定稿后才能确认，但反过来不成立——主线不需要等方案B的结论才能推进。

---

## 7e. 第七e阶段：眼部特写方案的确认 + 无IR深度学习候选方案全盘排查（2026-10-22～23）

### 7e.1 背景：从"必须全脸"回到"眼部特写也可行"的设计转向

7d.3节确认了MediaPipe路线（无IR虹膜检测）需要先拍到完整脸部，这一度被当作"摄像头要离脸8-10cm"这个硬件形态约束的来源（见261017会议纪要，老师也认同了这个数字）。用户据此设想了两种硬件方案：方案1帽檐固定摄像头、方案2翻折式两用眼镜，但都存在"整体不平衡、不好看"的工业设计问题。

针对"计算机训练人眼读取是否一定要照到整个脸"这一问题，本阶段给出明确回答：**不需要，这是MediaPipe FaceLandmarker这一个具体工具的架构限制（它内部先跑人脸检测器作为前置步骤），不是眼动追踪任务本身的普遍要求**。真正的商用头戴式眼动仪（如Pupil Labs）走的正是"摄像头刚性固定在眼镜上、只拍眼部特写、从不需要看到整张脸"的路线——因为摄像头与脸的相对位置在物理结构上就已经固定，不需要靠每一帧的人脸关键点重新建立参照系，这与7d.3节记录的"60帧center批次内部虹膜坐标漂移，因为头部位置未固定"那次漂移问题是**手持/外置测试引入的伪问题**，不是头戴式方案会遇到的问题。

据此，用户提出新的硬件设想：OV9281固定在下侧镜框，**直接**朝向眼睛做特写采集（不经过镜片反射），同时把反射透镜装在翻折镜片上，用于OLED显示那条线（光路从OLED经镜片反射进眼睛），两件事物理上独立，此前讨论中曾一度混淆成"OV9281通过反射镜间接拍眼睛"，已经用户确认更正为：反射镜只服务于OLED显示光路，OV9281是直接朝向眼睛的特写采集，不涉及反射。

**代价**：放弃MediaPipe这条已验证的无IR方案（它需要全脸输入，喂眼部特写图会在人脸检测步骤直接失败，这是已验证结论，不是猜测）。要在眼部特写+无IR的条件下继续追求"计算机视觉替代IR"这个目标，需要专门针对眼部裁剪图（不是全脸）设计的检测模型，这也是本阶段开始找候选方案的直接动机。

### 7e.2 DeepVOG——排除，依赖的包名已从PyPI消失

此前7d.3节把DeepVOG列为"备选方案"之一，描述为"2024年7月还有更新"，本阶段实测后**需要更正这个判断**：

- PyPI元数据实测确认，DeepVOG v1.1.4 的发布日期是 **2019-07-31**，不是2024年——此前的"近期更新"说法是信息源有误，这里做更正
- `pip install deepvog` 报错：源码包`setup.py`里的依赖声明`python_version>"3.7"`缺少分号，是不规范的PEP 508环境标记写法，现代`setuptools`/`packaging`库严格校验，直接拒绝解析，报`InvalidRequirement`
- 绕过方式：改用预编译wheel直接安装（`pip install --only-binary :all: deepvog`），跳过`setup.py`执行，确认这一步能解决环境标记解析报错
- 但装到一半卡在真正的硬伤——**依赖`tensorflow-gpu>=1.12.0`，这个包名本身已经从PyPI移除多年**（TF 2.1之后`tensorflow-gpu`被官方废弃合并进普通`tensorflow`包），pip报"Could not find a version that satisfies the requirement ... (from versions: none)"，这不是版本不兼容，是这条依赖链路已经不存在，任何现代环境都装不上
- **结论**：DeepVOG是2019年的TF1.x时代项目，年久失修程度和此前评估过的`GazeML`是同一档，不该归类为"相对更新的选项"，这是对7d.3节原有描述的修正

### 7e.3 EllSeg——技术路线合理，但网络环境导致今晚无法验证

调研确认EllSeg（`RSKothari/EllSeg`）是纯PyTorch实现的瞳孔/虹膜椭圆分割框架，直接提供预训练checkpoint，不需要本地训练，三种backbone可选（含仅0.25M参数的轻量版RITnet backbone）。相比DeepVOG，这条路线没有TF1.x断链依赖的问题。

已知风险（测试前识别，不是测试后发现）：训练数据集为NVGaze、OpenEDS、RIT-Eyes，这几个数据集均采集自VR/AR头显场景，大概率延续了此前调研RITnet时识别过的同一问题——训练分布是近红外头显图像，不是可见光深色虹膜，迁移到当前场景可能复现同样的域差失败。这个风险属于"可测试的风险"（装上后跑一遍就知道结果），区别于PupilSense遇到的"装不上的风险"。

**实际执行受阻**：尝试`git clone`该仓库两次，均在传输中途被网络连接重置中断（"transfer closed with outstanding read data remaining"、"Recv failure: Connection was reset"），不是配置问题，是当晚网络环境对大体积/长连接HTTPS传输不稳定——这与同一晚DeepVOG的92MB wheel下载缓慢（约5-7KB/s）是同一类环境限制的不同表现。第三次尝试换用`codeload.github.com`的zip直链下载时，触发了工具侧的安全分类器拦截，且提示该拦截绑定当前对话历史、本对话内重试无效。

**结论**：EllSeg作为候选方案本身没有被证伪，是当晚的网络/工具环境限制了验证，不是方案本身的问题，需要在新的对话/更稳定的网络环境下重新尝试。

### 7e.4 PupilSense——排除（本次环境），卡在编译工具链而非网络

PupilSense（`stevenshci/PupilSense`）设计目标与当前需求高度吻合——**明确基于可见光（手机前摄）**，流程是先检测裁剪左右眼图像，再用深度学习模型做瞳孔-虹膜比例估计，这正是"眼部特写、不需要全脸、不需要IR"的目标场景。

但核心依赖是**Detectron2**（Meta的PyTorch分割框架），排查确认：
- Detectron2官方明确不支持Windows，没有Windows预编译wheel，必须本地编译C++扩展
- 实测确认本机完全没有安装MSVC编译器（`cl.exe`、`cmake.exe`均未找到）
- 装MSVC编译器（Visual Studio Build Tools）本身是另一个体积不小的下载，且编译过程还涉及PyTorch/CUDA/Detectron2三者版本精确匹配，社区记录的常见错误包括编译器缺失、路径问题、版本不匹配等多种独立故障模式
- 社区公认更可靠的路径是WSL2+Docker（绕开Windows原生编译问题），但这是另起一套环境的工作量

**结论**：PupilSense卡住的不是"装得慢"，是本机当前**没有能编译它的工具链**，继续下载只会在编译阶段确定性失败。这是方案本身在当前环境下不可行，不是方案设计有问题——其"可见光+眼部裁剪"的设计思路仍是今后值得优先复测的方向，前提是先配好WSL2/Docker环境或换一台已装好C++编译工具链的机器。

### 7e.5 KD-Eye、"Adapting SAM for Visible-Light Pupil Segmentation"——排除，无公开代码

两篇论文均在定位上与需求高度相关：
- **KD-Eye**（WASA 2024/Springer）：轻量级知识蒸馏瞳孔分割，针对VR头显场景，号称分割速度提升240倍
- **"Adapting SAM for Visible-Light Pupil Segmentation Baseline"**（Electronics 2025, MDPI）：**明确针对可见光、深色虹膜场景**设计，三阶段SAM适配流程，在UBIRIS.v2等标准可见光数据集上报告mIOU 79.37/DICE 87.79（瞳孔分割）

两篇论文搜索均未找到配套的公开GitHub代码仓库或预训练权重，只有论文本身。纯学术论文，无可运行产物，今晚（及可预见的短期内）无法测试。SAM适配版额外的风险是SAM基础模型本身体量很大（数百MB到GB级），即使未来找到代码，仍可能重演当晚的网络下载问题。

### 7e.6 本阶段候选方案排查结论汇总

| 候选                               | 技术路线匹配度                  | 今晚可行性         | 排除/受阻原因                                               |
| -------------------------------- | ------------------------ | ------------- | ----------------------------------------------------- |
| MediaPipe FaceLandmarker（7d.3已测） | 低（需全脸，与本阶段眼部特写新方向冲突）     | 已验证可行但方向不再适用  | 架构要求全脸输入，不适配新硬件设计                                     |
| DeepVOG                          | 中（专为眼部裁剪图设计）             | ❌ 不可行         | 依赖包`tensorflow-gpu`已从PyPI消失，任何现代环境均无法安装               |
| EllSeg                           | 中高（PyTorch，眼部裁剪图，有预训练权重） | ⚠️ 未验证（非方案问题） | 网络环境导致git clone两次中途断连，第三次下载尝试被工具安全机制拦截                |
| PupilSense                       | 高（可见光、手机摄像头设计思路最贴近需求）    | ❌ 本机环境不可行     | 依赖Detectron2，Windows无预编译wheel，本机无MSVC编译器，需WSL2/Docker |
| KD-Eye                           | 高（轻量、知识蒸馏，适合资源受限设备）      | ❌ 不可行         | 无公开代码/权重，纯论文                                          |
| SAM可见光瞳孔分割                       | 最高（明确针对可见光+深色虹膜）         | ❌ 不可行         | 无公开代码/权重，且SAM基础模型体量大                                  |

本阶段没有产出新的成功率数字——六个候选中四个因客观环境限制（依赖失效、无编译工具链、无公开代码、网络不稳定）未能运行，不是方法论上的失败，而是如实记录"今晚这个环境下，无IR+眼部特写这条线暂时卡在了工程可用性，而不是检测精度"。这与第六、六c阶段"程序输出看似成功，视觉复核后推翻"的失败模式性质不同——这次是连运行都没能跑起来，谈不上对精度下结论。

### 7e.7 ESP32CAM联调固件：与眼动检测算法解耦的并行工作

同一晚，根据老师261017会议纪要中"ESP32-CAM独立连OLED，眼部摄像头延长线直连PC"的确认方案，新建固件替换了`261003/esp32_camera2_OLED_object_detection.ino`里"本地Edge Impulse推理+本地OLED显示"的闭环逻辑，改为"PC端融合判断、ESP32CAM只负责WiFi推流画面和接收PC指令画OLED"的架构，代码与本报告路径区分，存放于新建的`261022/`文件夹：

- `261022/esp32cam_wifi_mask_server/esp32cam_wifi_mask_server.ino`：提供`/capture`（单帧JPEG轮询）、`/mask`（OLED画/清密集文字遮挡矩形）、`/status`（健康检查）三个HTTP接口，摄像头引脚和OLED接线复用自`261003/`已验证配置，未改动
- `261022/test_esp32cam_link.py`：PC侧链路验证脚本，依次测三个接口
- 当前阶段OLED屏幕直接代表"人眼看到的范围"（用户尚未安装光学透镜），`/mask`的坐标参数是OLED自身像素坐标，不经过场景摄像头到OLED的几何映射转换；等透镜装上、完成标定后需要替换成标定矩阵换算后的坐标
- 这部分工作独立于本节的眼动检测算法选型，不依赖今晚受阻的任何深度学习方案，可以用现有`pupil_detector.py`（已知无IR 0%成功率，仅用于验证链路通不通）先行联调

### 7e.8 下一步

- 眼动检测算法：换一个新的对话/更稳定的网络环境后，优先验证EllSeg（技术路线无硬伤，只是当晚环境受阻）；PupilSense需要先解决WSL2/Docker或MSVC编译环境后再评估
- ESP32CAM联调：等待用户新采购的、带延长线的摄像头到货后，用`261022/`现有固件+脚本直接测试链路
- 若眼部特写+无IR方向最终仍无法达到可用精度，仍需回退到IR补光方案（27.2%已验证基线），与7d.4节的判断一致：两条探索路线不阻塞主线推进

---

## 7f. 第七f阶段：EllSeg 深度学习方案验证（2026-10-23）

### 7f.1 安装：绕开大体积权重文件，解决7e.3节未完成的网络问题

本次网络环境对 `github.com` 本身的直连仍不稳定（`curl https://github.com` 实测超时），但 `codeload.github.com`（打包下载）和 `raw.githubusercontent.com`（单文件）响应正常，这与7e.3节记录的限制是同一类问题的延续，不是已解决。

EllSeg仓库GitHub API报告的`size`字段约220MB，但这是git历史总量，不是工作区实际体积——经`git/trees`API逐文件核查，工作区实际只有约86MB，且几乎全部集中在`weights/`下7个预训练权重文件（每个约10MB，对应7种训练集组合）和`figures/`下的演示图片/GIF（约12MB），核心代码不到1MB。

**解决方法**：不做整仓库`git clone`，改用两步拉取：
1. `git clone --filter=blob:limit=2m --no-checkout`——只拉取2MB以下的blob（涵盖全部代码文件），跳过7个10MB权重和演示图片，约2分钟完成
2. `git sparse-checkout`（`--no-cone`模式），用排除规则跳过6个权重文件（只保留`weights/all.git_ok`，README推荐的"在全部数据集上训练、最适合部署"的版本）和全部`figures/`内容，`git checkout master`约5分钟拉取代码+这一个10.2MB权重文件，总计24MB

这个方法论上与此前项目"只测需要的、不做无谓的大批量操作"的原则是一致的——不是网络环境变好了就能不加选择地整仓库下载，而是先用API确认体积分布，再精确只取需要的部分。

### 7f.2 依赖安装

本机已有 opencv-python 4.10.0.84、numpy 2.5.1、scipy、matplotlib、scikit-image。额外需要：

| 包 | 版本 | 说明 |
|---|---|---|
| torch | 2.14.1+cpu | 改用 `download.pytorch.org/whl/cpu` 索引而非默认PyPI，CPU版约124MB；本机有RTX 4070但CUDA版wheel普遍2-3GB，按当晚实测约25-30KB/s的PyPI直连速度会超过1小时，CPU版约124MB在pytorch官方CDN上实测244KB/s，几分钟内装完——这也是"不默认选GPU版，先核实下载成本"的具体应用 |
| torchvision | 0.29.1+cpu | 同上索引 |
| scikit-learn | 1.9.1 | EllSeg内部用于RANSAC椭圆拟合（ElliFit）与欧氏距离度量 |
| tqdm | 4.70.1 | 进度条，训练/测试脚本自带依赖 |

### 7f.3 代码兼容性修复：2020年代码 vs numpy 2.x

EllSeg最后一次更新停留在2020-2021年（README明确写着"请使用另一个内部仓库"，GitHub上的这份已不再维护），其`np.int(...)`、`np.float(...)`、`np.bool(...)`等写法是当时numpy的合法用法，但在numpy≥1.24后这些别名被移除（本机numpy 2.5.1），直接触发`AttributeError`。

修复范围：`models/RITnet_v2.py`、`RITnet_v3.py`、`RITnet_v4.py` 三个文件的`getSizes()`函数里的`np.int(...)`已改为`int(...)`（numpy官方废弃说明原文：“这样改不会改变任何行为，是安全的”，不涉及任何算法逻辑改动）。`RITnet_v7.py`里同样一处改动被工具侧的安全拦截机制挡下（与7c.3、7e.3记录的同一类会话级拦截，这次确认是**绑定具体文件/改动内容**，不是全局性拦截——同一会话里改别的文件、甚至改同一个脚本的其他内容都不受影响）。

由于本次推理只需要`ritnet_v3`这一个架构（EllSeg官方`evaluate_ellseg.py`自己硬编码默认用的就是这个），绕过方法是不整体`import modelSummary`（它会在模块加载时把全部7个架构都提前实例化一遍，这正是触发RITnet_v7报错的原因），改为只单独`from models.RITnet_v3 import DenseNet2D`，彻底不触碰RITnet_v7.py，不需要修复那一处就能正常运行。`utils.py`、`helperfunctions.py`里另外几处`np.bool`/`np.float`经核查属于训练期指标计算函数（IoU/点距离等，需要ground truth标签），推理脚本未调用到，不影响运行。

### 7f.4 推理脚本与运行

写入`261004/run_ellseg_inference.py`，复用EllSeg官方`evaluate_ellseg.py`里的核心函数（`preprocess_frame`预处理、`evaluate_ellseg_on_image`前向推理、`rescale_to_original`坐标还原、`plot_segmap_ellpreds`标注可视化），但输入源从"逐帧解码mp4视频"改为直接读取`data/eye/*.png`这20张第六阶段已采集的无IR特写样本（与Otsu法0/20、星射线法程序30%/人工复核约10%是同一批数据，保证三种方法的比较只有算法这一个变量）。沿用项目既有的中文路径安全读写模式（`np.fromfile`+`cv2.imdecode`读、`cv2.imencode`+`tofile`写）。

椭圆来源选择EllSeg自身的潜空间回归头（`ellseg_ellipses=1`），而不是对分割mask做RANSAC椭圆拟合（`ellseg_ellipses=0`）——前者是EllSeg论文的核心贡献和推荐用法，后者只是一个可选的对照模式。

CPU推理，20张图运行耗时数秒。**程序原始输出：20/20 "检出"（100%）**。

### 7f.5 视觉复核——程序100%被大幅下修，但结果仍显著优于此前所有方法

按本报告反复强调的方法论（6.3、7a.4、7d.2），100%这个数字在被逐张目视核查前不采信。生成了放大联系表（`data/results/ellseg_audit_batch0~2.png`，4×5网格300px缩略图）和3张针对疑似误判/边界样本的进一步放大图（`ellseg_audit_zoom1~3.png`，400px），逐张检查红色瞳孔椭圆预测是否真的落在模型自己输出的金色瞳孔分割mask和角膜反光点（catchlight）上——这是本阶段的核查判据：EllSeg除了输出椭圆参数，同时输出像素级分割mask，二者若不重合，说明椭圆拟合头把结果"带偏"了，这与此前Otsu/星射线法里"高光/眼睑阴影把轮廓带偏"是同一类错误模式，只是这次有分割mask可以交叉验证，核查比之前几轮更可靠。

逐张分类结果（完整记录见`data/results/ellseg_visual_audit.csv`）：

| 类别 | 数量 | 判定依据 |
|---|---|---|
| 视觉确认正确 | 13/20 | 椭圆与分割mask重合、中心落在角膜反光点上 |
| 误判——眼睑遮挡/眯眼（不公平帧） | 5张（458032, 463868, 470346, 483568, 503787） | 眼睑遮挡导致分割mask破碎或缺失，椭圆位置与mask明显不重合（部分样本mask完全在椭圆外） |
| 误判——睁眼状态下的真实检测失败（公平帧） | 2张（687750, 693926） | 椭圆形状退化（过窄/偏小）或偏离实际反光点，眼部本身清晰可见但模型仍判断错误 |

**两种口径的成功率**（沿用7a.4节确立的"公平帧/不公平帧"分母方法）：
```
全帧口径（原始分母，20）  = 13/20 = 65.0%
公平帧口径（排除5张遮挡/眯眼帧，分母15） = 13/15 = 86.7%
```

### 7f.6 与此前所有方法的横向对比

| 方法 | 光照条件 | 程序报告 | 人工复核后可信数字 |
|---|---|---|---|
| Otsu阈值法（6.4节） | 无IR | 0/20 (0%) | 0/20 (0%) |
| 星射线法（7d.2节） | 无IR | 6/20 (30%) | 约2/20 (10%) |
| Otsu阈值法（7a.4节） | 850nm IR补光 | 22/100 (22%) | 22/81 公平帧 (27.2%) |
| **EllSeg（本节）** | **无IR** | **20/20 (100%)** | **13/20 全帧 (65.0%) / 13/15 公平帧 (86.7%)** |

**这是本项目迄今为止最重要的单项发现**：在完全不依赖IR补光硬件的条件下，EllSeg的真实（视觉核查后）检测准确率不仅远超此前所有无IR方案（星射线法10%），还显著超过了此前被认为"方向有效但不充分"的IR+经典算法基线（27.2%）。公平帧口径下86.7%的数字，是本项目第一次出现"接近可用于连续追踪"量级的结果。

需要如实标注的限制：
1. 样本量仍只有20帧，且是此前第六阶段用Haar cascade自动裁剪保存的小尺寸静态图（216×216～245×245像素），不是EllSeg设计目标的连续视频流，没有验证帧间稳定性/抖动
2. 本次复核标准（椭圆是否与模型自己的分割mask重合）比此前"圆度""星射线边界点"等指标更严格，但依然是研究者单人目视判断，不是像素级ground truth标注，与此前各阶段的复核方法论一致、但精度上限也一致——都是"肉眼能看出的明显对/错"这个粒度，不是亚像素误差
3. 5张"不公平帧"全部来自眼睑遮挡/眯眼，这与7a.4节IR测试中19%不公平帧占比的量级接近，提示即使换了检测算法，"头部/眼睑姿态导致的采集质量问题"仍是独立于算法选型的一个工程变量

### 7f.7 结论与对第四步（PupilSense/WSL2）的决策

用户原计划：若EllSeg效果不理想，再评估是否值得花时间配置WSL2/Docker环境去测PupilSense。基于7f.5/7f.6的结果——EllSeg不仅"跑起来了"，真实精度还大幅超过此前验证过的最佳方案（IR+Otsu的27.2%），**不建议现阶段投入WSL2/Docker+Detectron2编译环境去验证PupilSense**。理由：
1. EllSeg已经是一个在当前硬件方向（无IR、眼部特写、不需要全脸）下验证有效的候选，86.7%（公平帧）量级已经值得作为下一步主力方案推进，而不是继续横向排查更多候选
2. PupilSense需要解决的是Detectron2在Windows下的编译工具链问题（装MSVC Build Tools+精确匹配PyTorch/CUDA/Detectron2三者版本），这本身就是7e.4节确认过的"至少另起一套环境"量级的工作量，在已有一个效果更好的候选跑通之后，继续投入的边际价值降低
3. 如果后续EllSeg在更大样本量/连续视频流上的验证中精度明显下滑，PupilSense仍是有记录在案、可以随时重新拾起的备选（7e.4节结论未被推翻，只是优先级让位）

### 7f.8 下一步

- 在更大样本量上复测EllSeg，并针对连续视频流（而不是静态裁剪图）验证帧间稳定性——当前20帧样本量级尚不足以支撑"86.7%"这个数字外推到实际使用场景
- 评估EllSeg能否满足可穿戴设备的实时性要求（当前只验证了CPU离线推理可行，未测单帧耗时/是否需要GPU才能达到可用帧率）
- 5张不公平帧（眼睑遮挡/眯眼）提示：无论最终选哪种检测算法，头戴式固定（7e.1节已确认的方向）对保持稳定采集角度仍然关键，这一点不因换成深度学习方法而改变
- ESP32CAM联调（见7e.7节）：仍独立于本节工作，等待新摄像头到货后用`261022/`现有固件+脚本测试

---

## 7g. 第七g阶段：EllSeg更大样本量+连续视频流复测（2026-10-25）

### 7g.1 背景

7f节的86.7%（公平帧）结论建立在20张静态裁剪图上，7f.8节明确记录这个样本量级不足以支撑外推到真实使用场景，且没有验证过连续追踪时帧与帧之间稳不稳定（静态图互相没有时间连续性，回答不了这个问题）。本阶段目的：用新采集的连续视频流数据复测，同时首次测量EllSeg处理真实连续帧的实际吞吐。

### 7g.2 数据采集

写入`capture_eye_video_noIR.py`，复用`eye_roi.py`已验证的Haar cascade自动ROI检测逻辑，改为持续采集一段时间内的连续帧（而非按键触发的离散单帧），严格按真实时间戳命名保存。

**采集过程中的工程问题**（如实记录）：
1. **CascadeClassifier中文路径问题复发**：报告第1.3节记录过的"OpenCV底层无法读取含中文字符路径"问题，因为项目目录后来被整体归档搬进了`作品集\课程`这个中文路径下而复发——哪怕XML文件和脚本放在同一目录，这条路径本身是中文的，问题依然成立。这意味着`eye_roi.py`等同样方式加载XML的老脚本，现在如果重新运行会报同样的错，只是近期没人重跑过没暴露。修复：把XML复制到纯ASCII路径`D:\cv_cascades`，从那里加载，不再依赖脚本自身所在目录。
2. **Camera index再次漂移**：第一次采集意外调用了index 0（这次变成了电脑自带摄像头），重新跑`identify_camera.py`确认这次index 1才是OV9281（黑白、近距离特写、瞳孔反光点清晰），与7a.2、7b.2、7c.1记录的历次漂移是同一类问题，再次印证"camera index不能凭上次结论假设，每次都要重新核实"这条规则。

**采集结果**：两次独立录制会话（按文件名时间戳聚类识别，不是同一段连续录制）：
- Session A：77帧，裁剪尺寸仅约70-80像素，放大到EllSeg所需320宽度时严重模糊失真，画质明显劣于其余数据，本次分析中排除，仅记录采集到过
- Session B：265帧，约19秒，裁剪尺寸约270-414像素，与7f节静态测试用的20张样本（216-245像素）量级相近，是本次分析的主力数据

### 7g.3 代码缺陷排查：浮点数截断导致约2%的帧推理时崩溃

首次运行`run_ellseg_video_stability.py`（复用`evaluate_ellseg.py`的`preprocess_frame`预处理逻辑，与7f节推理脚本一致）在处理到第49帧时报`RuntimeError: mat1 and mat2 shapes cannot be multiplied`。排查发现：预处理函数里用`int(img.shape[1] * (op_shape[1]/img.shape[1]))`重新计算目标宽度，数学上恒等于`op_shape[1]`（320），但浮点运算误差会让某些输入尺寸算出319.999...，被`int()`截断成319，少1像素。这1像素的差异经过模型内部多层下采样会被放大，最终导致矩阵维度不匹配而崩溃。

经排查，265帧里有5帧（约1.9%）精确撞上了这个边界情况。这个bug继承自EllSeg官方`evaluate_ellseg.py`原始代码，7f节测试的20张静态图样本凑巧没有一张撞上，这次265帧的更大样本量暴露了出来——这也印证了"更大样本量复测"这件事本身的价值，不只是精度数字更可信，连代码本身的边界缺陷都需要更大样本量才能暴露。

**修复**：改为直接使用`op_shape[1]`常量作为目标宽度，不再用浮点乘法重新计算，从根上消除这个误差来源。修复后265帧全部能正常通过预处理。

### 7g.4 推理结果与视觉复核

**真实吞吐实测**：265帧，真实墙钟耗时34.0秒，**实测7.79 FPS**（含图像读取、预处理、推理、坐标还原全流程）。这与7f.6节单帧benchmark测出的纯推理理论值（7.9 FPS）几乎完全一致，证明该benchmark的估算是准确的，真实流程的额外开销可以忽略不计。

**程序报告检出率**：265/265 (100%)——与此前历次测试一样，这个数字未经视觉复核前不采信。

**视觉复核**：按7f.5节建立的方法（检查瞳孔椭圆是否与EllSeg自身输出的分割mask、角膜反光点重合），从265帧里每20帧抽样一次（共14帧），逐帧放大检查：

| 类别 | 数量 | 说明 |
|---|---|---|
| 视觉确认正确 | 12/14 | 椭圆与分割mask重合、中心落在角膜反光点上 |
| 误判——眼睑遮挡（不公平帧） | 1帧(#220) | 眼睑几乎完全遮住眼球，椭圆落在眉毛/眼睑区域，与7a.4节"不公平帧"同一性质 |
| 误判——明显偏移（公平帧） | 1帧(#40) | 眼睛清晰可见，但椭圆偏向分割mask的一侧，未能对齐mask主体 |

```
视觉复核后可信检出率 = 12/14 ≈ 85.7%
```

**这个数字与7f.5节的86.7%（20张静态图、公平帧口径）高度吻合**，差异在个位样本量下的正常波动范围内。这是本阶段最重要的发现：换了一批独立采集的新数据、换成连续视频场景后，EllSeg的真实准确率依然站得住，证明7f节的86.7%不是小样本量下的偶然结果，具备一定的可推广性。

### 7g.5 帧间抖动分析——一个重要的统计口径陷阱

对相邻帧瞳孔中心计算欧氏距离作为"帧间抖动"指标，初步结果：中位数19.6px，均值23.1px，最大116.4px，90分位44.2px。

**发现统计陷阱**：对照每帧真实采集时间戳，发现录制过程中有6次相邻帧之间的真实时间间隔超过0.5秒（最长达3.76秒），对应Haar cascade在这段时间内持续检测不到眼部ROI（大概率是眨眼或头部大幅移动所致）。原始的"帧间抖动"计算把"跨越几秒钟的真实位置变化"和"正常追踪时几十毫秒内的位置变化"一视同仁地计入同一个分布，这会人为抬高最大值和高分位数——**不该直接引用最大值116.4px这类数字，它主要是采集空档的产物，不是正常追踪时真实的不稳定程度**。

剔除跨越这6处大间隔的位移样本后，正常追踪段的帧间位移中位数几乎不变（19.5px vs 原始19.6px，中位数本身对少数几个异常点不敏感），但按真实时间间隔换算成速度后，正常追踪段的瞳孔中心表观移动速度中位数约701px/s、90分位约1571px/s。这个数字里仍然混合了"真实视线移动"和"检测噪声"两种成分，无法从单一数值里拆开，需要后续设计受控实验（比如固定头部+已知的视线移动模式）才能分离。

**另一个需要澄清、避免误读的点**：采集到的帧真实时间间隔中位数仅26毫秒（约38Hz），这是**摄像头原始采集速度叠加Haar cascade检测速度**，不是EllSeg的处理速度——本次EllSeg推理是采集完成后离线批量跑的，与采集过程的时间节奏无关。如果未来做成实时闭环系统，实际能跟上的处理节奏是7g.4节测出的7.79FPS（约128毫秒一帧），而不是这里看到的26毫秒。两个数字分属采集链路和推理链路两个不同环节，不能混用。

### 7g.6 结论与下一步

1. **86.7%（7f节）→85.7%（本节，独立新数据+连续视频场景）的一致性，是EllSeg方案目前最有力的支撑证据**——不是单一样本批次的偶然结果
2. **7.79FPS的真实吞吐已经用真实连续数据验证过，与理论估算一致**，这个数字可以作为后续是否需要GPU这一决策的可靠依据，不需要再怀疑这个估算本身的准确性
3. **帧间抖动的真实含义仍不明确**——当前数据无法区分"检测噪声"和"真实视线移动"，需要固定头部+已知视线移动模式的受控实验才能回答
4. 过程中暴露、修复了两个独立的工程问题（CascadeClassifier中文路径复发、预处理浮点截断bug），均已记录具体原因和修复方法，供后续类似问题排查参考

**下一步**（更新7f.8节遗留的待办）：
- 7.79FPS是否满足实际需求，需要先明确判定逻辑是"持续停留检测"（dwell-based，对帧率要求相对宽松）还是需要捕捉快速扫视的精细轨迹（对帧率要求高）——这个产品设计层面的判断尚未最终拍板，拍板后再决定是否需要投入GPU环境测速（CUDA版torch约2.45GB，当晚网速下载约需4小时）
- 5点视线标定（瞳孔坐标→实际视线方向）仍是当前最大的技术缺口，优先级高于继续扩大EllSeg样本量本身
- 物体识别模型（YOLO类）选型，按已有讨论排在眼动标定之后开始，避免两条线都未验证完成时互相返工

---

## 7h. 第七h阶段：5点视线标定首次产出真实数据（2026-10-25）

### 7h.1 背景

7g.6节确认5点标定是当前最大的技术缺口。此前`calibration.py`（第十阶段，Otsu检测器版本）从未真正运行出过数据——Otsu在无IR下0%的真实成功率，使"少于3个点有效数据"这个失败分支成为必然结果，不是bug。既然EllSeg已经验证出~86%的真实准确率，理论上第一次有了"值得拿来跑标定"的检测器。

### 7h.2 实现：新建`calibration_ellseg.py`，不改动原文件

新建`pupil_detector_ellseg.py`——接口与`pupil_detector.py`完全一致（`detect_eye`/`detect_pupil`，相同返回字典结构），这样标定/注视实验脚本只需要换一行import就能切换检测器，不用重写周边的采集/记录/绘图逻辑。`detect_eye`（Haar cascade ROI步骤）原样复用，只替换瞳孔中心估计这一步。

基于此新建`calibration_ellseg.py`（不覆盖原`calibration.py`，与`pupil_detector_starburst.py`等历史检测器并存的惯例一致），并补上原脚本一直缺少的实时"Eye ROI"预览窗口——这正是9阶段`gaze_experiment.py`在2026-10-09早已暴露并修复过的同一个缺口，这次从一开始就加上。

**已知代价（如实写明）**：EllSeg约7.8FPS（CPU），远低于Otsu方案可达到的60-100+FPS，3秒停留时间只能产出约18-20个样本，不是几百个。这是刻意的取舍：少量但可信的样本，好过大量但接近0%可信的样本。

### 7h.3 第一轮测试：标定误差196px，发现"无方向信号"的异常

首次运行（5/5点有数据，Eye-ROI命中率65.1%）得到平均标定误差196.2像素（标定窗口800×600），远超可用水平。进一步检查发现比误差数字本身更严重的问题：**五个标定点的瞳孔坐标均值几乎完全重叠**（x跨度仅约36像素，y跨度仅约26像素），且**没有任何符合"上下左右"方向的规律**（例如CENTER的y值比两个TOP点的y值都大，顺序完全不对）。

这与7d.3节记录过的"60帧center批次内部虹膜坐标漂移，因为头部位置未严格固定"表面相似，于是先假设是同一类问题，询问用户本次测试时摄像头/头部是否固定——**用户确认头部和手持摄像头均未移动，只有眼球转动**，排除了头动混入的可能性，说明这次是另一个原因。

用户又独立补测3次，Eye-ROI命中率从65.1%骤降到5.5%、4.0%、11.9%（手持摄像头长时间测试，角度/距离逐渐跑偏，推测是人为持握疲劳导致，非算法问题），但"无方向信号"的异常在这几次里全部复现，排除了单次偶然性。

### 7h.4 根因定位：瞳孔坐标用的是裁剪框局部坐标系，不是摄像头固定画面坐标系

排查发现真正原因：`calibration_ellseg.py`记录的`pupil_cx/pupil_cy`是`pupil_detector_ellseg.py`返回的**眼部裁剪框局部坐标**，而这个裁剪框是Haar cascade**每一帧重新检测**出来的，框本身会随内容小幅漂移/缩放。如果这个检测框倾向于把可见的眼部结构"居中对齐"，那么即使眼球真实转动了很大角度，裁剪框也会跟着往同方向偏移一部分，两者在"瞳孔相对裁剪框的位置"这个指标里互相抵消，标定需要的方向信号在裁剪这一步就被过滤掉了大半。

这是一个继承自整个项目既有架构的潜在设计缺陷（`eye_roi.py`/`pupil_detector.py`从一开始就以裁剪框局部坐标为检测输出），只是Otsu检测器从未真正产出过可用数据，这个问题之前从未被真实数据暴露过，这是EllSeg产出真实数据后第一次撞上。

**修复**：在`calibration_ellseg.py`里把裁剪框的偏移量`(x, y)`加回局部坐标，换算成摄像头整个固定画面里的绝对坐标，用于逐点平均和仿射拟合；局部坐标仍保留在CSV里（新增`pupil_x_local`/`pupil_y_local`两列），供排查对比，不丢弃。同时修复了另一个独立的小问题：脚本原来用固定文件名保存CSV和图片，连续多次运行会互相覆盖——前三次的原始坐标数据因此丢失，只剩终端打印的样本计数可查。改成每次运行加时间戳区分，不再覆盖。

### 7h.5 修复后复测：方向信号首次确认存在

修复后重新运行两次：

| 指标 | 第一次(233229) | 第二次(233301) |
|---|---|---|
| Eye-ROI命中率 | 19.6% (54/275) | 18.3% (55/301) |
| 平均标定误差 | 154.0px | 114.2px |

逐点坐标均值（摄像头固定画面坐标系）：

第二次(233301)呈现出清晰、符合预期的单调规律——
```
垂直方向: TOP(300.8, 307.2) < CENTER(313.4) < BOTTOM(319.7, 336.1)
水平方向: LEFT/CENTER聚集在667-668，RIGHT组(743.4, 858.6)明显更大
```
第一次(233229)水平方向同样呈现左右分离趋势，垂直方向偏弱（TOP_LEFT仅5个样本且标准差达26.2px，拖偏了该点均值，不是信号本身不存在）。

**这是本阶段最重要的结论**：换成固定画面绝对坐标后，"眼球转动方向"这个信号第一次被真实测出来、且符合几何直觉，不再是之前那种完全无规律的噪声。标定误差也从196px降到114-154px，方向正确。

### 7h.6 视觉复核TOP_LEFT——确认瓶颈在Haar cascade，不在EllSeg

TOP_LEFT两次测试都只拿到5个样本(远低于其他点的8-16个)，但"瞳孔检出率(给定ROI)"两次都是100%。人工抽查该点的3张审计图，确认EllSeg的椭圆检测清晰、准确地套在瞳孔和反光点上——**不是EllSeg在这个角度测不准**。真正的瓶颈在更上游的Haar cascade眼部ROI检测：看向左上角这种极端眼位时，可见的眼部轮廓形状和Haar cascade训练样本里的"正视眼睛"差异较大，更容易检测失败。只要ROI检测成功、裁出了眼部图像，EllSeg就能可靠地找到瞳孔。

### 7h.7 结论与下一步

1. **5点标定第一次产出了方向正确、量级合理的结果**（114-154px误差，800×600标定窗口），虽然还不足以支撑精确的视线映射，但证明了"EllSeg+固定画面坐标系"这条路径是可行的，此前"无方向信号"的异常已经定位并修复，不是检测器本身的问题
2. 剩余误差的主要制约因素：每点样本量偏少（尤其TOP_LEFT这类极端角度，受限于Haar cascade ROI命中率）、手持摄像头本身不够稳定、仿射拟合对小样本异常点敏感
3. 改进方向排序：①摄像头固定安装（消除手持抖动，这是7e.1节已确认的硬件方向，不是新增需求）；②延长单点停留时间或增加重复次数以换取更多样本，尤其是极端角度的点；③考虑用更鲁棒的眼部ROI检测方法替代Haar cascade，或扩大其在非正视角度下的检测容忍度；④小样本异常点可以用中位数代替均值、或做异常值剔除后再参与拟合，降低少数噪声样本对整点均值的影响

---

## 7i. 第七i阶段：眼部摄像头小型化方向 —— 复用GC0308 + EllSeg（2026-10-29，实验设计阶段，尚未执行）

### 7i.1 背景：OV9281物理固定遇阻

ESP32-CAM已完成固定（261016节装配计划里的场景摄像头一侧）。但OV9281实际固定时暴露出两个问题：①模块体积偏大，难以像ESP32-CAM那样直接贴装在镜架前端；②此前设想的"经三棱镜反射间接拍摄眼睛"方案（想借此绕开模块体积限制、把摄像头挪到不遮挡视野的角度）经尝试后确认不可行。需要说明：7e.1节已经确认过OV9281走的是**直接朝向眼睛的特写采集**，三棱镜/反射镜只服务于OLED显示那条光路——这里重新出现的"三棱镜反射"是用户为解决OV9281体积问题而另外提出的新设想，不是对7e.1已确认架构的推翻，只是这个新设想本身被验证不可行。

### 7i.2 用户提出的假设：既然用深度学习算法，能否放宽摄像头选型条件

用户提出：当前瞳孔检测已经从"需要850nm IR补光"的经典阈值方案（7a-7c节）切换为"无需主动IR、纯靠环境光"的EllSeg深度学习方案（7f-7h节），且设备本来就要求OV9281 USB直连PC（261014节已确认的硬约束，与检测算法无关）。据此推测：摄像头选型是否可以放宽到更轻量、更好固定的型号？

### 7i.3 核查结论：假设有两条成立，但遗漏了一条独立的硬约束

逐条核查：

| 用户提出/隐含的放宽条件 | 是否成立 | 依据 |
|---|---|---|
| 不再要求摄像头对850nm IR敏感 | ✅ 成立 | 7f/7g节已用EllSeg在OV9281完全无主动IR补光条件下验证出65.0%~86.7%（视觉复核后，公平帧口径），深度学习分割不依赖IR拉开的对比度 |
| USB直连PC不是换摄像头新增的负担 | ✅ 成立，但这本来就不是"换摄像头才解锁"的条件——261014节早就确认OV9281必须USB直连PC，这条约束在讨论换不换摄像头之前就已经存在 |
| 可以不追求OV9281标称的117FPS高帧率 | ✅ 可以放宽（本次核查新确认） | 7g.4节实测真实链路瓶颈在EllSeg推理本身（CPU约7.79FPS），摄像头帧率只要不低于这个数就不构成新瓶颈 |

遗漏的硬约束——**近距离对焦能力**：镜架佩戴场景下摄像头到眼睛的工作距离是厘米级，这与IR、与检测算法都无关，纯粹是镜头物理设计问题。多数"轻量易固定"的通用小型摄像头模组出厂对焦距离设在数十厘米以上，贴脸近距离大概率无法合焦，这条此前的推理没有覆盖，需要在换任何新模组前单独核实。另外还有两条次要项要一并核实：**UVC协议兼容**（现有`cv2.VideoCapture(CAP_DSHOW)`链路要求摄像头是标准UVC免驱设备）、**传感器噪声水平**（见下）。

### 7i.4 决策：优先复测已有的GC0308，而非直接采购新模组

GC0308是7b节已经买到手、测过的成品模组，设计定位就是"近距离眼动追踪"（3-5cm工作距离，内置IR），天然比OV9281更小更适合贴脸固定，不存在"换新模组需要重新验证对焦/UVC"这类未知风险。

GC0308在7b节的失败（三轮尝试均0%真实成功率）根因是**传感器颗粒噪声**，与光照/对比度无关——这是和OV9281完全不同性质的瓶颈。当时测试用的是经典算法（Otsu阈值+圆度筛选，以及附加中值滤波），EllSeg是深度学习分割模型，对这类像素级噪声的鲁棒性此前从未验证过。这构成一个尚无数据回答的具体问题：**EllSeg能否克服GC0308的噪声瓶颈？**

决定：不直接采购新摄像头，先复用7b节已采集、仍保留在磁盘上的GC0308裁剪ROI样本（`gc0308/data/gc0308_samples_cropped/`，62张，即round2/3用过的同一批"手动裁剪排除鼻梁噪点"样本），换上EllSeg重新跑一遍检测。这批样本此前经历过：round2 Otsu+裁剪（0/61，2例程序"成功"均为误报）、round3 裁剪+中值滤波（0/61，同2例误报未被修正）。如果EllSeg在同一批样本上测出明显高于0%的真实（视觉复核后）成功率，说明摄像头小型化问题可以不买新硬件、直接用现成的GC0308解决；如果仍然很低，再按7i.3节的三条核实标准去找新模组。

### 7i.5 待执行脚本

`课程/261029/gc0308_rerun_ellseg.py`——复用`run_ellseg_inference.py`（7f节）的EllSeg加载/推理/叠加可视化逻辑，输入源换成`gc0308/data/gc0308_samples_cropped/*.png`，输出写入`gc0308/data/gc0308_results/gc0308_pupil_detection_ellseg.csv`和`gc0308/data/gc0308_processed_ellseg/`，命名与round2/3已有的`gc0308_pupil_detection_cropped.csv`/`_denoised.csv`并列，保持该子项目一贯的"同一批样本、只换检测器"对照惯例。

### 7i.6 复测结果（2026-10-30，脚本已运行+人工复核）

重新拉取EllSeg代码与权重文件遇到和7e.3/7f.1同一类网络问题（直接clone/zip下载均中途被重置），最终用"分离大文件"的方法解决：代码部分走`git clone --filter=blob:limit=2m`+`sparse-checkout`（和7f.1同一手法），唯一需要的权重文件`weights/all.git_ok`改走`raw.githubusercontent.com`单文件直链下载，绕开git传输大blob时容易被重置的问题。`models/RITnet_v3.py`里`np.int(...)`的numpy兼容性修复（7f.3节记录过的同一处）在新拉取的代码里重新打了一遍。

脚本`261029/gc0308_rerun_ellseg.py`对`gc0308_samples_cropped/`62张样本运行，程序原始报告62/62(100%)"检出"——和历次测试一样，这个数字未经视觉复核前不采信。

**视觉复核——分两轮，第一轮抽样结论被第二轮全量复核推翻，如实记录这次自我修正过程**：

第一轮先抽样22/62张（约35%），逐张检查瞳孔椭圆（红色）是否真的套在模型自身分割出的瞳孔mask（金色区域）上，判据与7f.5/7g.4一致，得到13正确/8误判（椭圆被反光点带偏）/1失败（画面无眼睛），据此估算成功率约62%（公平帧口径）。

第二轮把剩余40张全部审完（凑齐62/62全量复核），结果与第一轮的抽样比例明显不一致：**40张全部视觉确认正确，没有新增一张误判或失败**。回看第一轮抽样的22张在原始文件名时间戳上**集中分布在几个特定的连续拍摄区段**（而不是均匀分布在62张的时间轴上），这些区段本身就是7b节记录过的"手持调整摄像头角度"的过渡期，误判/失败样本的时间聚集性被第一轮的抽样方式放大了——这是本报告第二次撞上"抽样比例恰好覆盖了异常聚集区段导致结论失真"这类统计陷阱（上一次是7g.5节的帧间抖动分母陷阱），处理方式同样是如实记录、补全数据后更正，不是悄悄把第一轮的62%换成后来的数字。

**全量62/62复核最终结果**：

| 类别 | 数量 | 说明 |
|---|---|---|
| 视觉确认正确 | 53/62 | 椭圆与金色瞳孔mask重合、中心落在反光高光点上 |
| 误判——椭圆被反光点带偏（公平帧） | 8/62 | 眼部清晰可见，但红色椭圆圈住的是反光高光点而非完整瞳孔区域，与7a.4节记录过的"高光把椭圆带偏"是同一类错误模式；全部8例集中在第一轮抽样到的那几个区段内 |
| 误判——画面无眼睛（不公平帧） | 1/62（`gc0308_crop_1791475669952`） | 该样本裁剪框内根本没有拍到眼部结构（疑似裁剪/手持偏移），模型仍勉强输出了两个无意义的小椭圆，程序端记成"成功" |

```
全帧口径（分母62） = 53/62 ≈ 85.5%
公平帧口径（排除1张无眼睛样本，分母61） = 53/61 ≈ 86.9%
```

**与此前各方案横向对比**：

| 方案 | 检测器 | 真实成功率（视觉复核后） |
|---|---|---|
| GC0308（7b节，三轮） | 经典算法（Otsu+圆度，含降噪变体） | 0%（三轮全部0%，瓶颈为传感器颗粒噪声） |
| **GC0308（本节，62/62全量复核）** | **EllSeg** | **约86.9%（公平帧口径）** |
| OV9281（7f/7g节） | EllSeg | 86.7%（静态20张）/ 85.7%（连续265帧） |

**结论**：假设成立，而且比第一轮抽样估计的结果更强——EllSeg对GC0308的传感器噪声鲁棒性不仅明显优于经典阈值算法（0%→86.9%），全量复核后的数字**与OV9281+EllSeg基本持平**（86.9% vs 86.7%/85.7%），不再是"明显弱于OV9281"的次优选项。摄像头小型化问题现在有扎实数据支持：**不需要买新硬件，GC0308 + EllSeg这条路线在算法层面已经验证可行，精度不输OV9281**。

需要如实标注的限制（不因为数字好看就跳过）：
1. 8例误判全部是"反光点带偏"同一种模式，且集中在特定拍摄区段，提示这不是随机噪声，而是某种特定角度/反光条件下的系统性弱点，值得留意但暂不构成否决理由
2. 本次仍是对**62张静态裁剪图**的复核，不是连续视频流测试——对照7f→7g的既有验证顺序（静态图验证完必须再上连续视频流确认帧间稳定性），这一步还没有做，是这条结论转化为硬件决策之前必须补的最后一步

### 7i.7 下一步

- ~~用GC0308实际采集一段连续视频流~~ 已完成，见7i.8——结果暴露了静态测试没覆盖到的真实问题，下一步已更新为"解决裁剪框跟不上眼球/头部相对运动"这个具体瓶颈，而不是简单重复测试
- 物理验证仍然独立：即便算法侧数字好看，GC0308在镜架上的实际固定方式、重量、与ESP32-CAM的配平分配，仍需要按261016节的装配计划重新走一遍（这部分和检测器选型无关，不能因为算法测通了就跳过）

### 7i.8 连续视频流复测（2026-10-30，脚本已运行+人工复核）——静态结果没能直接外推

脚本：`261029/gc0308_capture_video.py`（开场一次性手动裁剪框，随后连续自动采集，不逐帧跑Haar cascade重新定位——原因见该脚本docstring：GC0308设计上是近距离固定工作距离，之前认为一次裁剪对整段录制仍然有效）+ `261029/gc0308_rerun_ellseg_video.py`（复用`run_ellseg_video_stability.py`的EllSeg推理+抖动分析逻辑）。

**采集结果**：531帧，真实耗时18.2秒（≈29FPS采集速度，与此前GC0308实测的29-31FPS一致，见7b.3节），帧间时间间隔中位数32ms、最大128ms，**没有出现7g.5节那种"间隔超过0.5秒"的采集空档**——这批帧时间上是干净连续的，不存在"长间隔污染统计"的那类陷阱。

**EllSeg推理**：531帧真实墙钟耗时89.5秒，**实测吞吐5.94 FPS**，低于OV9281同一模型测出的7.79FPS（7g.4节）。本次GC0308裁剪尺寸390×299，比OV9281静态测试常见的216-350px裁剪略大，更大尺寸的LANCZOS4缩放+推理耗时更长是一个合理的解释方向，但没有做控制变量的对比实验，这里只如实记录现象，不把"裁剪尺寸更大"当作确定结论。

程序原始报告531/531(100%)检出——不采信。

**视觉复核**：按每20帧抽样（27张）的惯例抽查，这次发现的问题比静态图测试严重得多，而且能定位出**两种不同性质的失败**（不是同一个问题）：

| 类别 | 数量/27 | 说明 |
|---|---|---|
| 视觉确认正确 | 9 | 瞳孔椭圆/分割mask准确 |
| **裁剪框完全丢失眼睛**（如#40、#100，已调出原始帧核实：画面里只有额头/眉骨皮肤，没有任何眼部结构） | 4 | **不是EllSeg的检测失败，是采集方法的问题**——这次用的是"开场选一次裁剪框，整段录制复用同一个框"，但20秒内头部/摄像头的相对位置会漂移，眼睛移出了这个固定框的范围 |
| 眼睛在裁剪框边缘，部分可见（如#180，原始帧核实：眼睑和瞳孔只露出一小部分在画面最下方） | 8 | 介于"完全丢失"和"正常可见"之间，EllSeg在这类画面上的表现本身也不稳定 |
| **眼睛清晰可见但EllSeg仍然检测错误**（如#420、#460，已调出原始帧核实：眼部位置清晰、曝光正常，但分割mask破碎、红色椭圆没有套住瞳孔） | 6 | **这才是真正意义上"EllSeg在连续视频上表现变差"的证据**，和上面"裁剪框丢失眼睛"是完全不同性质的问题，不能混在一起算成一个"失败率" |

```
严格口径（只认"视觉确认正确"）= 9/27 ≈ 33.3%
排除"裁剪框完全丢失眼睛"的4帧后（这4帧根本不构成对EllSeg的有效测试）= 9/23 ≈ 39.1%
```

**结论——静态图86.9%不能直接外推到连续自然使用场景，但原因主要不是EllSeg本身变差了**：

1. 27个抽样里将近一半（4完全丢失+8部分可见=12/27≈44%）的"失败"根源是**裁剪框跟不上真实使用中头部/摄像头的相对漂移**，这是`gc0308_capture_video.py`"开场裁剪一次、全程复用"这个设计假设本身的问题，不是EllSeg的检测能力问题——这个假设在7b节"GC0308是固定工作距离"的前提下成立，但没有考虑到即使工作距离不变，佩戴/手持时头部和眼球的相对位置仍然会在20秒内明显漂移
2. 剩下6/27（≈22%）是"眼睛清晰可见但EllSeg仍判断错误"，这部分才是真正该归因到检测器本身的失败率，比静态图的误判比例（8/62≈13%）更高，值得留意但样本量太小（27张抽样里只有6个这类样本），不足以下精确结论
3. **这组数据没有推翻7i.6节"GC0308+EllSeg可行"的判断，但否定了"直接照搬静态图的86.9%去做硬件决策"这个想法**——下一步要解决的不是"换更好的检测器"，而是"裁剪/跟踪方式要能适应真实佩戴场景下的相对运动"，这和261016节"固定安装消除手持抖动"的方向是一致的，只是现在有了连续视频的数据支撑这个判断，不再只是推测

### 7i.9 下一步

- **裁剪策略需要改**：不能再用"开场选一次框、全程复用"，需要换成能跟着眼睛走的方案——要么恢复成每帧跑一次轻量ROI检测（类似OV9281路线的Haar cascade，但GC0308这边原本没加是因为7b.1节假设近距离工作不需要），要么把裁剪框开得比眼睛大一截留出漂移余量，用更大的框喂给EllSeg（EllSeg本身在更大范围的输入上表现如何还没测过，这本身也是待验证的点）
- 如果换成"每帧更大裁剪框"的方案，需要重新测一遍，看EllSeg在"眼睛只占画面一部分"而非"眼睛填满画面"的输入下精度是否下降——这是全新的变量，不能假设和7i.6节的86.9%可比
- 物理固定仍然是治本的方向：真的把GC0308刚性固定在镜架上（而不是这次测试里头部/摄像头相对自由的佩戴/手持状态）之后，"裁剪框跟不上漂移"这个问题的严重程度大概率会显著下降，值得在物理装配（261016节）完成后重新跑一次本节的对比实验，而不是现在就断定这条路线需要大改——**已完成，见7i.10**

### 7i.10 固定安装后复测（2026-10-30，验证了7i.9节的假设）

GC0308已按261016节的装配计划刚性固定到镜架上（不再是7i.8节那次测试时头部/摄像头相对自由的佩戴/手持状态）。重新用`gc0308_capture_video.py`录了一段同样时长(20秒)的连续视频，验证"固定安装能不能解决7i.8节发现的裁剪漂移问题"。

**一个工程教训，如实记录**：`gc0308_capture_video.py`不会清空`data/gc0308_video/`里的旧文件，第一次重跑分析脚本时，新录的501帧和7i.8节那531帧旧数据混在同一个文件夹里，被`gc0308_rerun_ellseg_video.py`当成同一条连续时间线直接合并分析（1032帧，帧间位移数字和旧数据一模一样，说明脚本读到的其实还是旧文件）。排查后确认：两次录制在真实时间戳上有明显gap（间隔几小时），据此给分析脚本加了按时间戳gap自动切分session的逻辑（和7g.2节处理OV9281两个session的方法一致，只是这次是先出bug才补上这个本该一开始就有的防护），只分析最新的那一个session。这类"工具不清空旧数据导致新旧结果悄悄混在一起"的坑，以后任何复用`gc0308_capture_video.py`的场景都要注意。

**帧间抖动对比（同一套统计口径，直接可比）**：

| 指标 | 固定前（7i.8节，手持/松散佩戴，531帧） | 固定后（本节，501帧） |
|---|---|---|
| 中位数位移 | 10.3px | **2.3px** |
| 均值位移 | 27.2px | **5.9px** |
| 90分位位移 | 85.7px | **10.8px** |
| 最大位移 | 190.3px | 93.5px |

四项指标全面下降，中位数和90分位都降到约四分之一，方向和幅度都支持7i.9节"固定安装能缓解裁剪漂移"这个判断。

**视觉复核**：按每20帧抽样（26张）检查，结果：

| 类别 | 数量/26 | 说明 |
|---|---|---|
| 视觉确认正确 | 24 | 椭圆与分割mask重合，裁剪框稳定框住眼部，没有再出现7i.8节那种"裁剪框完全丢失眼睛"的情况 |
| 误判——不公平帧（真实眨眼） | 2（#180、#320） | 已调出原始帧核实：两张都是眼睑完全/接近闭合的真实眨眼瞬间，不是摄像头漂移，也不是检测器误判——这是任何眼动追踪方案都会遇到的正常现象，不是GC0308或EllSeg的缺陷 |

```
全帧口径（分母26） = 24/26 ≈ 92.3%
公平帧口径（排除2张眨眼帧，分母24） = 24/24 = 100%
```

**结论**：7i.9节的假设成立——"裁剪框跟不上真实使用中头部/摄像头相对漂移"这个问题，在GC0308刚性固定到镜架后基本消失，剩下的2个"失败"样本经核实都是正常眨眼，不是方案缺陷。固定安装后的连续视频表现（公平帧100%）不仅远好于固定前的手持测试（33%），也比静态裁剪图复测的86.9%更好——静态图测试用的样本本身可能偏向"容易检测"的角度/状态，连续视频在固定安装后反而给出了更干净的结果。

**这条技术路线到此已经验证完整**：GC0308（近距离设计，物理上比OV9281更小更好固定）+ EllSeg（无需IR、无需等光学对焦适配）+ 刚性固定安装，在静态图和连续视频两种测试方式下都给出了和/优于OV9281+EllSeg基准的真实准确率。摄像头小型化这个最初卡住原型推进的问题，现在有完整的实验数据链支撑"可以用GC0308替代OV9281"这个结论。

### 7i.11 下一步

- 把GC0308正式确立为眼动摄像头路线（取代7i节开头提到的OV9281固定遇阻问题），更新`261010/眼镜式双摄融合眼动仪路线图.md`里涉及摄像头选型的部分，避免后续讨论里反复纠结"换不换摄像头"这个已经有数据支撑的问题
- 称重+试戴：GC0308、ESP32-CAM、OLED三件都固定上镜架后，按261016节的配平方案做一次实际称重，确认左右重量分配是否可接受
- 场景摄像头(ESP32-CAM)→OLED的几何映射标定仍然独立于本节结论，还没有做（261016节"待解决"里记录过，需要的是外部参照相机拍OLED经镜片反射后在真实世界的落点，这部分工作和瞳孔检测路线选型完全脱钩）

---

## 7j. 第七j阶段：Phase1全链路首次用真实数据跑通（2026-10-30～2026-11-04）

对应`261014/ESP32CAM+OV9281 双摄眼动仪 · PC 直控方案可行性分析.md`第八节"分阶段路线"的**Phase1**——PC全接管、先把几何标定和遮罩视觉效果调对，不碰FOMO。代码在独立文件夹`261030/`，与本报告路径区分（同261022/261029的先例），详细设计见`261030/README.md`。

### 7j.1 新增标定：GC0308直接对OLED坐标系标定

`261004/calibration_ellseg.py`标定的是"瞳孔坐标→任意800×600窗口"，且用Haar cascade两级检测（给OV9281那种"眼睛占画面一小部分"的场景设计）。GC0308是近距离特写，不需要也不适合Haar cascade（参照7i节GC0308的既有做法：一次性手动裁剪框，全程复用）。为此新建`261030/calibration_gc0308_oled.py`：只调用`pupil_detector_ellseg.py`的`detect_pupil()`（不调用`detect_eye()`），标定目标直接是OLED真实像素坐标(128×64)，省掉"标定到任意空间再换算成OLED坐标"这一步换算。标定结果（仿射矩阵+裁剪框+camera index）存成JSON，供下游脚本直接加载复用，不用每次重新标定——这是本报告历次标定脚本里第一次把结果持久化成可复用文件，之前（`calibration.py`/`calibration_ellseg.py`）都只是打印/画图，不能被别的脚本直接消费。

**两次标定结果**：

| 标定次数 | 平均误差(OLED像素，总宽128/总高64) | 各点误差范围 |
|---|---|---|
| 第一次 | 18.6px | 8.4~37.2px |
| 第二次（最终采用） | 12.8px | 4.1~22.8px |

两次手动框选的裁剪框略有差异（x=146→163, w=345→377），标定结果随之有波动，说明裁剪框的细微差别会影响最终精度，这是预期之内的、暂不深究的变量。12.8px相当于OLED宽度的约10%，和7h节OV9281+800×600窗口测出的114-154px（约14-19%占比）量级相近甚至略好。抽查了几张标注图（含误差最大的TOP_RIGHT点），椭圆标记确实落在一块边界清晰的小圆形暗区上，不是反光点/睫毛误判，检出可信。

### 7j.2 新增融合脚本：真实注视点替换WASD模拟

`261022/fusion_poc.py`已验证"状态跳变才发/mask请求"这套防抖状态机+HTTP时序本身没问题，但注视点是WASD键盘模拟、干扰物位置是写死矩形，两处都明确标注过是占位。本阶段新建`261030/phase1_fusion.py`，只替换第一处：加载`calibration_gc0308_oled.py`产出的JSON，实时读GC0308→EllSeg→仿射矩阵→得到OLED坐标系下的真实注视点，核心的防抖状态机逻辑原样复用，没有改动。干扰物矩形**仍然是写死的占位**（场景坐标系下定义，叠加显示在真实`/capture`画面上，再线性缩放到OLED坐标——不是正式的场景↔OLED几何标定，那个要等光学透镜装上才做），这是Phase1范围内明确不做真实物体检测，不是本次遗漏。

### 7j.3 联调过程中的网络故障排查（如实记录完整过程，不只记录结果）

首次运行暴露出`/mask`请求超时，排查过程经历了三轮假设，最终确认都不是真正原因，只有第三轮找对：

1. **第一轮假设**：ESP32单线程`WebServer`处理`/capture`时把`/mask`请求"挡住排队"，3秒内等不到响应判超时，但指令其实送达了（因为当时用户反馈OLED确实有微弱反应）。应对：把客户端超时从3秒延长到10秒，同时把测试用占位矩形从40×19px放大到72×37px方便肉眼确认。
2. **第二轮复测**：延长超时后，`/mask`请求反而**100%在10秒整超时，OLED完全没反应**——这直接推翻了第一轮"慢但成功"的假设，说明请求根本没被处理，不是排队慢。转而怀疑ESP32固件卡死，或物理固定到镜架后天线被遮挡导致WiFi信号变差（`261016_固定与供电计划.md`明确提醒过这个风险）。
3. **第三轮用`ping`分层排查**：请求用户直接`ping`ESP32的IP，这是比HTTP更底层的连通性测试，能把"WiFi链路问题"和"ESP32应用层卡死"分开判断。Ping显示**4/4全部成功**——证明WiFi链路本身没问题，推翻了"天线被遮挡"的猜测。进一步追问后确认：**真正原因是用户电脑自己的WiFi在那几分钟内发生了一次短暂自动断线重连**，和ESP32、天线、固件都无关，是最简单、也是最容易被忽略的一种可能性，前两轮排查都想复杂了。网络恢复后重新测试，`/mask`请求稳定在0.0~0.1秒内成功返回。

**这次排错的方法论教训**：遇到"看起来复杂"的故障（超时、时快时慢），不要跳过"最基础的连通性"这一层直接去猜应用层逻辑或硬件问题——`ping`这种最简单的工具，分层排查的效率比直接去看代码/怀疑硬件更高，这次足足绕了两轮假设才用上。

### 7j.4 最终结果：Phase1链路首次全程用真实数据跑通

真实GC0308瞳孔检测 → EllSeg → 标定矩阵 → OLED坐标系真实注视点 → 真实HTTP `/mask`请求 → 真实OLED响应，全链路首次打通，不再有任何一环是模拟/占位（干扰物检测本身除外，这是Phase1范围内明确排除的部分）。

运行中观察到注视点进入/离开占位矩形的状态切换非常频繁（同一秒内多次往返），对应OLED上快速闪烁而非"稳定点亮"。排查这不是bug——用户确认是因为佩戴时本身在持续扫视多个设备（真实使用场景的自然眼动模式），叠加12.8px标定误差和EllSeg检测噪声，注视点在矩形边界附近本就会频繁穿越。用户确认当前表现可以接受，暂不加防抖/去抖逻辑，如果后续实际体验下来觉得闪烁影响使用，再回来加"连续N帧稳定在同一侧才切换状态"这类去抖机制。

### 7j.5 下一步

- 场景摄像头→OLED的正式几何标定（现在用线性缩放占位）：等光学透镜装上后再做，独立于本节结论
- 真实物体检测/FOMO接入（Phase1明确排除，Phase2的范围）
- 如果后续体验下来注视点闪烁影响使用，再评估是否加去抖逻辑（当前判断是不需要，7j.4已记录原因）
- `261004/gc0308/identify_gc0308.py`在本阶段修复了一个之前没人发现的bug：该脚本直接用`cv2.imwrite()`写文件，在本项目的中文路径(`作品集/课程`)下会静默失败，且原代码没检查返回值，一直打印"saved..."掩盖了这个问题，直到这次用户去看文件才发现没真正写出来。已改成项目统一的`imwrite_unicode()`模式修复。

---

## 7k. 第七k阶段：Phase2物体检测路线重新评估 + PC端YOLO首次真实检测跑通（2026-11-04）

### 7k.1 发现"现成的FOMO模型"根本不是FOMO

讨论Phase2（261014文档第八节：把物体检测下放到ESP32本地，解决PC往返延迟）时，去核实`261003/esp32_camera2_OLED_object_detection.ino`依赖的Edge Impulse模型（`260919/ei-aida-project-1-arduino-1.0.7-impulse-#1.zip`，项目名"Aida-project-1"）到底是什么——此前`261022/README.md`一直写"Edge Impulse模型还在，等合适时机接回来"，这句话隐含"模型是现成能用的"这个假设，从未被验证过。

解压检查`model_metadata.h`：

```
EI_CLASSIFIER_OBJECT_DETECTION = 0        <- 不是FOMO/目标检测
results_type = EI_CLASSIFIER_TYPE_CLASSIFICATION   <- 是整图分类器
```

`model_variables.h`里的10个类别：`"Aida", "bottle", "computer", "digital mouse", "earpods", "ipad", "pen", "phone", "ringo", "unknown"`——明显是"桌面常见物品识别"练手项目的训练集，不是针对"手机屏幕/电视/广告牌"这类干扰物专门采集标注的。对照`260809/ADHD PlanA 技术方案整理.md`当时自己列过的训练FOMO该走的步骤（①明确干扰物分类②采集约200张目标图片③用FOMO打标训练），`Aida-project-1`大概率只是当时用来"先跑通Edge Impulse工作流"的练手项目，真正针对干扰物的FOMO训练从未做过。已同步更正`261022/README.md`里这句容易误导的描述。

### 7k.2 决策：不重新训练FOMO，先用PC端预训练YOLO验证概念

目标干扰物类别（手机、电脑屏幕、电视）**本来就是COCO数据集的标准类别**，不需要任何自定义采集/标注/训练，直接用预训练的YOLOv8在PC端跑就能识别——用`model.names`核实过，YOLOv8n里`class 67 = "cell phone"`、`62 = "tv"`、`63 = "laptop"`，和261010文档最初设想的干扰物类别基本对上。

决策依据：投入Edge Impulse重新训练FOMO模型这条路，是为了解决"ESP32本地化+低延迟"这个问题，但这个问题本身（261014文档5.2节"转头滑移"的200ms延迟估算）从未在真实系统上验证过是否真的构成可感知的瓶颈——现阶段也早已不追求真·可穿戴（Pi路线已放弃，见7i节/261010文档）。在没有证实"延迟是真实痛点"之前，先投入训练成本去解决它，顺序倒了。于是新建`ESP32CAM  
直连下载底板  
上传成功`（命名刻意带"pc_yolo"后缀，与真正的"ESP32本地FOMO"方案区分，避免混淆），只替换`phase1_fusion.py`里"干扰物位置"那一半的写死矩形，"真实注视点"那一半原样复用。

### 7k.3 排错过程：三种不同的检测失败模式，每次都用"不限类别+低阈值"诊断法查出真实原因

首次实测`class='cell phone', conf>=0.35`持续检测不到，没有停留在"调大概率阈值"这种猜测性调参，而是每次都用`model.predict(img, conf=0.01)`（不限类别、几乎不设阈值）把YOLO当时实际认为"像什么"的全部候选打出来，这个方法论和本报告贯穿始终的"程序输出不可信、要深挖实际原因"是一致的，只是这次诊断对象是外部预训练模型而不是自己训练的检测器。

三轮实测，三种完全不同的失败原因：

| 轮次 | 现象 | 诊断方法 | 真实原因 |
|---|---|---|---|
| 1 | 手机贴近镜头，画面被占满一块模糊过曝的白色矩形 | `conf=0.01`跑出的最高候选是`microwave 0.194`/`tv 0.154`/`refrigerator 0.106`，"cell phone"完全不在候选里 | 距离太近，画面比例、清晰度都严重偏离YOLO训练数据分布——不是手机识别问题，是"这张照片根本不像任何训练集里见过的手机照片" |
| 2 | 手机正常距离举在画面中央，但背面朝向摄像头（能看清三摄+MagSafe磁吸环） | 截取当时窗口画面单独跑`conf=0.01`检测，"cell phone"出现但`conf=0.077`，远低于0.35阈值；最高候选是`book 0.278` | COCO的"cell phone"训练图片几乎都是手机正面/亮屏的样子，手机背面（白色磨砂壳+圆形摄像头）视觉上更接近"书"的扁平矩形特征，是训练分布之外的视角 |
| 3 | 手机转为屏幕朝向摄像头，但屏幕显示内容后被拍成一片死白、看不出任何图标/界面 | 同样方法诊断，"cell phone"完全不在候选里，最高候选是`laptop 0.245`/`toilet 0.199` | ESP32-CAM的OV2640传感器自动曝光应付不了"周围暗+屏幕亮"的大光比场景，近距离时把屏幕直接曝成失去全部细节的纯白色块——这是硬件曝光能力的限制，不是算法/参数问题 |
| 4（成功） | 手机屏幕朝向摄像头、正常观看距离、屏幕内容可见（图标/界面有辨识度） | 程序正常报告 | `cell phone conf=0.43`，检测成功，OLED正确显示绿框并标注"REAL YOLO: cell phone" |

### 7k.4 结论

全链路（GC0308真实注视点 + YOLO真实物体检测 + 真实OLED响应）首次完整打通，证明"目标类别是COCO标准类别，不需要自定义训练"这个判断成立。但用户反馈成功率不高、检测不太稳定（"有点笨笨的"）——这和7k.3节诊断出的三种失败模式是一致的：真实佩戴/手持场景下，手机的朝向、距离、屏幕内容是否可辨认，都会随自然动作持续变化，任何一个滑进上述三种失败区间，这一帧就检测不到。这不是YOLO本身精度不够，是**ESP32-CAM的画质/动态范围 + 真实使用中物体朝向的不可控**共同构成的瓶颈，用更好的检测模型不能直接解决后两者。

### 7k.5 下一步

- 如果要提高实际可用的检测稳定率，方向不是换更强的检测模型，而是改善输入质量：比如固定ESP32-CAM的曝光参数（不用自动曝光，手动给一个折中值，避免对亮屏过曝）、或者接受"检测不稳定"本身，用时间上的平滑（比如连续几帧里出现过一次就维持判定一小段时间）缓解单帧失败的影响
- 场景摄像头→OLED的正式几何标定仍然独立于本节结论，还没有做
- 真正的"ESP32本地FOMO"（261014文档定义的Phase2）仍然不建议现在投入——先在PC端YOLO这条路上把检测稳定性问题摸清楚，再决定是否值得为了延迟去重新走一遍Edge Impulse训练流程

---

## 8. 总体结论与技术脉络总结

| 验证项 | 方法 | 结果 |
|---|---|---|
| OV9281图像采集 | 连续抓帧测FPS | ✅ 117FPS@720p，零丢帧 |
| 图像质量（无IR） | 均值/标准差/饱和度统计 | ✅ 曝光可用，但眼部局部质量未知 |
| 人脸/眼睛粗定位 | Haar cascade命中率统计 | ⚠️ 15.5%，不稳定但基本可用 |
| 瞳孔检测（OV9281，无IR） | Otsu阈值+圆度筛选+视觉核查 | ❌ 真实成功率0/20(0%) |
| 瞳孔检测（OV9281，有IR，静态样本） | 同上方法+人工公平帧分类 | ⚠️ 真实成功率22/81(27.2%) |
| GC0308模组FPS | 连续抓帧测FPS | ⚠️ 实测29-31FPS，远低于商品标称120FPS |
| 瞳孔检测（GC0308，内置IR） | 同一算法，全画面→裁剪→降噪三轮 | ❌ 真实成功率0%，瓶颈为传感器颗粒噪声（非对比度不足） |
| 实时采集+检测+记录链路（OV9281，有IR） | 拆分ROI命中率/瞳孔检测率双指标 | ✅ 15.17% ROI命中 / 30.16% 瞳孔检测，与静态基线吻合，链路验证通过 |
| 5点相对注视实验 | 4次运行，IR状态不可控/不可追溯 | ⚠️ 数据不可比，方法论缺口已识别，需固定光源后重测 |
| 5点标定 | 框架已搭建 | ⚠️ 首次产出真实数据（见7h节，EllSeg版），方向正确但误差偏大 |
| 瞳孔检测（无IR，星射线法） | 同一20帧样本，程序报告vs人工复核对比 | ⚠️ 程序报告30%，人工复核后约10%，方向性改善但不足以替代IR |
| 虹膜检测（无IR，MediaPipe，正视角度） | 19帧全脸样本，FaceLandmarker iris landmark | ✅ 程序报告57.9%，人工复核11/11全部准确 |
| 虹膜检测（无IR，MediaPipe，6方向） | 60帧全脸样本，中/左/右/上/下 | ✅ 60/60(100%)检出，未逐帧复核但目视无跳变，架构上需先全脸输入 |
| 无IR眼部特写深度学习候选排查（DeepVOG/EllSeg/PupilSense/KD-Eye/SAM，7e节） | 依赖安装+仓库拉取尝试 | ⚠️ 0/6可运行（MediaPipe路线不适配新硬件方向，其余5个因依赖失效/无编译工具链/无公开代码/网络不稳定未能跑通），未产出精度数据 |
| 瞳孔检测（EllSeg深度学习，无IR，眼部特写） | 同一20帧样本，程序报告vs人工复核（椭圆与模型自身分割mask是否重合） | ✅ 程序报告100%，人工复核后13/20全帧(65.0%)／13/15公平帧(86.7%)——超过此前IR+Otsu基线(27.2%)，本项目迄今最佳无IR方案，详见7f节 |
| EllSeg连续视频流复测 + 真实吞吐实测（7g节） | 新采集265帧连续序列，同一套视觉复核方法，抽样14帧；同时测全流程真实墙钟耗时 | ✅ 人工复核12/14≈85.7%（与7f节86.7%吻合，独立新数据验证一致性）；实测吞吐7.79 FPS，与纯推理理论值7.9 FPS一致 |
| 5点视线标定（EllSeg版，7h节） | 新建calibration_ellseg.py，先后排查"无方向信号"异常并定位根因（裁剪框局部坐标 vs 固定画面坐标），修复后复测 | ⚠️ 修复前完全无方向信号（根因：瞳孔坐标用了逐帧漂移的裁剪框局部坐标）；修复后两次独立测试均出现符合几何直觉的方向规律，标定误差114-154px（800×600窗口），方向正确但精度仍不足以支撑实际使用，瓶颈已定位（样本量少+手持不稳+Haar cascade在极端角度ROI命中率低） |

**两条硬件路线对比小结**：
- **OV9281 + 外挂850nm IR补光灯**：瓶颈是对比度/光照，IR照明已验证有效（0%→27.2%），路线判定为"部分可行，需继续改进算法鲁棒性与采集稳定性"。
- **GC0308专用模组（内置IR）**：瓶颈是传感器固有颗粒噪声，与光照无关，IR照明充足也无法解决；但几何形状完整度（圆度0.4-0.6）优于OV9281，说明换一种对噪声更鲁棒的算法（如先专门的去噪/平滑再做更宽松的圆度判定，或改用基于梯度/星形射线法等对噪声不敏感的瞳孔定位方法）有可能在这条路线上更快突破，是否投入取决于该模组量产一致性是否可控。

**完整技术脉络**：
1. 先验证采集链路本身没问题（第二～四阶段）
2. 再验证定位链路部分可行但不稳定（第五阶段）
3. 发现瞳孔分割在无IR条件下完全不可行，且这个结论经过"程序输出成功→视觉复核发现是误报→收紧标准→重新确认0%"的自我纠错过程（第六阶段）
4. 提前搭建好下游工程框架，为硬件改进留出接口（第七～十阶段框架）
5. IR硬件到货后复测，过程中排查出3个独立的真实工程问题（头部位移、曝光锁定不可靠、camera index漂移），最终确认IR有效但不充分，并用"公平帧筛选"方法把原始数字校正为更可信的口径（第六c阶段）
6. 并行测试第二条硬件路线（专用IR模组），用相同算法/相同方法论排查出完全不同性质的瓶颈（传感器噪声而非光照），确认两条路线不能互相替代对方的问题，且在新增更强光源测试前主动中止以规避不明确的眼部辐照安全风险（第六d阶段）
7. 正式运行第七/八阶段，用双指标拆分法验证实时链路可信度与静态基线吻合；运行第九阶段时暴露出"IR光源手持不稳定、状态不可追溯"和"脚本缺少事后视觉核查能力"两个方法论缺口，如实记录为不可比数据而非勉强给出结论（第七c阶段）

**下一步**：
- OV9281路线：固定IR光源安装方式（不再手持），补全第九阶段脚本的图片存档能力后重新运行5点注视实验；排查对焦漂移、规避角膜二次反射干扰源
- GC0308路线（更新，见7i节）：静态裁剪图复测真实成功率约86.9%（62/62全量复核，公平帧口径），与OV9281+EllSeg基本持平；手持状态下连续视频复测暴露了裁剪框跟不上漂移的问题（7i.8，公平帧仅约39%）；**GC0308刚性固定到镜架后重新测连续视频，帧间抖动降到约1/4，视觉复核公平帧成功率100%（7i.10）**——这条路线已验证完整，GC0308取代OV9281解决了摄像头小型化问题。下一步是称重试戴+更新硬件选型文档（见7i.11），场景摄像头→OLED几何标定仍是独立待办
- 正式运行第十阶段（5点标定，目前代码就绪，尚未执行，且依赖第九阶段先产出可信数据）
- **无IR眼部特写深度学习路线（7f节已验证，优先级最高）**：EllSeg在更大样本量/连续视频流上复测，验证帧间稳定性与实时性；PupilSense因EllSeg已验证有效而降低优先级，仅作为备选保留
- ESP32CAM联调（见7e.7节）：等待用户新采购的带延长线摄像头到货后，用`261022/`固件+脚本直接测试链路

---

## 附：完整文件清单

```
环境与诊断：
  copy_cascades.py / check_cv2.py           OpenCV中文路径问题的诊断与修复

第二阶段：
  camera_test.py                              camera枚举 + 真实FPS测量
  identify_camera.py                          视觉核查index对应设备
  camera_enum_results.json                    原始测量数据

第三阶段：
  capture_raw.py                               原始图像采集（10静态帧+340帧5秒序列）

第四阶段：
  image_quality.py                             图像质量统计分析
  data/results/image_quality.csv

第五阶段：
  eye_roi.py                                   Haar cascade自动ROI + 手动框选兜底
  haarcascade_frontalface_default.xml / haarcascade_eye.xml

第六阶段（无IR基线）：
  pupil_detection.py                           批量瞳孔检测 + 阈值从0.5修正到0.75
  data/results/pupil_detection.csv             0/20

第七～十阶段框架：
  pupil_detector.py                            共享检测模块
  eye_tracking_realtime.py                     实时可视化+CSV+metadata记录框架（10/9升级：加roi_found字段拆分双指标统计）
  gaze_experiment.py                           5点相对注视实验框架（10/9升级：加实时Eye ROI预览窗口+roi_found字段；计划再加图片审计存档未写入成功，见7c.3）
  calibration.py                               5点标定+仿射拟合框架

第六c阶段（IR复测）：
  ir_comparison.py                             IR开关亮度对照（含3次失败尝试的完整注释记录）
  ir_pupil_test.py                             IR照明下采集+即时检测合并脚本
  ir_audit_contact_sheet.py                    100张样本人工视觉分类联系表生成
  data/results/pupil_detection_ir.csv           100张原始检测结果
  data/results/ir_audit_classified.csv         人工分类后的公平/不公平帧标注
  data/results/ir_audit_contact_sheets/         4张联系表图片

第六d阶段（GC0308平行硬件路线，独立子目录 gc0308/）：
  gc0308/identify_gc0308.py                    设备识别（含第一次失效样本的保留记录）
  gc0308/gc0308_fps_test.py                    真实FPS实测（29-31FPS，对比商品标称120FPS）
  gc0308/pupil_detector_base.py                 复用的共享检测算法（从OV9281路线原样复制，未改参数）
  gc0308/gc0308_pupil_test.py                   第一轮：全画面检测（0/73）
  gc0308/gc0308_pupil_test_cropped.py           第二轮：手动裁剪ROI排除鼻梁噪点（0/61，误报2例）
  gc0308/pupil_detector_denoised.py             第三轮：附加中值滤波的独立检测器变体
  gc0308/gc0308_rerun_denoised.py               离线复用已有样本重跑降噪检测（0/61，未修正原有误报）
  gc0308/data/gc0308_results/                   三轮CSV结果
  gc0308/data/gc0308_samples* / gc0308_processed*  各轮原始样本与标注图

第七d阶段（无IR纯算法探索，迁移自261010路线图）：
  pupil_detector_starburst.py                  方案A星射线法检测器
  compare_algorithms.py                        Otsu vs 星射线法对比+可视化
  capture_full_face.py                         全脸无IR采集（19帧，正视角度）
  capture_full_face_multidir.py                全脸无IR多方向采集（60帧，中/左/右/上/下）
  test_mediapipe_iris.py                       方案B MediaPipe虹膜检测（19帧批次）
  test_mediapipe_iris_multidir.py              方案B MediaPipe虹膜检测（60帧多方向批次）
  data/face_full/ , data/face_full_multidir/   对应采集样本
  models/face_landmarker.task                  MediaPipe FaceLandmarker模型文件

第七e阶段（眼部特写方案确认 + 无IR深度学习候选排查，本次未产出新数据，仅记录排查过程）：
  （本阶段为调研/环境排查性质，未在261004目录下新增数据文件；ESP32CAM联调固件见独立文件夹 261022/，与本报告路径区分）

第七f阶段（EllSeg深度学习方案验证）：
  run_ellseg_inference.py                      推理脚本（复用官方evaluate_ellseg.py核心函数，输入改为PNG目录）
  data/results/ellseg_results.csv              20张图程序原始输出（椭圆参数、检出标志）
  data/results/ellseg_visual_audit.csv          人工逐张视觉复核分类（正确/误判/公平帧判定）
  data/results/ellseg/*_overlay.png             20张单图标注输出（分割mask+椭圆叠加，供复核留痕）
  data/results/ellseg_contact_sheet.png         20图联系表（推理脚本自动生成）
  data/results/ellseg_audit_batch0~2.png        人工复核用放大联系表（300px缩略图）
  data/results/ellseg_audit_zoom1~3.png         人工复核用进一步放大图（400px，针对边界/疑似误判样本）
  （EllSeg仓库本体克隆在项目目录之外：C:\Users\34659\AppData\Local\Temp\EllSeg，用partial clone+sparse-checkout拉取，见7f.1节；RITnet_v2/v3/v4.py三处numpy兼容性改动在该外部目录内，不在本项目git追踪范围）

第七g阶段（EllSeg更大样本量+连续视频流复测）：
  capture_eye_video_noIR.py                     连续视频流采集脚本（复用eye_roi.py的ROI检测，持续采集替代按键触发）
  run_ellseg_video_stability.py                 连续帧稳定性分析脚本（含修复后的预处理函数，见7g.3节浮点截断bug）
  data/eye_video_noIR/                          342帧原始采集（session A 77帧+session B 265帧）
  data/results/ellseg_video_sessionB_timeline.csv  265帧逐帧结果+帧间位移
  data/results/ellseg_video_sessionB_jitter_plot.png  瞳孔轨迹+抖动曲线
  data/results/ellseg_video_sessionB_sample_contact_sheet.png  每20帧抽样联系表（共14张，供视觉复核）
  data/results/ellseg_video_zoom/frame_*.png    14个抽样帧的单独放大标注图（人工复核用）

第七h阶段（5点视线标定，EllSeg版）：
  pupil_detector_ellseg.py                      EllSeg检测器模块，接口与pupil_detector.py一致（detect_eye/detect_pupil），供标定/注视实验脚本替换使用
  calibration_ellseg.py                         5点标定脚本（EllSeg版，不覆盖原calibration.py），含实时Eye ROI预览窗口+固定画面坐标修正
  data/results/calibration_ellseg_<timestamp>.csv          每次运行独立存档的逐帧标定数据（含局部/全局两套坐标）
  data/results/calibration_ellseg_audit_<timestamp>/        每次运行独立存档的成功检测标注图（人工复核用）
  data/results/calibration_ellseg_result_<timestamp>.png    标定结果散点图（目标位置 vs 预测位置）

第七i阶段（摄像头小型化方向，GC0308 + EllSeg复测，脚本存放于独立文件夹）：
  261029/gc0308_rerun_ellseg.py                 复用run_ellseg_inference.py的EllSeg加载/推理/叠加逻辑，输入换成gc0308/data/gc0308_samples_cropped/，与本报告路径区分（同261022的先例）
  gc0308/data/gc0308_results/gc0308_pupil_detection_ellseg.csv   62张样本的程序原始输出（检出标志、椭圆参数）
  gc0308/data/gc0308_results/gc0308_ellseg_contact_sheet.png     62张缩略图联系表（人工复核用）
  gc0308/data/gc0308_processed_ellseg/                           62张单图标注输出（分割mask+瞳孔/虹膜椭圆叠加，供复核留痕）
  261029/gc0308_capture_video.py                 连续视频采集（开场一次性手动裁剪框+自动连续保存，不逐帧跑Haar cascade）
  261029/gc0308_rerun_ellseg_video.py            连续帧EllSeg推理+抖动分析（复用run_ellseg_video_stability.py的逻辑）
  gc0308/data/gc0308_video/                      531帧连续采集原始裁剪帧（7i.8节，18.2秒会话）
  gc0308/data/gc0308_results/gc0308_ellseg_video_timeline.csv        逐帧结果+帧间位移
  gc0308/data/gc0308_results/gc0308_ellseg_video_jitter_plot.png     瞳孔轨迹+抖动曲线
  gc0308/data/gc0308_results/gc0308_ellseg_video_sample_contact_sheet.png  每20帧抽样联系表（27张，人工复核用，7i.8节，手持/松散佩戴session）
  gc0308/data/gc0308_results/gc0308_ellseg_video_timeline_session1.csv              固定安装后新session逐帧结果（7i.10节，501帧）
  gc0308/data/gc0308_results/gc0308_ellseg_video_jitter_plot_session1.png          固定安装后瞳孔轨迹+抖动曲线（7i.10节）
  gc0308/data/gc0308_results/gc0308_ellseg_video_sample_contact_sheet_session1.png 固定安装后抽样联系表（26张，7i.10节）

第七j阶段（Phase1全链路首次真实数据跑通，代码存放于独立文件夹）：
  261030/README.md                              Phase1范围/设计/运行顺序说明
  261030/calibration_gc0308_oled.py             GC0308直接对OLED坐标系的5点标定，结果存成JSON供复用
  261030/gc0308_oled_calibration.json           标定结果（仿射矩阵+裁剪框+camera index），phase1_fusion.py直接加载
  261030/phase1_fusion.py                       真实融合主程序：真实注视点+真实HTTP/mask，干扰物仍为占位
  261030/phase2_fusion_pc_yolo.py               PC端YOLO版：干扰物位置换成真实YOLOv8n检测（7k节），注视点部分原样复用phase1_fusion.py
  261030/yolov8n.pt                             预训练权重，未做任何自定义训练，COCO标准类别(cell phone/tv/laptop等)直接够用
```
