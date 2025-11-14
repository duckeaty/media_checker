import os
import cv2
import argparse
from datetime import datetime
import numpy as np
import sys
import time

# 支持所有常见视频格式
VIDEO_EXTENSIONS = [
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm',
    '.m4v', '.mpeg', '.mpg', '.3gp', '.ts', '.mts', '.m2ts',
    '.vob', '.ogv', '.drc', '.mxf', '.rmvb', '.swf', '.divx'
]

def get_video_files(directory):
    """高效获取视频文件"""
    video_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                video_files.append(os.path.join(root, file))
    return video_files

def analyze_video(video_path):
    """详细视频分析并实时显示步骤"""
    error_type = 0
    step_log = []
    
    try:
        # 步骤1：尝试打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            error_type = 1
            step_log.append("打开：失败")
            return error_type, step_log
        
        step_log.append("打开：成功")
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames <= 0:
            error_type = 2
            step_log.append("获取总帧数失败")
            cap.release()
            return error_type, step_log
        
        # 计算检测点（20%间隔）
        check_points = [int(total_frames * (i/20)) for i in range(0, 20)]
        check_points = list(set(check_points))  # 去重
        check_points.sort()
        
        # 处理每个检测点
        for i, point in enumerate(check_points):
            # 实时显示当前步骤
            print(f"\r正在处理: {os.path.basename(video_path)} - 检测点 {i+1}/{len(check_points)} | 已发现损坏: {error_type != 0}", end='')
            
            # 确定帧范围（首尾特殊处理）
            if point == 0:  # 首帧
                frames_to_check = range(0, min(5, total_frames))
            elif point == total_frames - 1:  # 尾帧
                frames_to_check = range(max(0, total_frames-5), total_frames)
            else:  # 中间帧
                frames_to_check = range(max(0, point-2), min(point+3, total_frames))
            
            # 检查帧范围
            success = False
            for frame_idx in frames_to_check:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                step = f"[第{i+1}次]尝试抓取第{frame_idx}帧"
                if ret and frame is not None and frame.size > 0:
                    step_log.append(f"{step}：成功")
                    success = True
                    break
                else:
                    step_log.append(f"{step}：失败")
            
            if not success:
                error_type = 2
                step_log.append(f"检测点{point}周围5帧全部失败")
                cap.release()
                return error_type, step_log
    
    except Exception as e:
        error_type = 2
        step_log.append(f"异常捕获：{str(e)}")
    finally:
        cap.release()
    
    return error_type, step_log

def save_progress(progress_file, processed_files):
    """保存进度到隐藏文件"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        for path in processed_files:
            f.write(f"{path}\n")

def load_progress(progress_file):
    """从进度文件加载"""
    processed_files = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            processed_files = set(line.strip() for line in f)
    return processed_files

def main():
    parser = argparse.ArgumentParser(description='专业视频检测工具')
    parser.add_argument('directory', type=str, help='要检查的目录路径')
    parser.add_argument('--output', type=str, default='video_report', help='输出文件前缀')
    parser.add_argument('--resume', action='store_true', help='从上次中断处继续')
    args = parser.parse_args()
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{args.output}_{timestamp}.txt"
    progress_file = f".{args.output}_progress_{timestamp}.txt"
    
    # 加载进度
    processed_files = load_progress(progress_file)
    video_files = get_video_files(args.directory)
    
    # 过滤已处理的文件
    if args.resume:
        video_files = [f for f in video_files if f not in processed_files]
        print(f"跳过 {len(processed_files)} 个已处理文件，剩余 {len(video_files)} 个待检查")
    
    # 初始化统计
    total_files = len(video_files)
    processed_count = 0
    corrupted_count = 0
    
    print(f"开始处理 {total_files} 个视频文件...\n")
    
    for video_path in video_files:
        processed_count += 1
        processed_files.add(video_path)
        save_progress(progress_file, processed_files)
        
        # 显示当前视频信息
        print(f"\n正在处理: {os.path.basename(video_path)}")
        print(f"总进度: {processed_count}/{total_files} ({processed_count/total_files*100:.1f}%)")
        print(f"已发现损坏文件: {corrupted_count}")
        
        # 详细分析并实时显示步骤
        error_type, step_log = analyze_video(video_path)
        
        # 显示处理步骤
        print("\n处理步骤:")
        for step in step_log:
            print(step)
        
        # 记录损坏文件
        if error_type != 0:
            corrupted_count += 1
            error_desc = f"类型{error_type}错误"
            with open(log_filename, 'a', encoding='utf-8') as f:
                f.write(f"{video_path} | {error_desc}\n")
    
    # 完成处理
    if os.path.exists(progress_file):
        os.remove(progress_file)
    
    print(f"\n检测完成！共处理 {total_files} 个文件")
    print(f"发现损坏文件: {corrupted_count}")
    print(f"详细日志已保存至: {os.path.abspath(log_filename)}")

if __name__ == "__main__":
    main()
