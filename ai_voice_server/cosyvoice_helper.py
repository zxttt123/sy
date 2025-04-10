import os
import sys
import torch
import logging
import argparse
from typing import List, Dict, Any, Optional, Union
import tempfile
import time
from pathlib import Path
import numpy as np
import soundfile as sf
from .utils.text_splitter import split_text, merge_sentences_into_chunks, merge_audio_files

# 添加CosyVoice路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COSYVOICE_PATH = os.path.join(os.path.dirname(ROOT_DIR), 'CosyVoice')
sys.path.append(os.path.join(COSYVOICE_PATH, 'third_party/Matcha-TTS'))

# 导入CosyVoice相关模块
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
from cosyvoice.utils.file_utils import load_wav
from cosyvoice.utils.common import set_all_random_seed

class CosyVoiceHelper:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CosyVoiceHelper, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_dir=None, lazy_load=False):
        if self._initialized:
            return
        
        # 允许懒加载模式，即只在第一次实际使用时加载模型
        self._lazy_load = lazy_load
        
        # 模型路径，如果未指定则使用默认值
        self.model_dir = model_dir or os.path.join(COSYVOICE_PATH, 'pretrained_models/CosyVoice2-0.5B')
        
        # 设置初始化标志
        self._initialized = True
        self.model = None
        self.model_type = None
        
        # 如果不是懒加载模式，立即初始化模型
        if not lazy_load:
            self._initialize_model()
    
    def _initialize_model(self):
        """实际初始化模型的方法"""
        if self.model is not None:
            # 模型已初始化，无需重复操作
            return
            
        try:
            logging.info(f"初始化CosyVoice2模型: {self.model_dir}")
            self.model = CosyVoice2(self.model_dir, load_jit=False, load_trt=False, fp16=False)
            self.model_type = "CosyVoice2"
        except Exception as e:
            logging.warning(f"初始化CosyVoice2失败: {e}，尝试使用CosyVoice")
            try:
                self.model = CosyVoice(self.model_dir, load_jit=False, load_trt=False, fp16=False)
                self.model_type = "CosyVoice"
            except Exception as e2:
                logging.error(f"初始化CosyVoice失败: {e2}")
                raise ValueError(f"无法初始化语音模型: {e2}")
        
        self.sample_rate = self.model.sample_rate
        logging.info(f"CosyVoiceHelper初始化完成，模型类型: {self.model_type}")
    
    @property
    def is_initialized(self):
        """检查模型是否已初始化"""
        return self.model is not None
    
    def _get_preset_voices(self) -> List[str]:
        """获取预置的声音列表 - 通过代码调用获取，而非硬编码"""
        if self.model is None:
            self._initialize_model()
            
        try:
            if self.model_type == "CosyVoice":
                return self.model.list_available_spks()
            elif self.model_type == "CosyVoice2":
                # 对于CosyVoice2，通过list_available_spks()方法获取预置声音
                try:
                    # 尝试通过与CosyVoice相同的方法获取
                    return self.model.list_available_spks()
                except (AttributeError, Exception) as e:
                    logging.warning(f"无法通过list_available_spks获取CosyVoice2预置声音: {e}")
                    # 如果无法获取，返回空列表，避免使用硬编码的预设列表
                    return []
        except Exception as e:
            logging.error(f"获取预置声音列表失败: {e}")
            return []
    
    def get_preset_voices(self) -> List[str]:
        """获取所有预置的声音列表"""
        if self.model is None:
            self._initialize_model()
            
        return self._get_preset_voices()
    
    def synthesize_speech(self, text: str, voice_id: str, is_preset: bool = False, 
                          prompt_audio: Optional[str] = None, prompt_text: Optional[str] = None) -> Any:
        """
        合成语音
        
        参数:
            text: 要合成的文本
            voice_id: 声音ID或预置声音名称
            is_preset: 是否使用预置声音
            prompt_audio: 提示音频文件路径
            prompt_text: 提示文本
            
        返回:
            合成的音频数据
        """
        # 确保模型已初始化
        if self.model is None:
            self._initialize_model()
            
        set_all_random_seed(42)  # 固定随机种子以获得稳定结果
        
        try:
            # 确保text不为空
            if not text or not text.strip():
                raise ValueError("合成文本不能为空")
            
            # 检查文本长度，如果超过阈值则自动分段处理
            max_single_text_length = 70  # 实测安全长度
            if len(text) > max_single_text_length and is_preset:
                logging.info(f"文本长度 {len(text)} 超过单次合成阈值({max_single_text_length})，自动使用分段合成")
                return self._synthesize_long_text_inner(text, voice_id)
                
            # 原有合成逻辑
            if is_preset:
                # 使用预置声音
                preset_voice_name = voice_id
                # 如果voice_id是数字或数字字符串，尝试将其映射到实际的声音名称
                preset_voices = self._get_preset_voices()
                
                if isinstance(voice_id, (int, str)) and str(voice_id).isdigit():
                    voice_idx = int(voice_id)
                    if 0 < voice_idx <= len(preset_voices):
                        preset_voice_name = preset_voices[voice_idx - 1]
                        logging.info(f"将数字ID {voice_id} 映射到预置声音: {preset_voice_name}")
                    else:
                        if preset_voices:
                            preset_voice_name = preset_voices[0]
                        else:
                            raise ValueError(f"无效的预置声音索引 {voice_id}，且无可用的预置声音")
                        logging.warning(f"无效的预置声音索引 {voice_id}，使用默认声音: {preset_voice_name}")
                
                logging.info(f"使用预置声音 '{preset_voice_name}' 合成文本: '{text[:30]}...'")
                
                # 为CosyVoice和CosyVoice2提供不同的实现
                if self.model_type == "CosyVoice":
                    try:
                        result = next(self.model.inference_sft(text, preset_voice_name, stream=False))
                        audio_data = result['tts_speech'].numpy().flatten()
                        # 记录音频数据类型和范围
                        logging.info(f"预置声音合成结果 - 类型: {audio_data.dtype}, 形状: {audio_data.shape}, 范围: [{audio_data.min()}, {audio_data.max()}]")
                        return {
                            "audio_data": audio_data,
                            "sample_rate": self.sample_rate
                        }
                    except Exception as e:
                        logging.error(f"CosyVoice sft合成失败: {e}")
                        raise
                        
                elif self.model_type == "CosyVoice2":
                    try:
                        result = next(self.model.inference_sft(text, preset_voice_name, stream=False))
                        audio_data = result['tts_speech'].numpy().flatten()
                        # 记录音频数据类型和范围
                        logging.info(f"预置声音合成结果 - 类型: {audio_data.dtype}, 形状: {audio_data.shape}, 范围: [{audio_data.min()}, {audio_data.max()}]")
                        return {
                            "audio_data": audio_data,
                            "sample_rate": self.sample_rate
                        }
                    except (AttributeError, Exception) as e:
                        logging.warning(f"CosyVoice2 sft方法失败，尝试其他方法: {e}")
                        
                        # 如果sft失败，尝试使用zero-shot方法
                        try:
                            # 为了使用zero-shot方法，我们需要一个音频样本
                            sample_path = os.path.join(os.path.dirname(__file__), "assets", "sample_voice.wav")
                            
                            if not os.path.exists(sample_path) or os.path.getsize(sample_path) == 0:
                                # 尝试找一个已有的样本文件
                                import glob
                                uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
                                samples = glob.glob(os.path.join(uploads_dir, "*.wav"))
                                
                                if samples:
                                    import shutil
                                    os.makedirs(os.path.dirname(sample_path), exist_ok=True)
                                    shutil.copy(samples[0], sample_path)
                                else:
                                    raise ValueError("无可用的声音样本")
                            
                            # 加载样本音频
                            sample_speech = load_wav(sample_path, 16000)
                            
                            # 使用cross_lingual方法
                            result = next(self.model.inference_cross_lingual(text, sample_speech, stream=False))
                            audio_data = result['tts_speech'].numpy().flatten()
                            # 记录音频数据类型和范围
                            logging.info(f"预置声音备选方法合成结果 - 类型: {audio_data.dtype}, 形状: {audio_data.shape}, 范围: [{audio_data.min()}, {audio_data.max()}]")
                            return {
                                "audio_data": audio_data,
                                "sample_rate": self.sample_rate
                            }
                        except Exception as cross_error:
                            logging.error(f"Cross-lingual方法也失败: {cross_error}")
                            raise ValueError(f"无法使用预置声音'{preset_voice_name}'合成: {e}, {cross_error}")
            
            else:
                # 使用上传的声音样本（零样本克隆）
                if not prompt_audio:
                    raise ValueError("使用自定义声音时需要提供声音样本")
                
                logging.info(f"使用自定义声音 {voice_id} 合成文本: '{text[:30]}...'")
                logging.info(f"提示音频: {prompt_audio}")
                logging.info(f"提示文本: {prompt_text or '(无)'}")
                
                prompt_speech_16k = load_wav(prompt_audio, 16000)
                
                # 记录提示音频信息
                logging.info(f"提示音频信息 - 形状: {prompt_speech_16k.shape}, 类型: {prompt_speech_16k.dtype}")
                
                # 确保提示文本不为空
                safe_prompt_text = prompt_text if prompt_text else "这是一段示例语音。"
                
                if self.model_type == "CosyVoice":
                    result = next(self.model.inference_zero_shot(text, safe_prompt_text, prompt_speech_16k, stream=False))
                elif self.model_type == "CosyVoice2":
                    result = next(self.model.inference_zero_shot(text, safe_prompt_text, prompt_speech_16k, stream=False))
                
                audio_data = result['tts_speech'].numpy().flatten()
                
                # 记录合成结果信息
                logging.info(f"自定义声音合成结果 - 类型: {audio_data.dtype}, 形状: {audio_data.shape}, 范围: [{audio_data.min()}, {audio_data.max()}]")
                
                # 确保音频数据有效
                if audio_data.size == 0:
                    logging.error("合成的音频数据为空")
                    raise ValueError("合成的音频数据为空")
                
                # 如果音频数据是浮点类型，转换为整数类型
                if np.issubdtype(audio_data.dtype, np.floating):
                    if audio_data.max() <= 1.0 and audio_data.min() >= -1.0:
                        # 音频数据在 [-1, 1] 范围内，缩放到 int16 范围
                        audio_data = (audio_data * 32767).astype(np.int16)
                        logging.info(f"音频数据已从浮点转换为int16，新范围: [{audio_data.min()}, {audio_data.max()}]")
                    else:
                        # 音频数据不在 [-1, 1] 范围内
                        audio_data = audio_data.astype(np.int16)
                        logging.info(f"音频数据已直接转换为int16，新范围: [{audio_data.min()}, {audio_data.max()}]")
                
                return {
                    "audio_data": audio_data,
                    "sample_rate": self.sample_rate
                }
                
        except Exception as e:
            logging.error(f"语音合成失败: {e}")
            raise

    def _synthesize_long_text_inner(self, text, speaker_name):
        """
        内部方法：处理长文本合成，直接返回合并后的音频数据
        """
        logging.info(f"开始长文本内部处理，共 {len(text)} 个字符")
        
        # 确保模型已初始化
        if self.model is None:
            self._initialize_model()
        
        # 将文本分割成句子
        sentences = split_text(text)
        logging.info(f"文本已分割为 {len(sentences)} 个句子")
        
        # 打印前几个句子便于调试
        for i in range(min(3, len(sentences))):
            logging.info(f"句子示例 {i+1}: {sentences[i]}")
        
        # 将句子合并为合适长度的块
        max_chunk_length = 70  # 经测试的安全单次合成长度
        chunks = merge_sentences_into_chunks(sentences, max_chunk_length)
        logging.info(f"句子已合并为 {len(chunks)} 个块")
        
        # 显示每个块的大小以进行调试
        for i, chunk in enumerate(chunks):
            logging.info(f"块 {i+1} 长度: {len(chunk)}")
        
        # 直接合成所有块的音频数据，然后合并
        audio_segments = []
        sample_rate = None
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            logging.info(f"正在合成第 {i+1}/{len(chunks)} 块，内容: '{chunk}'")
            try:
                # 为CosyVoice和CosyVoice2提供不同的实现
                if self.model_type == "CosyVoice":
                    try:
                        result = next(self.model.inference_sft(chunk, speaker_name, stream=False))
                        chunk_audio = result['tts_speech'].numpy().flatten()
                        chunk_rate = self.sample_rate
                    except Exception as e:
                        logging.error(f"CosyVoice sft合成块 {i+1} 失败: {e}")
                        continue
                        
                elif self.model_type == "CosyVoice2":
                    try:
                        result = next(self.model.inference_sft(chunk, speaker_name, stream=False))
                        chunk_audio = result['tts_speech'].numpy().flatten()
                        chunk_rate = self.sample_rate
                    except (AttributeError, Exception) as e:
                        logging.warning(f"CosyVoice2 sft方法失败，尝试其他方法: {e}")
                        continue
                
                # 保存采样率（第一个成功的块）
                if sample_rate is None:
                    sample_rate = chunk_rate
                
                # 收集音频数据
                audio_segments.append(chunk_audio)
                logging.info(f"第 {i+1}/{len(chunks)} 块合成完成，音频长度: {len(chunk_audio)/chunk_rate:.2f}秒")
            except Exception as e:
                logging.error(f"合成第 {i+1} 块时出错: {str(e)}")
        
        # 如果没有成功合成任何块，返回None
        if not audio_segments:
            logging.error("没有成功合成任何文本块")
            raise ValueError("无法合成任何文本")
        
        # 合并所有音频数据
        logging.info(f"合并 {len(audio_segments)} 个音频片段")
        combined_audio = np.concatenate(audio_segments)
        logging.info(f"合并后音频总长度: {len(combined_audio)/sample_rate:.2f}秒")
        
        return {
            "audio_data": combined_audio,
            "sample_rate": sample_rate
        }

    def synthesize_long_text(self, text, speaker_name, output_path=None, max_chunk_length=70):
        """
        合成长文本，通过将文本分段处理然后合并结果
        
        参数:
        text: 要合成的文本
        speaker_name: 说话人名称
        output_path: 输出音频文件路径，如果为None则创建临时文件
        max_chunk_length: 每个文本块的最大字符数
        
        返回:
        输出音频文件的路径或音频数据
        """
        logging.info(f"准备合成长文本，共 {len(text)} 个字符")
        
        if not text.strip():
            logging.error("输入文本为空，无法合成")
            return None
        
        try:
            # 使用内部处理方法获取合成的音频数据
            result = self._synthesize_long_text_inner(text, speaker_name)
            
            # 如果需要保存到文件
            if output_path:
                sf.write(output_path, result["audio_data"], result["sample_rate"])
                return output_path
            
            # 否则返回音频数据
            return result
            
        except Exception as e:
            logging.error(f"长文本合成失败: {e}")
            raise
            
    def synthesize(self, text, speaker_name, output_path=None):
        """
        合成文本为语音。如果文本长度超过阈值，自动使用长文本处理方法。
        
        参数:
        text: 要合成的文本
        speaker_name: 说话人名称
        output_path: 输出音频文件路径
        
        返回:
        输出音频文件的路径或音频数据
        """
        logging.info(f"开始合成文本，长度: {len(text)}")
        
        # 检查文本长度，如果超过阈值则使用长文本处理方法
        max_single_text_length = 70  # 根据实际测试调整
        
        if len(text) > max_single_text_length:  
            logging.info(f"文本长度 {len(text)} 超过阈值({max_single_text_length})，使用长文本处理")
            return self.synthesize_long_text(text, speaker_name, output_path)
        
        # 确保模型已初始化
        if self.model is None:
            self._initialize_model()
        
        logging.info(f"使用标准合成方法处理文本: {text[:30]}...")
        # 对于短文本的合成
        result = self.synthesize_speech(text, speaker_name, is_preset=True)
        
        # 如果需要保存到文件
        if output_path:
            sf.write(output_path, result["audio_data"], result["sample_rate"])
            return output_path
        
        # 否则返回音频数据
        return result

# 如果直接运行此脚本，支持通过命令行参数控制是否初始化模型
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CosyVoiceHelper测试程序")
    parser.add_argument('--noinit', action='store_true', help='不初始化模型')
    args = parser.parse_args()
    
    # 根据命令行参数决定是否立即加载模型
    helper = CosyVoiceHelper(lazy_load=args.noinit)
    
    # 如果指定了不初始化，则手动初始化以测试
    if args.noinit:
        helper._initialize_model()
    
    # 打印预设声音列表
    print(f"预设声音: {helper.get_preset_voices()}")
