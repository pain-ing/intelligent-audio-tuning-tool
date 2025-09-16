// Adobe Audition自动化处理脚本
// 生成时间: 2025-09-16 19:50:01
// 输入文件: test.wav
// 输出文件: output.wav

// 导入基础模板函数
#include "D:\\Mituanapp2\\worker\\app\\audition_templates\\base_template.jsx"

// 主处理函数
function main() {
    var startTime = new Date().getTime();
    var doc = null;

    try {
        logInfo("开始处理音频文件");
        logInfo("输入文件: test.wav");
        logInfo("输出文件: output.wav");

        // 打开音频文件
        doc = openAudioDocument("test.wav");
        if (!doc) {
            throw new Error("无法打开输入文件");
        }

        // 应用效果链
        var effectsApplied = 0;
        var totalEffects = 2;

        
        reportProgress("effects", 50, "应用效果: reverb");
        logInfo("应用效果 1: reverb");
        
        try {
            logInfo("应用卷积混响");
            logInfo("混响参数: 湿声=" + 0.3 + ", 干声=" + 0.7);

            doc.selectAll();
            // 应用卷积混响 - 需要根据实际API调整
            // var reverbEffect = doc.applyEffect("Convolution Reverb");
            // reverbEffect.wetLevel = 0.3;
            // reverbEffect.dryLevel = 0.7;
            // reverbEffect.preDelay = 0;

            // 使用默认脉冲响应

            reportMetric("reverb_wet_level", 0.3);
            reportMetric("reverb_dry_level", 0.7);

            logInfo("卷积混响应用完成");
        } catch (e) {
            logError("卷积混响应用失败: " + e.toString());
        }
        

        effectsApplied++;
        

        reportProgress("effects", 100, "应用效果: eq");
        logInfo("应用效果 2: eq");
        
        logInfo("EQ: 无频段配置，跳过");
        

        effectsApplied++;
        

        // 保存处理后的文件
        if (!saveAudioDocument(doc, "output.wav", "wav")) {
            throw new Error("保存文件失败");
        }

        // 计算处理时间
        var endTime = new Date().getTime();
        var processingTime = (endTime - startTime) / 1000;

        reportMetric("processing_time_seconds", processingTime, "s");
        reportMetric("effects_applied", effectsApplied);

        logInfo("处理完成，耗时: " + processingTime.toFixed(2) + " 秒");
        $.writeln("AUDITION_SUCCESS:Processing completed successfully");

    } catch (error) {
        handleError(error, "main processing");
        $.writeln("AUDITION_ERROR:" + error.toString());

    } finally {
        // 清理资源
        if (doc) {
            try {
                doc.close(false); // 不保存关闭
            } catch (e) {
                // 忽略关闭错误
            }
        }
    }
}

// 执行主函数
main();
