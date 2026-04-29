#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理工具 - 为可视化标注平台提供辅助功能
支持：数据预处理、结果统计、批量导出等
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

class BatchProcessor:
    """批量处理工具类"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        log_dir = self.data_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"batch_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def validate_csv(self, csv_path: str) -> Tuple[bool, List[str]]:
        """
        验证CSV文件格式
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        try:
            # 检查文件是否存在
            if not os.path.exists(csv_path):
                errors.append(f"文件不存在: {csv_path}")
                return False, errors
            
            # 尝试读取CSV
            df = pd.read_csv(csv_path)
            
            # 检查必需列
            required_cols = ['muri', 'uri', 'ord.page']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                errors.append(f"缺少必需列: {missing_cols}")
            
            # 检查数据完整性
            total_rows = len(df)
            
            # 检查空值
            for col in required_cols:
                if col in df.columns:
                    null_count = df[col].isna().sum()
                    if null_count > 0:
                        errors.append(f"{col}列有{null_count}个空值")
            
            # 检查URL格式
            url_cols = ['muri', 'uri', 'ord.page']
            for col in url_cols:
                if col in df.columns:
                    # 简单检查是否包含http://或https://
                    url_count = df[col].astype(str).str.contains(r'^https?://').sum()
                    if url_count < total_rows * 0.8:  # 80%的URL应该有效
                        errors.append(f"{col}列URL格式可能有问题")
            
            if not errors:
                self.logger.info(f"CSV验证通过: {csv_path} ({total_rows}条记录)")
                return True, []
            else:
                self.logger.warning(f"CSV验证发现问题: {errors}")
                return False, errors
                
        except Exception as e:
            errors.append(f"读取CSV文件失败: {e}")
            return False, errors
    
    def preprocess_data(self, input_csv: str, output_csv: str = None) -> pd.DataFrame:
        """
        数据预处理
        
        Args:
            input_csv: 输入CSV文件路径
            output_csv: 输出CSV文件路径（可选）
            
        Returns:
            处理后的DataFrame
        """
        try:
            # 读取数据
            df = pd.read_csv(input_csv)
            
            # 1. 去除重复记录
            original_count = len(df)
            df = df.drop_duplicates()
            if len(df) < original_count:
                self.logger.info(f"去除了{original_count - len(df)}条重复记录")
            
            # 2. 清理URL
            url_cols = ['muri', 'uri', 'ord.page']
            for col in url_cols:
                if col in df.columns:
                    # 去除空格
                    df[col] = df[col].astype(str).str.strip()
                    # 替换空字符串为NaN
                    df[col] = df[col].replace({'': np.nan, 'nan': np.nan, 'NaN': np.nan})
            
            # 3. 添加ID（如果不存在）
            if 'ord.id' not in df.columns:
                df['ord.id'] = range(1, len(df) + 1)
                self.logger.info(f"添加了ord.id列")
            
            # 4. 添加处理时间
            df['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 5. 保存处理后的数据
            if output_csv:
                df.to_csv(output_csv, index=False, encoding='utf-8-sig')
                self.logger.info(f"预处理完成，保存到: {output_csv}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"数据预处理失败: {e}")
            raise
    
    def analyze_annotations(self, annotation_file: str) -> Dict[str, Any]:
        """
        分析标注结果
        
        Args:
            annotation_file: 标注文件路径（JSON格式）
            
        Returns:
            分析结果字典
        """
        try:
            with open(annotation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            annotations = data.get('annotations', {})
            total_records = data.get('metadata', {}).get('total_records', 0)
            
            # 统计标注分布
            validity_counts = {}
            watermark_counts = {}
            
            for idx, anno in annotations.items():
                validity = anno.get('validity', '未标注')
                watermark = anno.get('watermark', '未标注')
                
                validity_counts[validity] = validity_counts.get(validity, 0) + 1
                watermark_counts[watermark] = watermark_counts.get(watermark, 0) + 1
            
            # 计算标注率
            annotated_rate = len(annotations) / total_records if total_records > 0 else 0
            
            result = {
                'total_records': total_records,
                'annotated_count': len(annotations),
                'annotated_rate': round(annotated_rate * 100, 2),
                'validity_distribution': validity_counts,
                'watermark_distribution': watermark_counts,
                'analysis_time': datetime.now().isoformat()
            }
            
            # 保存分析结果
            report_file = self.data_dir / "reports" / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_file.parent.mkdir(exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"标注分析完成，报告保存到: {report_file}")
            return result
            
        except Exception as e:
            self.logger.error(f"标注分析失败: {e}")
            raise
    
    def merge_results(self, data_csv: str, annotation_file: str, output_csv: str) -> pd.DataFrame:
        """
        合并数据和标注结果
        
        Args:
            data_csv: 原始数据CSV
            annotation_file: 标注文件（JSON）
            output_csv: 输出文件路径
            
        Returns:
            合并后的DataFrame
        """
        try:
            # 读取原始数据
            df_data = pd.read_csv(data_csv)
            
            # 读取标注数据
            with open(annotation_file, 'r', encoding='utf-8') as f:
                annotation_data = json.load(f)
            
            annotations = annotation_data.get('annotations', {})
            
            # 创建标注列
            df_data['标注_是否有效'] = ''
            df_data['标注_水印类型'] = ''
            df_data['标注_备注'] = ''
            df_data['标注_时间'] = ''
            df_data['标注_状态'] = '未标注'
            
            # 填充标注数据
            for idx_str, anno in annotations.items():
                try:
                    idx = int(idx_str) if idx_str.isdigit() else int(float(idx_str))
                    if idx < len(df_data):
                        df_data.at[idx, '标注_是否有效'] = anno.get('validity', '')
                        df_data.at[idx, '标注_水印类型'] = anno.get('watermark', '')
                        df_data.at[idx, '标注_备注'] = anno.get('note', '')
                        df_data.at[idx, '标注_时间'] = anno.get('timestamp', '')
                        df_data.at[idx, '标注_状态'] = '已标注'
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"处理标注记录{idx_str}时出错: {e}")
                    continue
            
            # 保存合并结果
            df_data.to_csv(output_csv, index=False, encoding='utf-8-sig')
            
            # 生成统计信息
            total = len(df_data)
            annotated = len([v for v in df_data['标注_状态'] if v == '已标注'])
            
            self.logger.info(f"合并完成: {total}条记录，{annotated}条已标注 ({annotated/total*100:.1f}%)")
            self.logger.info(f"结果保存到: {output_csv}")
            
            return df_data
            
        except Exception as e:
            self.logger.error(f"合并结果失败: {e}")
            raise
    
    def generate_summary_report(self, merged_csv: str) -> Dict[str, Any]:
        """
        生成汇总报告
        
        Args:
            merged_csv: 合并后的CSV文件
            
        Returns:
            报告内容字典
        """
        try:
            df = pd.read_csv(merged_csv)
            
            # 基础统计
            total_records = len(df)
            annotated_count = df['标注_状态'].eq('已标注').sum()
            
            # 有效性分布
            validity_dist = df['标注_是否有效'].value_counts().to_dict()
            
            # 水印分布
            watermark_dist = df['标注_水印类型'].value_counts().to_dict()
            
            # 时间统计
            if '标注_时间' in df.columns:
                # 尝试解析时间
                time_col = pd.to_datetime(df['标注_时间'], errors='coerce')
                if not time_col.isna().all():
                    first_time = time_col.min()
                    last_time = time_col.max()
                    avg_time_per_record = (last_time - first_time).total_seconds() / annotated_count if annotated_count > 0 else 0
                else:
                    first_time = last_time = avg_time_per_record = None
            else:
                first_time = last_time = avg_time_per_record = None
            
            # 构建报告
            report = {
                'summary': {
                    'total_records': total_records,
                    'annotated_records': int(annotated_count),
                    'annotation_rate': round(annotated_count / total_records * 100, 2) if total_records > 0 else 0,
                    'unannotated_records': int(total_records - annotated_count)
                },
                'validity_analysis': {
                    'distribution': validity_dist,
                    'top_validity': max(validity_dist.items(), key=lambda x: x[1])[0] if validity_dist else '无数据'
                },
                'watermark_analysis': {
                    'distribution': watermark_dist,
                    'top_watermark': max(watermark_dist.items(), key=lambda x: x[1])[0] if watermark_dist else '无数据'
                },
                'time_analysis': {
                    'first_annotation': str(first_time) if first_time else '无数据',
                    'last_annotation': str(last_time) if last_time else '无数据',
                    'avg_time_per_record_seconds': round(avg_time_per_record, 2) if avg_time_per_record else '无数据'
                },
                'quality_metrics': {
                    'completeness_score': round(annotated_count / total_records * 100, 2) if total_records > 0 else 0,
                    'consistency_score': self._calculate_consistency_score(df),
                    'timeliness_score': self._calculate_timeliness_score(df)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            # 保存报告
            report_file = self.data_dir / "reports" / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_file.parent.mkdir(exist_ok=True)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # 生成Markdown报告
            self._generate_markdown_report(report, report_file.with_suffix('.md'))
            
            self.logger.info(f"汇总报告生成完成: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"生成汇总报告失败: {e}")
            raise
    
    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """计算一致性分数"""
        try:
            # 检查相同来源的标注是否一致
            if 'ord.source' in df.columns:
                source_groups = df.groupby('ord.source')
                consistency_scores = []
                
                for source, group in source_groups:
                    if len(group) > 1:
                        # 计算相同来源中相同标注的比例
                        validity_consistency = group['标注_是否有效'].nunique() / len(group)
                        watermark_consistency = group['标注_水印类型'].nunique() / len(group)
                        avg_consistency = (validity_consistency + watermark_consistency) / 2
                        consistency_scores.append(avg_consistency)
                
                if consistency_scores:
                    return round(np.mean(consistency_scores) * 100, 2)
            
            return 0.0
            
        except:
            return 0.0
    
    def _calculate_timeliness_score(self, df: pd.DataFrame) -> float:
        """计算及时性分数"""
        try:
            if '标注_时间' in df.columns:
                # 检查标注时间是否集中在合理范围内
                time_col = pd.to_datetime(df['标注_时间'], errors='coerce')
                if not time_col.isna().all():
                    time_std = time_col.std().total_seconds()
                    # 标准差越小，说明标注时间越集中，及时性越好
                    if time_std > 0:
                        return round(100 / (1 + time_std / 3600), 2)  # 转换为小时
            return 0.0
        except:
            return 0.0
    
    def _generate_markdown_report(self, report: Dict, output_path: Path):
        """生成Markdown格式报告"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# 图片标注汇总报告\n\n")
                f.write(f"生成时间: {report['generated_at']}\n\n")
                
                # 摘要
                f.write("## 📊 数据摘要\n\n")
                summary = report['summary']
                f.write(f"- **总记录数**: {summary['total_records']}\n")
                f.write(f"- **已标注记录**: {summary['annotated_records']}\n")
                f.write(f"- **标注率**: {summary['annotation_rate']}%\n")
                f.write(f"- **未标注记录**: {summary['unannotated_records']}\n\n")
                
                # 有效性分析
                f.write("## ✅ 有效性标注分布\n\n")
                validity = report['validity_analysis']
                f.write(f"**主要类别**: {validity['top_validity']}\n\n")
                f.write("| 类别 | 数量 | 占比 |\n")
                f.write("|------|------|------|\n")
                for category, count in validity['distribution'].items():
                    percentage = count / summary['total_records'] * 100
                    f.write(f"| {category} | {count} | {percentage:.1f}% |\n")
                f.write("\n")
                
                # 水印分析
                f.write("## 🏷️ 水印标注分布\n\n")
                watermark = report['watermark_analysis']
                f.write(f"**主要水印**: {watermark['top_watermark']}\n\n")
                f.write("| 水印类型 | 数量 | 占比 |\n")
                f.write("|----------|------|------|\n")
                for wtype, count in watermark['distribution'].items():
                    percentage = count / summary['total_records'] * 100
                    f.write(f"| {wtype} | {count} | {percentage:.1f}% |\n")
                f.write("\n")
                
                # 质量指标
                f.write("## 📈 质量指标\n\n")
                metrics = report['quality_metrics']
                f.write(f"- **完整性分数**: {metrics['completeness_score']}/100\n")
                f.write(f"- **一致性分数**: {metrics['consistency_score']}/100\n")
                f.write(f"- **及时性分数**: {metrics['timeliness_score']}/100\n\n")
                
                # 时间分析
                f.write("## ⏰ 时间分析\n\n")
                time_analysis = report['time_analysis']
                f.write(f"- **首次标注**: {time_analysis['first_annotation']}\n")
                f.write(f"- **最后标注**: {time_analysis['last_annotation']}\n")
                f.write(f"- **平均每条耗时**: {time_analysis['avg_time_per_record_seconds']}秒\n\n")
                
                f.write("---\n")
                f.write("*报告由可视化标注平台批量处理工具生成*\n")
            
            self.logger.info(f"Markdown报告生成完成: {output_path}")
            
        except Exception as e:
            self.logger.warning(f"生成Markdown报告失败: {e}")

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量处理工具 - 可视化标注平台辅助工具')
    parser.add_argument('action', choices=['validate', 'preprocess', 'analyze', 'merge', 'report'],
                       help='执行的操作')
    parser.add_argument('--input', '-i', required=True, help='输入文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--annotation', '-a', help='标注文件路径（JSON格式）')
    parser.add_argument('--data', '-d', help='数据文件路径（CSV格式）')
    
    args = parser.parse_args()
    
    processor = BatchProcessor()
    
    try:
        if args.action == 'validate':
            # 验证CSV文件
            is_valid, errors = processor.validate_csv(args.input)
            if is_valid:
                print("✅ CSV文件验证通过")
            else:
                print("❌ CSV文件验证失败:")
                for error in errors:
                    print(f"  - {error}")
        
        elif args.action == 'preprocess':
            # 数据预处理
            if not args.output:
                print("错误：预处理需要指定输出文件路径 (--output)")
                return
            
            df = processor.preprocess_data(args.input, args.output)
            print(f"✅ 数据预处理完成: {len(df)}条记录")
            print(f"   输出文件: {args.output}")
        
        elif args.action == 'analyze':
            # 分析标注结果
            if not args.input.endswith('.json'):
                print("错误：分析操作需要JSON格式的标注文件")
                return
            
            result = processor.analyze_annotations(args.input)
            print(f"✅ 标注分析完成")
            print(f"   总记录: {result['total_records']}")
            print(f"   已标注: {result['annotated_count']}")
            print(f"   标注率: {result['annotated_rate']}%")
        
        elif args.action == 'merge':
            # 合并数据和标注
            if not args.data:
                print("错误：合并操作需要数据文件 (--data)")
                return
            
            if not args.annotation:
                print("错误：合并操作需要标注文件 (--annotation)")
                return
            
            if not args.output:
                print("错误：合并操作需要输出文件路径 (--output)")
                return
            
            df = processor.merge_results(args.data, args.annotation, args.output)
            print(f"✅ 数据合并完成")
            print(f"   输出文件: {args.output}")
        
        elif args.action == 'report':
            # 生成汇总报告
            if not args.input.endswith('.csv'):
                print("错误：报告生成需要CSV格式的合并文件")
                return
            
            report = processor.generate_summary_report(args.input)
            print(f"✅ 汇总报告生成完成")
            print(f"   标注率: {report['summary']['annotation_rate']}%")
            print(f"   主要类别: {report['validity_analysis']['top_validity']}")
            print(f"   主要水印: {report['watermark_analysis']['top_watermark']}")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()