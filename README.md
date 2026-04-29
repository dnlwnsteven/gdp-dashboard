# 转载数据图片比对助手

基于【转载】数据标注标准（2026.3）实现的自动化图片比对工具，用于自动标注转载数据中的图片一致性。

## 📋 功能特性

### 核心功能
- **自动下载比对**：自动下载muri和ord.page的图片进行比对
- **多维度相似度计算**：SSIM、特征匹配、颜色直方图、感知哈希
- **智能标注分类**：根据标准自动分类为"有效数据"、"不一样的图"等
- **水印识别**：自动识别常见水印类型（视觉中国、新华网等）
- **特殊规则处理**：支持虎扑、网易、央视新闻等特殊客户规则

### 高级功能
- **批量处理**：支持大规模CSV文件批量处理
- **并发处理**：多线程并发下载和比对
- **详细报告**：生成处理统计和标注分布报告
- **配置管理**：可自定义阈值和规则
- **错误处理**：完善的错误处理和重试机制

## 🚀 快速开始

### 安装依赖
```bash
pip install opencv-python pillow numpy pandas requests scikit-image pytesseract
```

### 基本使用
```bash
# 处理整个CSV文件
python complete_image_comparison_assistant.py -i input.csv -o output.csv

# 限制处理条数
python complete_image_comparison_assistant.py -i input.csv -l 100

# 使用更多线程加速
python complete_image_comparison_assistant.py -i input.csv -t 8 -v
```

### 输入文件格式
输入CSV文件应包含以下列：
- `muri`：我方库内的图片链接
- `ord.page`：图片所在客户网页链接
- `ord.id`：订单ID（可选）
- `ord.source`：图片来源（用于水印检测）

示例：
```csv
ord.id,muri,ord.page,ord.source
120638831,http://pictronapi.tuchong.com/api/image/xxx,https://m.weibo.cn/detail/xxx,adobe
```

## 📊 标注标准实现

### 标注分类
| 分类 | 说明 | 判定条件 |
|------|------|----------|
| **有效数据** | 图片一致且正常显示 | SSIM≥0.85 或 特征匹配率≥0.70 |
| **不一样的图** | 图片内容不同 | 相似度低于阈值 |
| **空白** | 网页显示为白图 | 平均像素值>95% |
| **无效数据** | 链接失效 | HTTP错误或超时 |
| **电影宣传图** | 影视海报/剧照 | source包含电影关键词 |
| **有水印** | 检测到水印 | OCR识别到水印关键词 |

### 水印类型识别
- vcg/视觉中国/cfp
- 新华网/新华视点/CIC/新华视点
- 中新社/中新网/CNS
- IC photo/ic/图虫
- 人民视觉/人民论坛/人民网/人民日报/人民图片
- 央视总台/中央广电总台央视新闻客户端

### 特殊客户规则
- **虎扑**：仅承认正文区域、自有账号发布
- **网易**：APP内查看的特殊处理
- **国广国际**：央视总台数据特殊标注

## ⚙️ 配置说明

### 阈值配置
```python
# 在代码中修改或通过配置文件
SSIM_THRESHOLD = 0.85        # 结构相似性阈值
FEATURE_MATCH_THRESHOLD = 0.70  # 特征匹配阈值
WHITE_IMAGE_THRESHOLD = 0.95   # 白图检测阈值
```

### 处理配置
```python
BATCH_SIZE = 100      # 批次大小
MAX_WORKERS = 4       # 最大并发数
DOWNLOAD_TIMEOUT = 10 # 下载超时（秒）
```

## 📈 输出结果

### 结果文件
输出CSV包含以下列：
- `ord.id`：订单ID
- `muri`：我方图片链接
- `ord.page`：客户页面链接
- `是否有效`：标注分类
- `水印`：水印类型（如有）
- `置信度`：判断置信度（0-1）
- `原因`：判断原因说明
- `特殊规则`：应用的特殊规则

### 报告文件
生成JSON格式的详细报告：
- 处理统计（成功率、处理时间等）
- 标注分布统计
- 水印识别统计
- 质量指标评估
- 改进建议

## 🧪 测试示例

### 创建测试数据
```python
from complete_image_comparison_assistant import create_example_data
example_file = create_example_data()
```

### 运行测试
```bash
# 测试示例数据
python complete_image_comparison_assistant.py -i example_data.csv

# 测试单个URL对
python complete_image_comparison_assistant.py --test-url "http://example.com/image1.jpg" "https://example.com/page1.html"
```

## 🔧 高级用法

### 自定义配置
```python
from complete_image_comparison_assistant import AssistantConfig, ImageComparisonAssistant

# 创建自定义配置
config = AssistantConfig()
config.SSIM_THRESHOLD = 0.90
config.SPECIAL_CLIENTS['myclient.com'] = "我的特殊客户"

# 使用自定义配置
assistant = ImageComparisonAssistant(config)
assistant.setup()
```

### 编程接口
```python
# 直接使用API
assistant = ImageComparisonAssistant()
assistant.setup()

# 处理数据
results = assistant.process_file("input.csv", "output.csv")

# 获取报告
report = assistant.generate_report(results)
```

## 🐛 故障排除

### 常见问题
1. **下载失败**：检查网络连接和URL有效性
2. **OCR识别失败**：安装tesseract-ocr和中文语言包
3. **内存不足**：减少批次大小或并发数
4. **处理速度慢**：增加并发数或优化网络

### 日志查看
```bash
# 查看详细日志
tail -f /home/workspace/image_comparison_assistant.log
```

## 📚 技术架构

### 模块设计
```
1. 图片下载模块 (ImageDownloader)
   ├── 网络请求
   ├── 错误处理
   └── 图片预处理

2. 特征提取模块 (FeatureExtractor)
   ├── ORB特征
   ├── 颜色直方图
   ├── 感知哈希
   └── 边缘检测

3. 相似度计算模块 (SimilarityCalculator)
   ├── SSIM计算
   ├── 特征匹配
   ├── 颜色相似度
   └── 哈希相似度

4. 标注规则引擎 (AnnotationRuleEngine)
   ├── 特殊客户规则
   ├── 水印识别
   ├── 电影内容检测
   └── 决策逻辑
```

### 算法流程
```
1. 下载图片 → 2. 预处理 → 3. 特征提取 → 4. 相似度计算 → 5. 规则判断 → 6. 输出结果
```

## 📄 许可证

本项目基于开源许可证发布。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请提交Issue或联系维护者。