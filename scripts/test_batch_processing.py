#!/usr/bin/env python3
"""
批处理功能测试脚本
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_audio_files(count: int = 5) -> list:
    """创建测试音频文件"""
    test_files = []
    temp_dir = tempfile.mkdtemp(prefix="batch_test_")
    
    print(f"📁 创建测试目录: {temp_dir}")
    
    for i in range(count):
        # 创建简单的测试文件（模拟音频文件）
        test_file = os.path.join(temp_dir, f"test_audio_{i+1}.wav")
        with open(test_file, 'wb') as f:
            # 写入一些测试数据（模拟音频数据）
            f.write(b"RIFF" + b"\x00" * 44 + b"test_audio_data" * 100)
        
        test_files.append(test_file)
    
    print(f"✅ 创建了 {count} 个测试音频文件")
    return test_files, temp_dir


def test_batch_models():
    """测试批处理数据模型"""
    print("🧪 测试批处理数据模型")
    print("-" * 40)
    
    try:
        from worker.app.batch_models import (
            BatchTask, AudioProcessingParams, TaskStatus, 
            BatchProgress, BatchResult, BatchConfiguration
        )
        
        # 测试音频处理参数
        params = AudioProcessingParams(
            style_params={"reverb": 0.3, "echo": 0.2},
            output_format="wav",
            use_audition=True
        )
        print("✅ 音频处理参数创建成功")
        
        # 测试批处理任务
        task = BatchTask(
            input_path="/test/input.wav",
            output_path="/test/output.wav",
            processing_params=params
        )
        print(f"✅ 批处理任务创建成功: {task.task_id}")
        
        # 测试任务状态变更
        task.start_processing()
        assert task.status == TaskStatus.PROCESSING
        print("✅ 任务状态变更测试通过")
        
        # 测试任务完成
        task.complete_successfully(processing_time=1.5, output_size=1024*1024)
        assert task.status == TaskStatus.COMPLETED
        assert task.processing_time == 1.5
        print("✅ 任务完成测试通过")
        
        # 测试批处理进度
        progress = BatchProgress(batch_id="test_batch", total_tasks=10)
        progress.update_progress(5, 1, 0, 2.0)
        assert progress.progress_percentage == 60.0
        print("✅ 批处理进度测试通过")
        
        # 测试配置
        config = BatchConfiguration(max_concurrent_tasks=8)
        assert config.max_concurrent_tasks == 8
        print("✅ 批处理配置测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 批处理数据模型测试失败: {e}")
        return False


def test_progress_tracker():
    """测试进度跟踪器"""
    print("\n📊 测试进度跟踪器")
    print("-" * 40)
    
    try:
        from worker.app.batch_progress import ProgressTracker, global_progress_manager
        from worker.app.batch_models import BatchTask, TaskStatus, AudioProcessingParams
        
        # 创建进度跟踪器
        tracker = ProgressTracker("test_batch_001", 3)
        print("✅ 进度跟踪器创建成功")
        
        # 创建测试任务
        tasks = []
        for i in range(3):
            task = BatchTask(
                input_path=f"/test/input_{i}.wav",
                output_path=f"/test/output_{i}.wav",
                processing_params=AudioProcessingParams()
            )
            tasks.append(task)
            tracker.add_task(task)
        
        print("✅ 任务添加到跟踪器成功")
        
        # 模拟任务处理
        tracker.update_task_status(tasks[0].task_id, TaskStatus.PROCESSING)
        tracker.update_task_status(tasks[0].task_id, TaskStatus.COMPLETED, processing_time=1.2)
        
        tracker.update_task_status(tasks[1].task_id, TaskStatus.PROCESSING)
        tracker.update_task_status(tasks[1].task_id, TaskStatus.FAILED, error_message="测试错误")
        
        tracker.update_task_status(tasks[2].task_id, TaskStatus.PROCESSING)
        tracker.update_task_status(tasks[2].task_id, TaskStatus.COMPLETED, processing_time=0.8)
        
        # 检查进度
        progress = tracker.get_progress()
        assert progress.completed_tasks == 2
        assert progress.failed_tasks == 1
        assert progress.progress_percentage == 100.0
        
        print(f"✅ 进度跟踪测试通过: 完成 {progress.completed_tasks}, 失败 {progress.failed_tasks}")
        
        # 测试统计信息
        stats = tracker.get_task_statistics()
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        print("✅ 统计信息测试通过")
        
        # 测试全局管理器
        global_tracker = global_progress_manager.create_tracker("global_test", 5)
        assert global_progress_manager.get_tracker("global_test") is not None
        print("✅ 全局进度管理器测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 进度跟踪器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processor():
    """测试批处理管理器"""
    print("\n⚙️ 测试批处理管理器")
    print("-" * 40)
    
    try:
        from worker.app.batch_processor import BatchProcessor
        from worker.app.batch_models import BatchTask, AudioProcessingParams, BatchConfiguration
        
        # 创建测试文件
        test_files, temp_dir = create_test_audio_files(3)
        
        try:
            # 创建批处理管理器
            config = BatchConfiguration(max_concurrent_tasks=2)
            processor = BatchProcessor(config)
            print("✅ 批处理管理器创建成功")
            
            # 创建批处理任务
            tasks = []
            for i, input_file in enumerate(test_files):
                output_file = os.path.join(temp_dir, f"output_{i+1}.wav")
                task = BatchTask(
                    input_path=input_file,
                    output_path=output_file,
                    processing_params=AudioProcessingParams(
                        style_params={"test_param": i * 0.1}
                    )
                )
                tasks.append(task)
            
            # 提交批处理
            batch_id = processor.submit_batch(tasks)
            print(f"✅ 批处理提交成功: {batch_id}")
            
            # 开始批处理
            success = processor.start_batch(batch_id)
            assert success, "批处理启动失败"
            print("✅ 批处理启动成功")
            
            # 等待处理完成
            print("⏳ 等待批处理完成...")
            max_wait = 30  # 最多等待30秒
            wait_time = 0
            
            while wait_time < max_wait:
                status = processor.get_batch_status(batch_id)
                if status:
                    progress = status["progress"]
                    print(f"   进度: {progress['progress_percentage']:.1f}% "
                          f"(完成: {progress['completed_tasks']}, "
                          f"失败: {progress['failed_tasks']})")
                    
                    if progress["progress_percentage"] >= 100.0:
                        break
                
                time.sleep(1)
                wait_time += 1
            
            # 获取最终结果
            result = processor.get_batch_result(batch_id)
            if result:
                print(f"✅ 批处理完成: 成功率 {result.success_rate:.1f}%")
                print(f"   总任务: {result.total_tasks}")
                print(f"   完成: {result.completed_tasks}")
                print(f"   失败: {result.failed_tasks}")
            else:
                print("⚠️ 未获取到批处理结果")
            
            return True
            
        finally:
            # 清理测试文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 清理测试目录: {temp_dir}")
        
    except Exception as e:
        print(f"❌ 批处理管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_storage():
    """测试批处理存储"""
    print("\n💾 测试批处理存储")
    print("-" * 40)
    
    try:
        from worker.app.batch_storage import BatchStorage
        from worker.app.batch_models import BatchTask, BatchStatus, AudioProcessingParams
        
        # 创建临时存储
        temp_storage_dir = tempfile.mkdtemp(prefix="batch_storage_test_")
        
        try:
            storage = BatchStorage(temp_storage_dir)
            print("✅ 批处理存储创建成功")
            
            # 测试保存批处理
            batch_id = "test_batch_storage"
            storage.save_batch(batch_id, BatchStatus.CREATED, 2)
            print("✅ 批处理保存成功")
            
            # 测试保存任务
            task = BatchTask(
                input_path="/test/input.wav",
                output_path="/test/output.wav",
                processing_params=AudioProcessingParams()
            )
            storage.save_task(task, batch_id)
            print("✅ 任务保存成功")
            
            # 测试加载批处理
            loaded_batch = storage.load_batch(batch_id)
            assert loaded_batch is not None
            assert loaded_batch["batch_id"] == batch_id
            print("✅ 批处理加载成功")
            
            # 测试加载任务
            loaded_tasks = storage.load_batch_tasks(batch_id)
            assert len(loaded_tasks) == 1
            assert loaded_tasks[0]["task_id"] == task.task_id
            print("✅ 任务加载成功")
            
            # 测试获取批处理列表
            batch_list = storage.get_batch_list()
            assert len(batch_list) >= 1
            print("✅ 批处理列表获取成功")
            
            return True
            
        finally:
            # 清理临时存储
            shutil.rmtree(temp_storage_dir, ignore_errors=True)
            print(f"🧹 清理存储目录: {temp_storage_dir}")
        
    except Exception as e:
        print(f"❌ 批处理存储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """集成测试"""
    print("\n🔗 批处理集成测试")
    print("-" * 40)
    
    try:
        from worker.app.batch_processor import global_batch_processor
        from worker.app.batch_storage import global_batch_storage
        from worker.app.batch_models import BatchTask, AudioProcessingParams, BatchStatus
        
        # 创建测试文件
        test_files, temp_dir = create_test_audio_files(2)
        
        try:
            # 创建任务
            tasks = []
            for i, input_file in enumerate(test_files):
                output_file = os.path.join(temp_dir, f"integrated_output_{i+1}.wav")
                task = BatchTask(
                    input_path=input_file,
                    output_path=output_file,
                    processing_params=AudioProcessingParams()
                )
                tasks.append(task)
            
            # 提交并开始批处理
            batch_id = global_batch_processor.submit_batch(tasks)
            
            # 保存到存储
            global_batch_storage.save_batch(batch_id, BatchStatus.CREATED, len(tasks))
            for task in tasks:
                global_batch_storage.save_task(task, batch_id)
            
            print(f"✅ 集成测试批处理创建成功: {batch_id}")
            
            # 检查状态
            status = global_batch_processor.get_batch_status(batch_id)
            assert status is not None
            print("✅ 状态查询成功")
            
            # 检查存储
            stored_batch = global_batch_storage.load_batch(batch_id)
            assert stored_batch is not None
            print("✅ 存储查询成功")
            
            return True
            
        finally:
            # 清理测试文件
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 批处理功能测试")
    print("=" * 60)
    
    tests = [
        ("批处理数据模型", test_batch_models),
        ("进度跟踪器", test_progress_tracker),
        ("批处理管理器", test_batch_processor),
        ("批处理存储", test_batch_storage),
        ("集成测试", test_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    # 测试结果总结
    print("\n" + "=" * 60)
    print("📋 批处理功能测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 测试统计: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 批处理功能 - 所有测试通过！")
        print("✅ 批处理支持功能已准备就绪")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
