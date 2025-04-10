// 获取用户上传的声音
async function loadVoices() {
    try {
        // 获取用户上传的声音
        const response = await fetch('/api/voices', {
            headers: {
                'Authorization': 'Bearer ' + getToken()
            }
        });
        
        if (!response.ok) {
            throw new Error('获取声音列表失败');
        }
        
        const data = await response.json();
        
        // 获取预置的声音
        const presetResponse = await fetch('/api/preset_voices', {
            headers: {
                'Authorization': 'Bearer ' + getToken()
            }
        });
        
        if (!presetResponse.ok) {
            throw new Error('获取预置声音列表失败');
        }
        
        const presetVoices = await presetResponse.json();
        
        // 清空下拉列表
        const voiceSelect = document.getElementById('voice');
        voiceSelect.innerHTML = '';
        
        if (presetVoices && presetVoices.length > 0) {
            // 创建预设声音分组
            const presetGroup = document.createElement('optgroup');
            presetGroup.label = '预设声音';
            
            presetVoices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice;
                option.textContent = voice;
                option.dataset.isPreset = 'true';
                presetGroup.appendChild(option);
            });
            
            voiceSelect.appendChild(presetGroup);
        }
        
        // 添加用户声音分组
        if (data && data.length > 0) {
            const userGroup = document.createElement('optgroup');
            userGroup.label = '我的声音';
            
            data.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.id;
                option.textContent = voice.name;
                option.dataset.isPreset = 'false';
                userGroup.appendChild(option);
            });
            
            voiceSelect.appendChild(userGroup);
        }
        
    } catch (error) {
        console.error('加载声音列表失败:', error);
        showMessage('加载声音列表失败: ' + error.message, 'error');
    }
}

// 修改语音合成函数支持预置声音
async function synthesize() {
    const text = document.getElementById('text').value;
    const voiceSelect = document.getElementById('voice');
    
    if (!text || !voiceSelect.value) {
        showMessage('请输入文本并选择声音', 'error');
        return;
    }
    
    // 获取选择的声音ID和是否为预置声音的信息
    const selectedOption = voiceSelect.options[voiceSelect.selectedIndex];
    const voiceId = selectedOption.value;
    const isPreset = selectedOption.dataset.isPreset === 'true';
    
    try {
        // 显示处理中状态
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="loading-spinner"></span>合成中...';
        }
        
        // 构建请求数据
        const formData = new FormData();
        formData.append('text', text);
        formData.append('voice_id', voiceId);
        formData.append('is_preset', isPreset);
        
        const response = await fetch('/api/synthesize', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '合成失败');
        }
        
        // 处理音频响应
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        
        // 更新音频播放器
        const audioPlayer = document.getElementById('resultAudio');
        if (audioPlayer) {
            audioPlayer.src = audioUrl;
            audioPlayer.style.display = 'block';
            
            // 尝试自动播放
            try {
                await audioPlayer.play();
            } catch (e) {
                console.log('自动播放失败，需要用户交互', e);
            }
        }
        
        // 显示成功消息
        showMessage('语音合成成功！', 'success');
        
    } catch (error) {
        console.error('语音合成失败:', error);
        showMessage('合成失败: ' + error.message, 'error');
    } finally {
        // 恢复按钮状态
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = '生成语音';
        }
    }
}