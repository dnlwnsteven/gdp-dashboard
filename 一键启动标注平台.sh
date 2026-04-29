#!/bin/bash
# 可视化图片标注平台一键启动脚本

echo "=========================================="
echo "  可视化图片标注平台 - 一键启动"
echo "  版本: 2.0 (支持批量预加载)"
echo "  日期: 2026-04-29"
echo "=========================================="
echo ""

# 检查Python环境
echo "检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "错误：未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo ""
echo "检查Python依赖..."
echo "1. tkinter (GUI界面)..."

python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  警告：tkinter未安装，尝试安装..."
    
    # 根据不同系统安装tkinter
    if [ -f /etc/debian_version ]; then
        echo "  检测到Debian/Ubuntu系统，尝试安装..."
        sudo apt-get update && sudo apt-get install -y python3-tk
    elif [ -f /etc/redhat-release ]; then
        echo "  检测到RedHat/CentOS系统，尝试安装..."
        sudo yum install -y python3-tkinter
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  检测到macOS系统，请手动安装：brew install python-tk"
    else
        echo "  请手动安装tkinter："
        echo "  Debian/Ubuntu: sudo apt-get install python3-tk"
        echo "  RedHat/CentOS: sudo yum install python3-tkinter"
        echo "  macOS: brew install python-tk"
    fi
fi

echo "2. 图像处理库..."
python3 -c "import PIL, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  安装图像处理库..."
    pip3 install pillow opencv-python requests pandas numpy --quiet
fi

# 检查是否安装成功
echo ""
echo "验证依赖安装..."
python3 -c "
try:
    import tkinter
    print('✅ tkinter: 已安装')
except:
    print('❌ tkinter: 未安装')

try:
    from PIL import Image
    print('✅ Pillow: 已安装')
except:
    print('❌ Pillow: 未安装')

try:
    import requests
    print('✅ requests: 已安装')
except:
    print('❌ requests: 未安装')

try:
    import pandas as pd
    print('✅ pandas: 已安装')
except:
    print('❌ pandas: 未安装')
"

# 创建示例数据（如果不存在）
if [ ! -f "example_data.csv" ]; then
    echo ""
    echo "创建示例数据..."
    cat > example_data.csv << 'EOF'
ord.id,muri,uri,ord.page,ord.source
120638831,http://pictronapi.tuchong.com/api/image/2U405lZv6L23XMYQFpI2BT9FsypK37jD2h6i0eCla/preview?size=640,http://pictronapi.tuchong.com/api/image/2U405lZv6L23XMYQFpI2BT9FsypK37jD2h6i0eCla/original,https://m.weibo.cn/detail/5244532293111648,adobe
121531583,http://pictronapi.tuchong.com/api/image/2U405xkEHKTVXgrXTD7S9hH4uBLumaRB9VV7Y2WKc/preview?size=640,http://pictronapi.tuchong.com/api/image/2U405xkEHKTVXgrXTD7S9hH4uBLumaRB9VV7Y2WKc/original,http://www.neweekly.com.cn/article/shp1697627334,cnsphoto
121551152,http://pictronapi.tuchong.com/api/image/2U405vt8q8qKHXfk6K6Og8z0Y2K2e0R7V8W2g1Ws2/preview?size=640,http://pictronapi.tuchong.com/api/image/2U405vt8q8qKHXfk6K6Og8z0Y2K2e0R7V8W2g1Ws2/original,http://www.neweekly.com.cn/article/shp0355507852,cnsphoto
EOF
    echo "✅ 示例数据已创建: example_data.csv"
fi

# 创建配置文件
if [ ! -f "config.json" ]; then
    echo ""
    echo "创建配置文件..."
    cat > config.json << 'EOF'
{
    "platform": {
        "name": "可视化图片标注平台",
        "version": "2.0",
        "description": "专为转载数据标注设计的批量预加载平台"
    },
    "features": {
        "batch_preload": true,
        "dual_image_view": true,
        "annotation_standards": true,
        "export_csv": true,
        "export_json": true
    },
    "annotation_options": {
        "validity": ["有效数据", "电影宣传图", "有水印", "无效数据", "不一样的图", "空白"],
        "watermark": ["无", "视觉中国", "新华网", "中新社", "图虫", "人民日报", "央视总台", "角标水印", "其他水印"]
    }
}
EOF
    echo "✅ 配置文件已创建: config.json"
fi

# 启动平台
echo ""
echo "=========================================="
echo "  启动可视化图片标注平台..."
echo "=========================================="
echo ""
echo "使用说明："
echo "1. 点击 '加载CSV数据' 选择你的转载数据文件"
echo "2. 点击 '批量预加载图片' 提前下载所有图片"
echo "3. 使用左右箭头或随机跳转浏览图片"
echo "4. 在右侧选择标注选项"
echo "5. 标注会自动保存，也可以手动导出"
echo ""
echo "平台即将启动..."
echo ""

# 启动Python程序
python3 visual_annotation_platform.py

echo ""
echo "=========================================="
echo "  平台已关闭"
echo "=========================================="
echo ""
echo "标注结果文件："
ls -la *.csv *.json 2>/dev/null | grep -E "(标注|annotation|result)" || echo "（暂无结果文件）"
echo ""
echo "缓存目录："
ls -la ~/.image_annotation_cache 2>/dev/null || echo "（缓存目录为空）"
echo ""
echo "感谢使用可视化图片标注平台！"