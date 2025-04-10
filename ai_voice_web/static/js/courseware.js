// 加载声音列表
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
        
        // 如果有预置声音，添加预置声音分组
        if (presetVoices && presetVoices.length > 0) {
            const presetGroup = document.createElement('optgroup');
            presetGroup.label = '预置声音';
            
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

// 修改上传课件函数支持预置声音
async function uploadCourseware() {
    const coursewareFile = document.getElementById('courseware').files[0];
    const voiceSelect = document.getElementById('voice');
    const voiceOption = voiceSelect.options[voiceSelect.selectedIndex];
    const voiceId = voiceOption.value;
    const isPreset = voiceOption.dataset.isPreset === 'true';
    
    if (!coursewareFile) {
        showMessage('请选择一个课件文件', 'error');
        return;
    }
    
    if (!voiceId) {
        showMessage('请选择一个声音', 'error');
        return;
    }
    
    // 记录请求信息到控制台，便于调试
    console.log(`课件处理请求 - 文件: ${coursewareFile.name}, 声音ID: ${voiceId}, 是否预置: ${isPreset}`);
    
    // 检查文件大小
    if (coursewareFile.size < 0.5 * 1024 * 1024) { // 小于0.5MB
        showMessage('文件过小，请上传大于0.5MB的课件', 'error');
        return;
    }
    
    if (coursewareFile.size > 20 * 1024 * 1024) { // 大于20MB
        showMessage('文件过大，请上传小于20MB的课件', 'error');
        return;
    }
    
    // 检查文件类型
    const fileType = coursewareFile.name.split('.').pop().toLowerCase();
    if (!['ppt', 'pptx', 'doc', 'docx'].includes(fileType)) {
        showMessage('只支持PPT和Word文档(.ppt, .pptx, .doc, .docx)', 'error');
        return;
    }
    
    try {
        showLoading('正在处理课件，这可能需要几分钟时间...');
        
        const formData = new FormData();
        formData.append('file', coursewareFile);
        formData.append('voice_id', voiceId);
        formData.append('is_preset', isPreset);
        
        const response = await fetch('/api/courseware', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + getToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '课件处理失败');
        }
        
        const result = await response.json();
        
        hideLoading();
        showMessage('课件处理成功!', 'success');
        
        // 显示下载链接
        const downloadLink = document.getElementById('downloadLink');
        downloadLink.href = result.download_url;
        downloadLink.textContent = '下载处理后的课件';
        downloadLink.style.display = 'block';
        
        // 刷新课件列表
        loadCoursewareList();
    } catch (error) {
        hideLoading();
        console.error('课件处理失败:', error);
        showMessage('课件处理失败: ' + error.message, 'error');
    }
}