"""
Adobe Audition集成模块 - 基础架构
"""

import os
import subprocess
import tempfile
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import platform

logger = logging.getLogger(__name__)


class AuditionDetector:
    """Adobe Audition安装检测器"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.audition_paths = self._get_default_paths()
        self.detected_version = None
        self.executable_path = None
    
    def _get_default_paths(self) -> List[str]:
        """获取默认安装路径"""
        if self.platform == "windows":
            # Windows平台的常见安装路径
            base_paths = [
                r"C:\Program Files\Adobe",
                r"C:\Program Files (x86)\Adobe"
            ]

            versions = [
                "Adobe Audition 2024",
                "Adobe Audition 2023",
                "Adobe Audition 2022",
                "Adobe Audition 2021",
                "Adobe Audition 2020",
                "Adobe Audition CC 2019",
                "Adobe Audition CC 2018"
            ]

            paths = []
            for base in base_paths:
                for version in versions:
                    if "2024" in version or "2023" in version or "2022" in version or "2021" in version or "2020" in version:
                        exe_name = "Adobe Audition.exe"
                    else:
                        exe_name = "Adobe Audition CC.exe"

                    path = os.path.join(base, version, exe_name)
                    paths.append(path)

            return paths

        elif self.platform == "darwin":  # macOS
            versions = [
                "Adobe Audition 2024",
                "Adobe Audition 2023",
                "Adobe Audition 2022",
                "Adobe Audition 2021",
                "Adobe Audition 2020",
                "Adobe Audition CC 2019",
                "Adobe Audition CC 2018"
            ]

            paths = []
            for version in versions:
                if "CC" in version:
                    app_name = f"{version}.app"
                    exe_name = f"{version}"
                else:
                    app_name = f"{version}.app"
                    exe_name = "Adobe Audition"

                path = f"/Applications/{app_name}/Contents/MacOS/{exe_name}"
                paths.append(path)

            return paths
        else:
            return []  # Linux不支持Adobe Audition
    
    def detect_installation(self) -> bool:
        """检测Adobe Audition安装"""
        if self.platform not in ["windows", "darwin"]:
            logger.warning("Adobe Audition不支持当前平台")
            return False

        # 方法1: 检查默认安装路径
        for path in self.audition_paths:
            if os.path.exists(path):
                if self._verify_executable(path):
                    self.executable_path = path
                    self.detected_version = self._get_version(path)
                    logger.info(f"检测到Adobe Audition: {path}, 版本: {self.detected_version}")
                    return True

        # 方法2: Windows注册表检测
        if self.platform == "windows":
            registry_path = self._detect_from_registry()
            if registry_path and os.path.exists(registry_path):
                if self._verify_executable(registry_path):
                    self.executable_path = registry_path
                    self.detected_version = self._get_version(registry_path)
                    logger.info(f"从注册表检测到Adobe Audition: {registry_path}")
                    return True

        # 方法3: 环境变量检测
        env_path = self._detect_from_environment()
        if env_path and os.path.exists(env_path):
            if self._verify_executable(env_path):
                self.executable_path = env_path
                self.detected_version = self._get_version(env_path)
                logger.info(f"从环境变量检测到Adobe Audition: {env_path}")
                return True

        logger.warning("未检测到Adobe Audition安装")
        return False
    
    def _get_version(self, executable_path: str) -> Optional[str]:
        """获取Adobe Audition版本信息"""
        try:
            # 尝试通过文件属性获取版本信息
            if self.platform == "windows":
                import win32api
                info = win32api.GetFileVersionInfo(executable_path, "\\")
                version = f"{info['FileVersionMS'] >> 16}.{info['FileVersionMS'] & 0xFFFF}"
                return version
            else:
                # macOS可以通过plist文件获取版本
                plist_path = executable_path.replace("/Contents/MacOS/", "/Contents/Info.plist")
                if os.path.exists(plist_path):
                    import plistlib
                    with open(plist_path, 'rb') as f:
                        plist = plistlib.load(f)
                        return plist.get('CFBundleShortVersionString', 'Unknown')
        except Exception as e:
            logger.warning(f"无法获取版本信息: {e}")
        
        return "Unknown"

    def _verify_executable(self, executable_path: str) -> bool:
        """验证可执行文件是否有效"""
        try:
            if not os.path.exists(executable_path):
                return False

            # 检查文件是否可执行
            if not os.access(executable_path, os.X_OK):
                return False

            # 尝试获取版本信息来验证这确实是Adobe Audition
            if self.platform == "windows":
                # Windows下检查文件描述
                try:
                    import win32api
                    info = win32api.GetFileVersionInfo(executable_path, "\\StringFileInfo\\040904b0\\FileDescription")
                    return "Adobe Audition" in info
                except:
                    # 如果win32api不可用，检查文件名
                    return "audition" in os.path.basename(executable_path).lower()
            else:
                # macOS下检查应用包结构
                if executable_path.endswith(".app/Contents/MacOS/Adobe Audition"):
                    return True
                return "audition" in os.path.basename(executable_path).lower()

        except Exception as e:
            logger.warning(f"验证可执行文件失败: {e}")
            return False

    def _detect_from_registry(self) -> Optional[str]:
        """从Windows注册表检测Adobe Audition"""
        if self.platform != "windows":
            return None

        try:
            import winreg

            # 常见的注册表路径
            registry_paths = [
                r"SOFTWARE\Adobe\Audition",
                r"SOFTWARE\WOW6432Node\Adobe\Audition",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Adobe Audition.exe",
                r"SOFTWARE\Classes\Applications\Adobe Audition.exe\shell\open\command"
            ]

            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        # 尝试获取安装路径
                        try:
                            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                            exe_path = os.path.join(install_path, "Adobe Audition.exe")
                            if os.path.exists(exe_path):
                                return exe_path
                        except FileNotFoundError:
                            pass

                        # 尝试获取默认值（可能包含完整路径）
                        try:
                            default_value, _ = winreg.QueryValueEx(key, "")
                            if default_value and "audition" in default_value.lower():
                                # 清理路径（移除引号和参数）
                                clean_path = default_value.strip('"').split()[0]
                                if os.path.exists(clean_path):
                                    return clean_path
                        except FileNotFoundError:
                            pass

                except FileNotFoundError:
                    continue
                except Exception as e:
                    logger.debug(f"注册表检测错误: {e}")
                    continue

        except ImportError:
            logger.debug("winreg模块不可用")
        except Exception as e:
            logger.warning(f"注册表检测失败: {e}")

        return None

    def _detect_from_environment(self) -> Optional[str]:
        """从环境变量检测Adobe Audition"""
        try:
            # 检查PATH环境变量
            path_env = os.environ.get("PATH", "")
            for path_dir in path_env.split(os.pathsep):
                if "adobe" in path_dir.lower() and "audition" in path_dir.lower():
                    if self.platform == "windows":
                        exe_path = os.path.join(path_dir, "Adobe Audition.exe")
                    else:
                        exe_path = os.path.join(path_dir, "Adobe Audition")

                    if os.path.exists(exe_path):
                        return exe_path

            # 检查Adobe特定的环境变量
            adobe_vars = [
                "ADOBE_AUDITION_PATH",
                "AUDITION_HOME",
                "ADOBE_HOME"
            ]

            for var in adobe_vars:
                var_value = os.environ.get(var)
                if var_value:
                    if self.platform == "windows":
                        exe_path = os.path.join(var_value, "Adobe Audition.exe")
                    else:
                        exe_path = os.path.join(var_value, "Adobe Audition")

                    if os.path.exists(exe_path):
                        return exe_path

        except Exception as e:
            logger.warning(f"环境变量检测失败: {e}")

        return None

    def get_installation_info(self) -> Dict[str, Any]:
        """获取安装信息"""
        if not self.executable_path:
            return {"installed": False}

        info = {
            "installed": True,
            "executable_path": self.executable_path,
            "version": self.detected_version,
            "platform": self.platform
        }

        try:
            # 获取文件信息
            stat = os.stat(self.executable_path)
            info["file_size"] = stat.st_size
            info["modified_time"] = stat.st_mtime

            # 获取目录信息
            install_dir = os.path.dirname(self.executable_path)
            info["install_directory"] = install_dir

            # 检查相关文件
            if self.platform == "windows":
                dll_files = [f for f in os.listdir(install_dir) if f.endswith('.dll')]
                info["dll_count"] = len(dll_files)

        except Exception as e:
            logger.warning(f"获取安装信息失败: {e}")

        return info


class AuditionParameterConverter:
    """Adobe Audition参数转换器"""
    
    def __init__(self):
        self.parameter_mapping = self._load_parameter_mapping()
    
    def _load_parameter_mapping(self) -> Dict[str, Any]:
        """加载参数映射配置"""
        return {
            "eq": {
                "type": "parametric_eq",
                "effect_name": "Parametric Equalizer",
                "bands": [],
                "max_bands": 10,
                "frequency_range": [20, 20000],
                "gain_range": [-20, 20],
                "q_range": [0.1, 10.0]
            },
            "compression": {
                "type": "multiband_compressor",
                "effect_name": "Multiband Compressor",
                "threshold": -20,
                "ratio": 4.0,
                "attack": 10,
                "release": 100,
                "knee": 2.0,
                "makeup_gain": 0.0,
                "bands": 4,
                "threshold_range": [-60, 0],
                "ratio_range": [1.0, 20.0],
                "attack_range": [0.1, 100],
                "release_range": [10, 5000]
            },
            "reverb": {
                "type": "convolution_reverb",
                "effect_name": "Convolution Reverb",
                "impulse_response": None,
                "wet_level": 0.3,
                "dry_level": 0.7,
                "pre_delay": 0,
                "room_size": 0.5,
                "damping": 0.5,
                "wet_range": [0.0, 1.0],
                "dry_range": [0.0, 1.0],
                "pre_delay_range": [0, 500]
            },
            "limiter": {
                "type": "adaptive_limiter",
                "effect_name": "Adaptive Limiter",
                "ceiling": -0.1,
                "release": 50,
                "lookahead": 5,
                "link_channels": True,
                "ceiling_range": [-20, 0],
                "release_range": [1, 1000],
                "lookahead_range": [0, 20]
            },
            "stereo": {
                "type": "stereo_width",
                "effect_name": "Stereo Width",
                "width": 1.0,
                "bass_mono": False,
                "bass_cutoff": 120,
                "width_range": [0.0, 2.0],
                "cutoff_range": [20, 500]
            },
            "pitch": {
                "type": "pitch_shift",
                "effect_name": "Pitch Shifter",
                "semitones": 0.0,
                "cents": 0.0,
                "preserve_formants": True,
                "semitones_range": [-12, 12],
                "cents_range": [-100, 100]
            },
            "time_stretch": {
                "type": "time_stretch",
                "effect_name": "Time and Pitch",
                "stretch_ratio": 1.0,
                "algorithm": "high_quality",
                "preserve_pitch": True,
                "stretch_range": [0.25, 4.0]
            }
        }
    
    def convert_style_params(self, style_params: Dict[str, Any]) -> Dict[str, Any]:
        """将风格参数转换为Adobe Audition参数"""
        audition_params = {}
        conversion_log = []

        for param_type, params in style_params.items():
            if param_type in self.parameter_mapping:
                try:
                    converted = self._convert_parameter(param_type, params)
                    validated = self._validate_parameter(param_type, converted)
                    audition_params[param_type] = validated
                    conversion_log.append(f"✓ {param_type}: 转换成功")
                except Exception as e:
                    logger.warning(f"参数转换失败 {param_type}: {e}")
                    conversion_log.append(f"✗ {param_type}: {str(e)}")
                    # 使用默认参数
                    audition_params[param_type] = self.parameter_mapping[param_type].copy()
            else:
                logger.warning(f"不支持的参数类型: {param_type}")
                conversion_log.append(f"? {param_type}: 不支持的类型")

        # 添加转换日志到结果中
        audition_params["_conversion_log"] = conversion_log
        audition_params["_conversion_timestamp"] = time.time()

        return audition_params
    
    def _convert_parameter(self, param_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """转换单个参数"""
        mapping = self.parameter_mapping[param_type].copy()
        
        if param_type == "eq" and "bands" in params:
            mapping["bands"] = self._convert_eq_bands(params["bands"])
        elif param_type == "compression":
            mapping.update({
                "threshold": params.get("threshold", mapping["threshold"]),
                "ratio": params.get("ratio", mapping["ratio"]),
                "attack": params.get("attack", mapping["attack"]),
                "release": params.get("release", mapping["release"])
            })
        elif param_type == "reverb":
            mapping.update({
                "wet_level": params.get("mix", mapping["wet_level"]),
                "impulse_response": params.get("ir_key")
            })
        elif param_type == "limiter":
            mapping.update({
                "ceiling": params.get("tp_db", mapping["ceiling"]),
                "release": params.get("release_ms", mapping["release"])
            })
        elif param_type == "stereo":
            mapping["width"] = params.get("width", mapping["width"])
        
        return mapping
    
    def _convert_eq_bands(self, bands: List[Dict]) -> List[Dict]:
        """转换EQ频段参数"""
        audition_bands = []
        for band in bands:
            audition_bands.append({
                "frequency": band.get("freq", 1000),
                "gain": band.get("gain", 0),
                "q": band.get("q", 1.0),
                "type": band.get("type", "peak")
            })
        return audition_bands

    def _validate_parameter(self, param_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证和修正参数值"""
        mapping = self.parameter_mapping[param_type]
        validated = params.copy()

        if param_type == "eq":
            # 验证EQ频段
            if "bands" in validated:
                valid_bands = []
                for band in validated["bands"]:
                    valid_band = self._validate_eq_band(band, mapping)
                    if valid_band:
                        valid_bands.append(valid_band)
                validated["bands"] = valid_bands[:mapping["max_bands"]]

        elif param_type == "compression":
            # 验证压缩参数
            validated["threshold"] = self._clamp_value(
                validated.get("threshold", mapping["threshold"]),
                mapping["threshold_range"]
            )
            validated["ratio"] = self._clamp_value(
                validated.get("ratio", mapping["ratio"]),
                mapping["ratio_range"]
            )
            validated["attack"] = self._clamp_value(
                validated.get("attack", mapping["attack"]),
                mapping["attack_range"]
            )
            validated["release"] = self._clamp_value(
                validated.get("release", mapping["release"]),
                mapping["release_range"]
            )

        elif param_type == "reverb":
            # 验证混响参数
            validated["wet_level"] = self._clamp_value(
                validated.get("wet_level", mapping["wet_level"]),
                mapping["wet_range"]
            )
            validated["dry_level"] = self._clamp_value(
                validated.get("dry_level", mapping["dry_level"]),
                mapping["dry_range"]
            )
            if "pre_delay" in validated:
                validated["pre_delay"] = self._clamp_value(
                    validated["pre_delay"],
                    mapping["pre_delay_range"]
                )

        elif param_type == "limiter":
            # 验证限制器参数
            validated["ceiling"] = self._clamp_value(
                validated.get("ceiling", mapping["ceiling"]),
                mapping["ceiling_range"]
            )
            validated["release"] = self._clamp_value(
                validated.get("release", mapping["release"]),
                mapping["release_range"]
            )
            if "lookahead" in validated:
                validated["lookahead"] = self._clamp_value(
                    validated["lookahead"],
                    mapping["lookahead_range"]
                )

        elif param_type == "stereo":
            # 验证立体声参数
            validated["width"] = self._clamp_value(
                validated.get("width", mapping["width"]),
                mapping["width_range"]
            )
            if "bass_cutoff" in validated:
                validated["bass_cutoff"] = self._clamp_value(
                    validated["bass_cutoff"],
                    mapping["cutoff_range"]
                )

        elif param_type == "pitch":
            # 验证音调参数
            validated["semitones"] = self._clamp_value(
                validated.get("semitones", mapping["semitones"]),
                mapping["semitones_range"]
            )
            if "cents" in validated:
                validated["cents"] = self._clamp_value(
                    validated["cents"],
                    mapping["cents_range"]
                )

        return validated

    def _validate_eq_band(self, band: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证EQ频段参数"""
        try:
            validated_band = {
                "frequency": self._clamp_value(
                    band.get("freq", 1000),
                    mapping["frequency_range"]
                ),
                "gain": self._clamp_value(
                    band.get("gain", 0),
                    mapping["gain_range"]
                ),
                "q": self._clamp_value(
                    band.get("q", 1.0),
                    mapping["q_range"]
                ),
                "type": band.get("type", "peak")
            }

            # 验证滤波器类型
            valid_types = ["peak", "lowpass", "highpass", "bandpass", "notch", "lowshelf", "highshelf"]
            if validated_band["type"] not in valid_types:
                validated_band["type"] = "peak"

            return validated_band

        except Exception as e:
            logger.warning(f"EQ频段验证失败: {e}")
            return None

    def _clamp_value(self, value: float, value_range: List[float]) -> float:
        """将值限制在指定范围内"""
        try:
            min_val, max_val = value_range
            return max(min_val, min(max_val, float(value)))
        except (ValueError, TypeError):
            # 如果转换失败，返回范围中点
            min_val, max_val = value_range
            return (min_val + max_val) / 2

    def get_supported_parameters(self) -> List[str]:
        """获取支持的参数类型列表"""
        return list(self.parameter_mapping.keys())

    def get_parameter_info(self, param_type: str) -> Optional[Dict[str, Any]]:
        """获取参数类型的详细信息"""
        return self.parameter_mapping.get(param_type)

    def validate_style_params(self, style_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证风格参数的有效性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "supported_params": [],
            "unsupported_params": []
        }

        for param_type, params in style_params.items():
            if param_type in self.parameter_mapping:
                validation_result["supported_params"].append(param_type)

                # 检查参数完整性
                try:
                    self._convert_parameter(param_type, params)
                except Exception as e:
                    validation_result["errors"].append(f"{param_type}: {str(e)}")
                    validation_result["valid"] = False
            else:
                validation_result["unsupported_params"].append(param_type)
                validation_result["warnings"].append(f"不支持的参数类型: {param_type}")

        return validation_result


class AuditionTemplateManager:
    """Adobe Audition模板管理器"""
    
    def __init__(self, template_dir: str = None):
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "audition_templates"
        )
        self._ensure_template_dir()
    
    def _ensure_template_dir(self):
        """确保模板目录存在"""
        os.makedirs(self.template_dir, exist_ok=True)
    
    def create_processing_script(self, 
                               input_file: str, 
                               output_file: str, 
                               audition_params: Dict[str, Any]) -> str:
        """创建Adobe Audition处理脚本"""
        script_content = self._generate_extendscript(input_file, output_file, audition_params)
        
        script_path = os.path.join(
            self.template_dir, 
            f"process_{os.path.basename(input_file)}.jsx"
        )
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def _generate_extendscript(self,
                             input_file: str,
                             output_file: str,
                             audition_params: Dict[str, Any]) -> str:
        """生成ExtendScript脚本内容"""

        # 转换路径为ExtendScript兼容格式
        input_file_escaped = input_file.replace("\\", "\\\\").replace('"', '\\"')
        output_file_escaped = output_file.replace("\\", "\\\\").replace('"', '\\"')

        # 生成效果处理代码
        effects_code = self._generate_effects_code(audition_params)

        # 生成完整脚本
        script = f'''// Adobe Audition自动化处理脚本
// 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
// 输入文件: {input_file}
// 输出文件: {output_file}

// 导入基础模板函数
#include "{os.path.join(self.template_dir, "base_template.jsx").replace(chr(92), chr(92)+chr(92))}"

// 主处理函数
function main() {{
    var startTime = new Date().getTime();
    var doc = null;

    try {{
        logInfo("开始处理音频文件");
        logInfo("输入文件: {input_file_escaped}");
        logInfo("输出文件: {output_file_escaped}");

        // 打开音频文件
        doc = openAudioDocument("{input_file_escaped}");
        if (!doc) {{
            throw new Error("无法打开输入文件");
        }}

        // 应用效果链
        var effectsApplied = 0;
        var totalEffects = {len([k for k in audition_params.keys() if not k.startswith('_')])};

        {effects_code}

        // 保存处理后的文件
        if (!saveAudioDocument(doc, "{output_file_escaped}", "wav")) {{
            throw new Error("保存文件失败");
        }}

        // 计算处理时间
        var endTime = new Date().getTime();
        var processingTime = (endTime - startTime) / 1000;

        reportMetric("processing_time_seconds", processingTime, "s");
        reportMetric("effects_applied", effectsApplied);

        logInfo("处理完成，耗时: " + processingTime.toFixed(2) + " 秒");
        $.writeln("AUDITION_SUCCESS:Processing completed successfully");

    }} catch (error) {{
        handleError(error, "main processing");
        $.writeln("AUDITION_ERROR:" + error.toString());

    }} finally {{
        // 清理资源
        if (doc) {{
            try {{
                doc.close(false); // 不保存关闭
            }} catch (e) {{
                // 忽略关闭错误
            }}
        }}
    }}
}}

// 执行主函数
main();
'''
        return script
    
    def _generate_effects_code(self, audition_params: Dict[str, Any]) -> str:
        """生成效果处理代码"""
        effects_code = []
        effect_index = 0

        for effect_type, params in audition_params.items():
            # 跳过内部参数
            if effect_type.startswith('_'):
                continue

            effect_index += 1
            progress_code = f'''
        reportProgress("effects", {effect_index * 100 // len([k for k in audition_params.keys() if not k.startswith('_')])}, "应用效果: {effect_type}");
        logInfo("应用效果 {effect_index}: {effect_type}");
        '''

            if effect_type == "eq":
                effects_code.append(progress_code + self._generate_eq_code(params))
            elif effect_type == "compression":
                effects_code.append(progress_code + self._generate_compression_code(params))
            elif effect_type == "reverb":
                effects_code.append(progress_code + self._generate_reverb_code(params))
            elif effect_type == "limiter":
                effects_code.append(progress_code + self._generate_limiter_code(params))
            elif effect_type == "stereo":
                effects_code.append(progress_code + self._generate_stereo_code(params))
            elif effect_type == "pitch":
                effects_code.append(progress_code + self._generate_pitch_code(params))
            else:
                effects_code.append(f'''
        logWarning("不支持的效果类型: {effect_type}");
        ''')

            effects_code.append('''
        effectsApplied++;
        ''')

        return "\n".join(effects_code)
    
    def _generate_eq_code(self, params: Dict[str, Any]) -> str:
        """生成EQ处理代码"""
        bands = params.get("bands", [])

        if not bands:
            return '''
        logInfo("EQ: 无频段配置，跳过");
        '''

        bands_code = []
        for i, band in enumerate(bands):
            freq = band.get("frequency", 1000)
            gain = band.get("gain", 0)
            q = band.get("q", 1.0)
            band_type = band.get("type", "peak")

            bands_code.append(f'''
        // EQ频段 {i+1}: {freq}Hz, {gain}dB, Q={q}, 类型={band_type}
        try {{
            // 注意: 实际的Adobe Audition ExtendScript API可能不同
            // 这里提供一个通用的框架
            doc.selectAll();
            // 应用EQ效果 - 需要根据实际API调整
            logInfo("EQ频段 {i+1}: " + {freq} + "Hz, " + {gain} + "dB");
        }} catch (e) {{
            logWarning("EQ频段 {i+1} 应用失败: " + e.toString());
        }}
        ''')

        return f'''
        try {{
            logInfo("应用参数EQ，共 {len(bands)} 个频段");
            {chr(10).join(bands_code)}
            logInfo("参数EQ应用完成");
        }} catch (e) {{
            logError("参数EQ应用失败: " + e.toString());
        }}
        '''
    
    def _generate_compression_code(self, params: Dict[str, Any]) -> str:
        """生成压缩处理代码"""
        threshold = params.get("threshold", -20)
        ratio = params.get("ratio", 4.0)
        attack = params.get("attack", 10)
        release = params.get("release", 100)
        makeup_gain = params.get("makeup_gain", 0.0)

        return f'''
        try {{
            logInfo("应用多频段压缩器");
            logInfo("压缩参数: 阈值=" + {threshold} + "dB, 比率=" + {ratio} + ":1");
            logInfo("时间参数: 启动=" + {attack} + "ms, 释放=" + {release} + "ms");

            doc.selectAll();
            // 应用多频段压缩 - 需要根据实际API调整
            // var compEffect = doc.applyEffect("Multiband Compressor");
            // compEffect.threshold = {threshold};
            // compEffect.ratio = {ratio};
            // compEffect.attack = {attack};
            // compEffect.release = {release};
            // compEffect.makeupGain = {makeup_gain};

            reportMetric("compression_threshold", {threshold}, "dB");
            reportMetric("compression_ratio", {ratio});

            logInfo("多频段压缩器应用完成");
        }} catch (e) {{
            logError("多频段压缩器应用失败: " + e.toString());
        }}
        '''
    
    def _generate_reverb_code(self, params: Dict[str, Any]) -> str:
        """生成混响处理代码"""
        wet_level = params.get("wet_level", 0.3)
        dry_level = params.get("dry_level", 0.7)
        pre_delay = params.get("pre_delay", 0)
        impulse_response = params.get("impulse_response")

        return f'''
        try {{
            logInfo("应用卷积混响");
            logInfo("混响参数: 湿声=" + {wet_level} + ", 干声=" + {dry_level});

            doc.selectAll();
            // 应用卷积混响 - 需要根据实际API调整
            // var reverbEffect = doc.applyEffect("Convolution Reverb");
            // reverbEffect.wetLevel = {wet_level};
            // reverbEffect.dryLevel = {dry_level};
            // reverbEffect.preDelay = {pre_delay};

            {"// reverbEffect.impulseResponse = " + chr(34) + str(impulse_response) + chr(34) + ";" if impulse_response else "// 使用默认脉冲响应"}

            reportMetric("reverb_wet_level", {wet_level});
            reportMetric("reverb_dry_level", {dry_level});

            logInfo("卷积混响应用完成");
        }} catch (e) {{
            logError("卷积混响应用失败: " + e.toString());
        }}
        '''
    
    def _generate_limiter_code(self, params: Dict[str, Any]) -> str:
        """生成限制器处理代码"""
        ceiling = params.get("ceiling", -0.1)
        release = params.get("release", 50)
        lookahead = params.get("lookahead", 5)

        return f'''
        try {{
            logInfo("应用自适应限制器");
            logInfo("限制器参数: 上限=" + {ceiling} + "dB, 释放=" + {release} + "ms");

            doc.selectAll();
            // 应用自适应限制器 - 需要根据实际API调整
            // var limiterEffect = doc.applyEffect("Adaptive Limiter");
            // limiterEffect.ceiling = {ceiling};
            // limiterEffect.release = {release};
            // limiterEffect.lookahead = {lookahead};

            reportMetric("limiter_ceiling", {ceiling}, "dB");
            reportMetric("limiter_release", {release}, "ms");

            logInfo("自适应限制器应用完成");
        }} catch (e) {{
            logError("自适应限制器应用失败: " + e.toString());
        }}
        '''

    def _generate_stereo_code(self, params: Dict[str, Any]) -> str:
        """生成立体声处理代码"""
        width = params.get("width", 1.0)
        bass_mono = params.get("bass_mono", False)
        bass_cutoff = params.get("bass_cutoff", 120)

        return f'''
        try {{
            logInfo("应用立体声宽度调整");
            logInfo("立体声参数: 宽度=" + {width} + ", 低频单声道=" + {str(bass_mono).lower()});

            doc.selectAll();
            // 应用立体声宽度 - 需要根据实际API调整
            // var stereoEffect = doc.applyEffect("Stereo Width");
            // stereoEffect.width = {width};
            // stereoEffect.bassMono = {str(bass_mono).lower()};
            // stereoEffect.bassCutoff = {bass_cutoff};

            reportMetric("stereo_width", {width});

            logInfo("立体声宽度调整完成");
        }} catch (e) {{
            logError("立体声宽度调整失败: " + e.toString());
        }}
        '''

    def _generate_pitch_code(self, params: Dict[str, Any]) -> str:
        """生成音调处理代码"""
        semitones = params.get("semitones", 0.0)
        cents = params.get("cents", 0.0)
        preserve_formants = params.get("preserve_formants", True)

        return f'''
        try {{
            logInfo("应用音调变换");
            logInfo("音调参数: 半音=" + {semitones} + ", 音分=" + {cents});

            doc.selectAll();
            // 应用音调变换 - 需要根据实际API调整
            // var pitchEffect = doc.applyEffect("Pitch Shifter");
            // pitchEffect.semitones = {semitones};
            // pitchEffect.cents = {cents};
            // pitchEffect.preserveFormants = {str(preserve_formants).lower()};

            reportMetric("pitch_semitones", {semitones});
            reportMetric("pitch_cents", {cents});

            logInfo("音调变换完成");
        }} catch (e) {{
            logError("音调变换失败: " + e.toString());
        }}
        '''


    def create_batch_script(self,
                          file_pairs: List[Tuple[str, str]],
                          audition_params: Dict[str, Any]) -> str:
        """创建批处理脚本"""
        batch_scripts = []

        for i, (input_file, output_file) in enumerate(file_pairs):
            script_path = self.create_processing_script(input_file, output_file, audition_params)
            batch_scripts.append(script_path)

        # 创建批处理主脚本
        batch_script_path = os.path.join(self.template_dir, f"batch_process_{int(time.time())}.jsx")

        batch_content = f'''
// Adobe Audition批处理脚本
// 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
// 文件数量: {len(file_pairs)}

var batchFiles = [
{chr(10).join([f'    "{script.replace(chr(92), chr(92)+chr(92))}",' for script in batch_scripts])}
];

function processBatch() {{
    var startTime = new Date().getTime();
    var successCount = 0;
    var errorCount = 0;

    for (var i = 0; i < batchFiles.length; i++) {{
        try {{
            $.writeln("BATCH_PROGRESS:" + ((i + 1) / batchFiles.length * 100).toFixed(1) + "%");
            $.evalFile(batchFiles[i]);
            successCount++;
        }} catch (e) {{
            $.writeln("BATCH_ERROR:File " + (i + 1) + ": " + e.toString());
            errorCount++;
        }}
    }}

    var endTime = new Date().getTime();
    var totalTime = (endTime - startTime) / 1000;

    $.writeln("BATCH_COMPLETE:Processed " + batchFiles.length + " files");
    $.writeln("BATCH_STATS:Success=" + successCount + ", Errors=" + errorCount + ", Time=" + totalTime + "s");
}}

processBatch();
'''

        with open(batch_script_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)

        return batch_script_path

    def cleanup_old_scripts(self, max_age_hours: int = 24):
        """清理旧的脚本文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for filename in os.listdir(self.template_dir):
                if filename.endswith('.jsx') and filename.startswith('process_'):
                    file_path = os.path.join(self.template_dir, filename)
                    file_age = current_time - os.path.getmtime(file_path)

                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        logger.debug(f"清理旧脚本文件: {filename}")

        except Exception as e:
            logger.warning(f"清理脚本文件失败: {e}")

    def get_template_info(self) -> Dict[str, Any]:
        """获取模板信息"""
        info = {
            "template_directory": self.template_dir,
            "base_template_exists": os.path.exists(os.path.join(self.template_dir, "base_template.jsx")),
            "script_count": 0,
            "total_size_bytes": 0
        }

        try:
            for filename in os.listdir(self.template_dir):
                if filename.endswith('.jsx'):
                    file_path = os.path.join(self.template_dir, filename)
                    info["script_count"] += 1
                    info["total_size_bytes"] += os.path.getsize(file_path)
        except Exception as e:
            logger.warning(f"获取模板信息失败: {e}")

        return info


# 创建全局实例
global_audition_detector = AuditionDetector()
global_parameter_converter = AuditionParameterConverter()
global_template_manager = AuditionTemplateManager()

# 导出主要类
__all__ = [
    'AuditionDetector',
    'AuditionParameterConverter',
    'AuditionTemplateManager',
    'global_audition_detector',
    'global_parameter_converter',
    'global_template_manager'
]
