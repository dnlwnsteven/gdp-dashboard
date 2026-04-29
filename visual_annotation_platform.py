#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化图片标注平台 - 批量预加载版本
专为转载数据标注设计
支持同时查看muri、uri、网页（ord.page）三列图片
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import time
import threading
from queue import Queue
from typing import Dict, List, Tuple, Optional, Any
import logging
from pathlib import Path
import csv
from datetime import datetime

# 图像处理相关
try:
    from PIL import Image
    import requests
    from io import BytesIO
    import cv2
    HAS_IMAGE_LIBS = True
except ImportError:
    HAS_IMAGE_LIBS = False
    print("警告：缺少图像处理库，请安装：pip install pillow opencv-python requests")

# 界面相关
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    import tkinter.font as tkfont
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False
    print("警告：缺少tkinter库")

# 配置
class Config:
    """平台配置"""
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".image_annotation_cache")
    MAX_THREADS = 10  # 最大并发下载线程数
    MAX_RETRIES = 3   # 下载重试次数
    TIMEOUT = 30      # 下载超时时间(秒)
    MAX_IMAGE_SIZE = (800, 600)  # 最大显示尺寸
    
    # 标注选项
    VALIDITY_OPTIONS = [
        ("有效数据", "有效数据"),
        ("电影宣传图", "电影宣传图"), 
        ("有水印", "有水印"),
        ("无效数据", "无效数据"),
        ("不一样的图", "不一样的图"),
        ("空白", "空白")
    ]
    
    WATERMARK_OPTIONS = [
        ("无", "无"),
        ("视觉中国", "视觉中国"),
        ("新华网", "新华网"),
        ("中新社", "中新社"),
        ("图虫", "图虫"),
        ("人民日报", "人民日报"),
        ("央视总台", "央视总台"),
        ("角标水印", "角标水印"),
        ("其他水印", "其他水印")
    ]

class ImageDownloader:
    """图片下载器 - 支持批量预加载"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self._ensure_cache_dir()
        self.download_queue = Queue()
        self.results = {}
        self.lock = threading.Lock()
        
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_cache_path(self, url: str) -> str:
        """获取缓存文件路径"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.jpg")
    
    def download_image(self, url: str, retry_count: int = 0) -> Optional[Image.Image]:
        """下载单张图片"""
        if not url or pd.isna(url):
            return None
            
        cache_path = self.get_cache_path(url)
        
        # 检查缓存
        if os.path.exists(cache_path):
            try:
                return Image.open(cache_path)
            except:
                pass  # 缓存损坏，重新下载
                
        # 下载图片
        try:
            response = requests.get(url, timeout=Config.TIMEOUT)
            response.raise_for_status()
            
            # 保存到缓存
            with open(cache_path, 'wb') as f:
                f.write(response.content)
                
            return Image.open(BytesIO(response.content))
        except Exception as e:
            if retry_count < Config.MAX_RETRIES:
                time.sleep(1)
                return self.download_image(url, retry_count + 1)
            print(f"下载失败 {url}: {e}")
            return None
    
    def download_worker(self):
        """下载工作线程"""
        while True:
            try:
                item = self.download_queue.get(timeout=1)
                if item is None:  # 结束信号
                    break
                    
                idx, url_type, url = item
                if url:
                    image = self.download_image(url)
                    with self.lock:
                        self.results[(idx, url_type)] = image
                else:
                    with self.lock:
                        self.results[(idx, url_type)] = None
                        
                self.download_queue.task_done()
            except:
                continue
    
    def batch_download(self, data: pd.DataFrame) -> Dict[Tuple, Optional[Image.Image]]:
        """批量下载所有图片"""
        # 准备下载任务
        tasks = []
        for idx, row in data.iterrows():
            # MURI图片
            if 'muri' in data.columns and row['muri']:
                tasks.append((idx, 'muri', row['muri']))
            # URI图片  
            if 'uri' in data.columns and row['uri']:
                tasks.append((idx, 'uri', row['uri']))
            # 网页缩略图（可选）
            if 'ord.page' in data.columns and row['ord.page']:
                tasks.append((idx, 'page', row['ord.page']))
        
        # 启动工作线程
        self.results = {}
        threads = []
        for _ in range(min(Config.MAX_THREADS, len(tasks))):
            t = threading.Thread(target=self.download_worker, daemon=True)
            t.start()
            threads.append(t)
        
        # 添加任务到队列
        for task in tasks:
            self.download_queue.put(task)
        
        # 等待所有任务完成
        self.download_queue.join()
        
        # 发送结束信号
        for _ in range(len(threads)):
            self.download_queue.put(None)
        
        # 等待线程结束
        for t in threads:
            t.join(timeout=2)
            
        return self.results

class AnnotationPlatform:
    """可视化标注平台"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("图片标注平台 - 转载数据专用")
        self.root.geometry("1400x900")
        
        # 数据存储
        self.data = None
        self.current_index = 0
        self.annotations = {}
        self.image_cache = {}  # 缓存加载的图片
        self.download_results = None
        
        # 创建界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 控制面板 (顶部)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 数据加载
        ttk.Button(control_frame, text="加载CSV数据", command=self.load_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="批量预加载图片", command=self.preload_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存标注", command=self.save_annotations).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="导出结果", command=self.export_results).pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        self.progress_var = tk.StringVar(value="0/0")
        ttk.Label(control_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=20)
        
        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # 内容区域 (左右分割)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧 - 图片显示区
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # MURI图片
        muri_frame = ttk.LabelFrame(left_frame, text="MURI图片")
        muri_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.muri_label = ttk.Label(muri_frame, text="MURI图片将显示在这里")
        self.muri_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # URI图片
        uri_frame = ttk.LabelFrame(left_frame, text="URI图片")
        uri_frame.pack(fill=tk.BOTH, expand=True)
        
        self.uri_label = ttk.Label(uri_frame, text="URI图片将显示在这里")
        self.uri_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 右侧 - 标注和控制区
        right_frame = ttk.Frame(content_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)  # 固定宽度
        
        # 网页信息
        web_frame = ttk.LabelFrame(right_frame, text="网页信息")
        web_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.web_text = scrolledtext.ScrolledText(web_frame, height=3, wrap=tk.WORD)
        self.web_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标注选项
        annotation_frame = ttk.LabelFrame(right_frame, text="标注选项")
        annotation_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 是否有效
        ttk.Label(annotation_frame, text="是否有效：").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.validity_var = tk.StringVar()
        validity_frame = ttk.Frame(annotation_frame)
        validity_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for text, value in Config.VALIDITY_OPTIONS:
            rb = ttk.Radiobutton(validity_frame, text=text, value=value, 
                                variable=self.validity_var)
            rb.pack(anchor=tk.W)
        
        # 水印类型
        ttk.Label(annotation_frame, text="水印类型：").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.watermark_var = tk.StringVar(value="无")
        watermark_frame = ttk.Frame(annotation_frame)
        watermark_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for text, value in Config.WATERMARK_OPTIONS:
            rb = ttk.Radiobutton(watermark_frame, text=text, value=value,
                                variable=self.watermark_var)
            rb.pack(anchor=tk.W)
        
        # 备注
        ttk.Label(annotation_frame, text="备注：").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.note_var = tk.StringVar()
        ttk.Entry(annotation_frame, textvariable=self.note_var).pack(fill=tk.X, padx=10, pady=5)
        
        # 导航控制
        nav_frame = ttk.Frame(right_frame)
        nav_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(nav_frame, text="上一张", command=self.previous_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="下一张", command=self.next_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="随机跳转", command=self.random_image).pack(side=tk.LEFT, padx=5)
        
        # 跳转到指定ID
        jump_frame = ttk.Frame(right_frame)
        jump_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(jump_frame, text="跳转到ID:").pack(side=tk.LEFT, padx=5)
        self.jump_var = tk.StringVar()
        ttk.Entry(jump_frame, textvariable=self.jump_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(jump_frame, text="跳转", command=self.jump_to_id).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # 批量操作
        batch_frame = ttk.LabelFrame(right_frame, text="批量操作")
        batch_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(batch_frame, text="标记所有为有效数据", 
                  command=lambda: self.batch_annotate("validity", "有效数据")).pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(batch_frame, text="标记所有为无效数据", 
                  command=lambda: self.batch_annotate("validity", "无效数据")).pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(batch_frame, text="清除所有标注", 
                  command=self.clear_all_annotations).pack(fill=tk.X, padx=10, pady=5)
    
    def load_data(self):
        """加载CSV数据"""
        file_path = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            self.data = pd.read_csv(file_path)
            required_cols = ['muri', 'uri', 'ord.page']
            missing_cols = [col for col in required_cols if col not in self.data.columns]
            
            if missing_cols:
                messagebox.showwarning("警告", f"缺少必要的列: {missing_cols}")
                return
                
            # 初始化标注
            self.annotations = {}
            self.current_index = 0
            self.image_cache = {}
            
            # 更新进度
            self.update_progress()
            self.update_status(f"加载成功: {len(self.data)} 条记录")
            
            # 显示第一条数据
            self.show_current_image()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {e}")
    
    def preload_images(self):
        """批量预加载所有图片"""
        if self.data is None:
            messagebox.showwarning("警告", "请先加载数据")
            return
            
        self.update_status("开始批量预加载图片...")
        
        # 创建下载器
        downloader = ImageDownloader()
        
        # 启动下载线程
        def download_thread():
            try:
                self.download_results = downloader.batch_download(self.data)
                self.root.after(0, self.on_preload_complete)
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"预加载失败: {e}"))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def on_preload_complete(self):
        """预加载完成回调"""
        loaded_count = len([v for v in self.download_results.values() if v is not None])
        total_count = len(self.download_results)
        
        self.update_status(f"预加载完成: {loaded_count}/{total_count} 张图片")
        messagebox.showinfo("完成", f"图片预加载完成\n成功: {loaded_count}\n失败: {total_count - loaded_count}")
        
        # 缓存当前图片
        self.cache_current_images()
    
    def cache_current_images(self):
        """缓存当前显示的图片"""
        if self.download_results is None:
            return
            
        idx = self.current_index
        
        # 缓存MURI图片
        muri_key = (idx, 'muri')
        if muri_key in self.download_results:
            self.image_cache['muri'] = self.download_results[muri_key]
        
        # 缓存URI图片
        uri_key = (idx, 'uri')
        if uri_key in self.download_results:
            self.image_cache['uri'] = self.download_results[uri_key]
        
        # 更新显示
        self.update_image_display()
    
    def show_current_image(self):
        """显示当前图片"""
        if self.data is None or len(self.data) == 0:
            return
            
        row = self.data.iloc[self.current_index]
        
        # 更新网页信息
        web_info = f"网页URL:\n{row['ord.page']}\n\n记录ID: {row.name}"
        if 'ord.id' in self.data.columns:
            web_info += f"\n数据ID: {row['ord.id']}"
        self.web_text.delete(1.0, tk.END)
        self.web_text.insert(1.0, web_info)
        
        # 加载标注
        if self.current_index in self.annotations:
            anno = self.annotations[self.current_index]
            self.validity_var.set(anno.get('validity', ''))
            self.watermark_var.set(anno.get('watermark', '无'))
            self.note_var.set(anno.get('note', ''))
        else:
            self.validity_var.set('')
            self.watermark_var.set('无')
            self.note_var.set('')
        
        # 显示图片
        self.update_image_display()
        self.update_progress()
    
    def update_image_display(self):
        """更新图片显示"""
        # MURI图片
        if 'muri' in self.image_cache and self.image_cache['muri']:
            self.display_image(self.muri_label, self.image_cache['muri'], "MURI图片")
        else:
            row = self.data.iloc[self.current_index]
            muri_url = row['muri'] if 'muri' in row else None
            if muri_url:
                self.muri_label.config(text=f"加载中...\n{muri_url[:50]}...")
            else:
                self.muri_label.config(text="无MURI图片")
        
        # URI图片
        if 'uri' in self.image_cache and self.image_cache['uri']:
            self.display_image(self.uri_label, self.image_cache['uri'], "URI图片")
        else:
            row = self.data.iloc[self.current_index]
            uri_url = row['uri'] if 'uri' in row else None
            if uri_url:
                self.uri_label.config(text=f"加载中...\n{uri_url[:50]}...")
            else:
                self.uri_label.config(text="无URI图片")
    
    def display_image(self, label: ttk.Label, image: Image.Image, title: str):
        """在标签上显示图片"""
        try:
            # 调整图片大小
            image.thumbnail(Config.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            
            # 转换为tkinter格式
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(image)
            
            # 更新标签
            label.config(image=photo, text="")
            label.image = photo  # 保持引用
        except Exception as e:
            label.config(text=f"{title}显示失败: {e}")
    
    def save_current_annotation(self):
        """保存当前标注"""
        if self.data is None:
            return
            
        idx = self.current_index
        
        # 创建标注对象
        annotation = {
            'validity': self.validity_var.get(),
            'watermark': self.watermark_var.get(),
            'note': self.note_var.get(),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存到内存
        self.annotations[idx] = annotation
        self.update_status(f"已保存第 {idx+1} 条标注")
    
    def next_image(self):
        """下一张图片"""
        if self.data is None or len(self.data) == 0:
            return
            
        # 保存当前标注
        self.save_current_annotation()
        
        # 移动到下一张
        if self.current_index < len(self.data) - 1:
            self.current_index += 1
            self.cache_current_images()
            self.show_current_image()
    
    def previous_image(self):
        """上一张图片"""
        if self.data is None or len(self.data) == 0:
            return
            
        # 保存当前标注
        self.save_current_annotation()
        
        # 移动到上一张
        if self.current_index > 0:
            self.current_index -= 1
            self.cache_current_images()
            self.show_current_image()
    
    def random_image(self):
        """随机跳转"""
        if self.data is None or len(self.data) == 0:
            return
            
        # 保存当前标注
        self.save_current_annotation()
        
        # 随机选择
        import random
        self.current_index = random.randint(0, len(self.data) - 1)
        self.cache_current_images()
        self.show_current_image()
    
    def jump_to_id(self):
        """跳转到指定ID"""
        if self.data is None:
            return
            
        try:
            target_id = int(self.jump_var.get())
            
            # 查找ID
            if 'ord.id' in self.data.columns:
                matches = self.data[self.data['ord.id'] == target_id]
                if len(matches) > 0:
                    idx = matches.index[0]
                    self.current_index = idx
                    self.cache_current_images()
                    self.show_current_image()
                    self.update_status(f"跳转到ID: {target_id}")
                else:
                    self.update_status(f"未找到ID: {target_id}")
            else:
                # 使用行号
                if 0 <= target_id < len(self.data):
                    self.current_index = target_id
                    self.cache_current_images()
                    self.show_current_image()
                    self.update_status(f"跳转到行号: {target_id}")
                else:
                    self.update_status(f"无效行号: {target_id}")
                    
        except ValueError:
            self.update_status("请输入有效的数字ID")
    
    def batch_annotate(self, field: str, value: str):
        """批量标注"""
        if self.data is None:
            return
            
        # 确认操作
        if not messagebox.askyesno("确认", f"确定要将所有记录标记为'{value}'吗？"):
            return
            
        # 批量设置
        for idx in range(len(self.data)):
            if idx not in self.annotations:
                self.annotations[idx] = {}
            self.annotations[idx][field] = value
        
        # 更新当前显示
        if field == 'validity':
            self.validity_var.set(value)
        elif field == 'watermark':
            self.watermark_var.set(value)
        
        self.update_status(f"已批量标记所有记录: {field}={value}")
    
    def clear_all_annotations(self):
        """清除所有标注"""
        if not messagebox.askyesno("确认", "确定要清除所有标注吗？"):
            return
            
        self.annotations = {}
        self.validity_var.set('')
        self.watermark_var.set('无')
        self.note_var.set('')
        
        self.update_status("已清除所有标注")
    
    def save_annotations(self):
        """保存标注到文件"""
        if not self.annotations:
            messagebox.showwarning("警告", "没有标注数据可保存")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="保存标注文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # 构建完整数据
            save_data = {
                'metadata': {
                    'total_records': len(self.data) if self.data else 0,
                    'annotated_count': len(self.annotations),
                    'save_time': datetime.now().isoformat(),
                    'data_source': self.data_path if hasattr(self, 'data_path') else 'unknown'
                },
                'annotations': self.annotations
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
            self.update_status(f"标注已保存到: {file_path}")
            messagebox.showinfo("成功", f"已保存 {len(self.annotations)} 条标注")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def export_results(self):
        """导出标注结果到CSV"""
        if self.data is None:
            messagebox.showwarning("警告", "请先加载数据")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="导出结果",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # 复制数据
            result_df = self.data.copy()
            
            # 添加标注列
            result_df['标注_是否有效'] = ''
            result_df['标注_水印类型'] = ''
            result_df['标注_备注'] = ''
            result_df['标注_时间'] = ''
            
            # 填充标注数据
            for idx, anno in self.annotations.items():
                if idx < len(result_df):
                    result_df.at[idx, '标注_是否有效'] = anno.get('validity', '')
                    result_df.at[idx, '标注_水印类型'] = anno.get('watermark', '')
                    result_df.at[idx, '标注_备注'] = anno.get('note', '')
                    result_df.at[idx, '标注_时间'] = anno.get('timestamp', '')
            
            # 保存到CSV
            result_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            self.update_status(f"结果已导出到: {file_path}")
            messagebox.showinfo("成功", f"已导出 {len(result_df)} 条记录")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def update_progress(self):
        """更新进度显示"""
        if self.data is not None:
            total = len(self.data)
            current = self.current_index + 1
            annotated = len([k for k in self.annotations.keys() if isinstance(k, int)])
            self.progress_var.set(f"{current}/{total} (已标注: {annotated})")
    
    def update_status(self, message: str):
        """更新状态信息"""
        self.status_var.set(message)
        print(f"状态: {message}")

def main():
    """主函数"""
    if not HAS_TKINTER:
        print("错误：需要tkinter库，请在Python环境中安装")
        return
    
    if not HAS_IMAGE_LIBS:
        print("警告：缺少图像处理库，部分功能可能受限")
        print("请安装：pip install pillow opencv-python requests")
    
    # 创建主窗口
    root = tk.Tk()
    
    # 设置字体
    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
    except:
        pass
    
    # 创建平台
    app = AnnotationPlatform(root)
    
    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    main()