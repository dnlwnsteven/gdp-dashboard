#!/usr/bin/env python3
"""
可视化标注平台主运行脚本
用于快速启动标注平台
"""

import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description='可视化标注平台启动器')
    parser.add_argument('--data', '-d', help='数据文件路径 (CSV格式)', default='examples/示例数据.csv')
    parser.add_argument('--port', '-p', help='运行端口', type=int, default=8501)
    parser.add_argument('--config', '-c', help='配置文件路径', default='config.json')
    parser.add_argument('--batch', '-b', action='store_true', help='批量处理模式')
    parser.add_argument('--output', '-o', help='输出文件路径', default='outputs/标注结果.csv')
    
    args = parser.parse_args()
    
    # 检查依赖
    print("=" * 60)
    print("    可视化标注平台启动器 v2.0")
    print("=" * 60)
    
    # 检查Python环境
    print("[1/5] 检查Python环境...")
    try:
        subprocess.run([sys.executable, '--version'], check=True)
    except Exception as e:
        print(f"错误: Python环境检查失败 - {e}")
        sys.exit(1)
    
    # 检查数据文件
    print("[2/5] 检查数据文件...")
    if not os.path.exists(args.data):
        print(f"警告: 数据文件 '{args.data}' 不存在")
        print("      使用示例数据文件...")
        if not os.path.exists('examples/示例数据.csv'):
            print("错误: 示例数据文件也不存在")
            sys.exit(1)
        args.data = 'examples/示例数据.csv'
    
    # 检查配置文件
    print("[3/5] 检查配置文件...")
    if not os.path.exists(args.config):
        print(f"警告: 配置文件 '{args.config}' 不存在")
        print("      使用默认配置...")
    
    # 创建输出目录
    print("[4/5] 创建输出目录...")
    os.makedirs('outputs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 启动平台
    print("[5/5] 启动可视化标注平台...")
    print(f"数据文件: {args.data}")
    print(f"运行端口: http://localhost:{args.port}")
    print(f"输出文件: {args.output}")
    print("=" * 60)
    
    # 构建启动命令
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        'src/visual_annotation_platform.py',
        '--server.port', str(args.port),
        '--',
        '--data', args.data,
        '--config', args.config,
        '--output', args.output
    ]
    
    if args.batch:
        cmd.append('--batch')
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n标注平台已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
