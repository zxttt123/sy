// 检查登录状态
function checkLogin() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.href.includes('login.html') && !window.location.href.includes('register.html')) {
        window.location.href = 'login.html';
        return;
    }
    
    // 检查管理员界面的访问权限
    if (window.location.href.includes('admin.html')) {
        // 先显示调试信息
        const isAdmin = localStorage.getItem('isAdmin') === 'true';
        console.log('检查管理员权限:', {
            'token存在': !!token,
            'isAdmin标记值': localStorage.getItem('isAdmin'),
            'isAdmin转换为布尔值': isAdmin
        });
        
        // 尝试从服务器验证管理员权限
        fetch('/api/admin/check', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            console.log('管理员检查响应状态:', response.status);
            
            if (response.ok) {
                return response.json().then(data => {
                    console.log('管理员检查响应数据:', data);
                    localStorage.setItem('isAdmin', 'true');
                    console.log('管理员权限验证成功，已更新本地存储');
                });
            } else {
                // 如果是403错误，清除isAdmin标记
                if (response.status === 403) {
                    localStorage.removeItem('isAdmin');
                    console.error('服务器拒绝管理员访问');
                    alert('您没有管理员权限');
                    window.location.href = 'index.html';
                } else {
                    // 对于其他错误，先获取错误详情
                    return response.json().then(errorData => {
                        console.error('管理员检查失败:', errorData);
                        alert('权限验证失败: ' + (errorData.detail || '未知错误'));
                        window.location.href = 'index.html';
                    }).catch(() => {
                        // 如果无法解析JSON
                        console.error('无法解析错误响应');
                        alert('权限验证失败');
                        window.location.href = 'index.html';
                    });
                }
            }
        })
        .catch(error => {
            console.error('管理员权限验证网络错误:', error);
            alert('管理员权限验证失败，请检查网络连接');
            window.location.href = 'index.html';
        });
    }
}

// 登录处理
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/api/token', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', username);
            
            // 明确处理管理员权限，使用严格转换
            if (data.is_admin === true) {
                console.log('用户是管理员，设置本地标记');
                localStorage.setItem('isAdmin', 'true');
            } else {
                console.log('用户不是管理员，确保移除标记');
                localStorage.removeItem('isAdmin');
            }
            
            window.location.href = 'index.html';
        } else {
            const errorData = await response.json();
            alert('登录失败: ' + (errorData.detail || '用户名或密码错误'));
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('登录失败: ' + error.message);
    }
}

// 注册处理 - 修改为只在注册页面直接调用时才执行
async function handleRegister(event) {
    // 检查是否有其他事件处理程序已经处理了此事件
    if (event.defaultPrevented) {
        console.log('已有处理程序处理了注册事件，跳过main.js中的handleRegister');
        return;
    }
    
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const userRole = document.getElementById('userRole')?.value || '';

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        if (userRole) {
            formData.append('user_role', userRole);
        }

        const response = await fetch('/api/register', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            alert('注册成功！请登录');
            window.location.href = 'login.html';
        } else {
            alert('注册失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('注册失败: ' + error.message);
    }
}

// 加载声音列表
async function loadVoiceList() {
    try {
        // 加载预设声音
        const presetResponse = await fetch('/api/voices?type=preset', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        // 加载自定义声音
        const customResponse = await fetch('/api/voices?type=custom', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (presetResponse.ok && customResponse.ok) {
            const presetVoices = await presetResponse.json();
            const customVoices = await customResponse.json();
            
            const voiceSelect = document.getElementById('voiceId');
            if (voiceSelect) {
                voiceSelect.innerHTML = ''; // 清空现有选项
                
                // 添加预设声音选项
                if (presetVoices.length > 0) {
                    const presetGroup = document.createElement('optgroup');
                    presetGroup.label = '预设声音';
                    presetVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'true'; // 添加数据属性标记为预置声音
                        presetGroup.appendChild(option);
                    });
                    voiceSelect.appendChild(presetGroup);
                }
                
                // 添加自定义声音选项
                if (customVoices.length > 0) {
                    const customGroup = document.createElement('optgroup');
                    customGroup.label = '我的声音';
                    customVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'false'; // 添加数据属性标记为非预置声音
                        customGroup.appendChild(option);
                    });
                    voiceSelect.appendChild(customGroup);
                }
            }
            
            // 加载课件制作声音选择框（现在同时包含预置声音和用户自己上传的声音）
            const coursewareVoiceSelect = document.getElementById('coursewareVoiceId');
            if (coursewareVoiceSelect) {
                coursewareVoiceSelect.innerHTML = ''; // 清空现有选项
                
                // 添加预设声音选项
                if (presetVoices.length > 0) {
                    const presetGroup = document.createElement('optgroup');
                    presetGroup.label = '预设声音';
                    presetVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'true'; // 添加数据属性标记为预置声音
                        presetGroup.appendChild(option);
                    });
                    coursewareVoiceSelect.appendChild(presetGroup);
                }
                
                // 添加用户自己的声音
                if (customVoices.length > 0) {
                    const customGroup = document.createElement('optgroup');
                    customGroup.label = '我的声音';
                    customVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'false'; // 添加数据属性标记为非预置声音
                        customGroup.appendChild(option);
                    });
                    coursewareVoiceSelect.appendChild(customGroup);
                } else if (presetVoices.length === 0) {
                    // 如果没有可用声音，添加提示选项
                    const option = document.createElement('option');
                    option.value = "";
                    option.disabled = true;
                    option.selected = true;
                    option.textContent = "没有可用声音";
                    coursewareVoiceSelect.appendChild(option);
                }
            }

            // 加载声音置换声音选择框
            const voiceReplaceSelect = document.getElementById('voiceReplaceVoiceId');
            if (voiceReplaceSelect) {
                voiceReplaceSelect.innerHTML = ''; // 清空现有选项
                
                // 添加预设声音选项
                if (presetVoices.length > 0) {
                    const presetGroup = document.createElement('optgroup');
                    presetGroup.label = '预设声音';
                    presetVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'true'; // 添加数据属性标记为预置声音
                        presetGroup.appendChild(option);
                    });
                    voiceReplaceSelect.appendChild(presetGroup);
                }
                
                // 添加自定义声音选项
                if (customVoices.length > 0) {
                    const customGroup = document.createElement('optgroup');
                    customGroup.label = '我的声音';
                    customVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = voice.name;
                        option.dataset.isPreset = 'false'; // 添加数据属性标记为非预置声音
                        customGroup.appendChild(option);
                    });
                    voiceReplaceSelect.appendChild(customGroup);
                } else if (presetVoices.length === 0) {
                    // 如果没有可用声音，添加提示选项
                    const option = document.createElement('option');
                    option.value = "";
                    option.disabled = true;
                    option.selected = true;
                    option.textContent = "没有可用声音";
                    voiceReplaceSelect.appendChild(option);
                }
            }
        }
    } catch (error) {
        console.error('Error loading voices:', error);
    }
}

// 上传声音样本
async function uploadVoice(event) {
    event.preventDefault();
    
    const audioFile = document.getElementById('audioFile').files[0];
    const promptText = document.getElementById('promptText').value;
    
    if (!audioFile) {
        showToast('请选择音频文件', 'error');
        return;
    }

    // 验证文件类型
    if (!audioFile.name.toLowerCase().match(/\.(wav|mp3)$/)) {
        showToast('只支持 WAV 或 MP3 格式的音频文件', 'error');
        return;
    }
    
    // 检查文件大小 (50MB限制)
    if (audioFile.size > 50 * 1024 * 1024) {
        showToast('文件大小不能超过50MB', 'error');
        return;
    }

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>上传中...';

    const formData = new FormData();
    formData.append('audio', audioFile);
    formData.append('prompt_text', promptText);

    try {
        console.log('开始上传文件:', audioFile.name, 'Size:', audioFile.size);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });

        console.log('上传请求完成，状态:', response.status);
        
        // 获取响应内容类型
        const contentType = response.headers.get('content-type');
        console.log('响应内容类型:', contentType);
        
        if (response.ok) {
            let data;
            
            // 尝试解析响应
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
                console.log('收到JSON响应:', data);
            } else {
                const text = await response.text();
                console.log('收到非JSON响应:', text.substring(0, 100) + '...');
                data = { message: "文件上传成功，但响应格式异常" };
            }
            
            showToast('声音样本上传成功！', 'success');
            document.getElementById('uploadForm').reset();
            await loadVoiceList();
            
            // 添加成功提示并滚动到语音合成区域
            const synthesisPanel = document.querySelector('.synthesis-panel');
            if (synthesisPanel) {
                const successNote = document.createElement('div');
                successNote.className = 'tips-card';
                successNote.style.backgroundColor = '#f0fff5';
                successNote.style.borderLeftColor = '#2ac769';
                successNote.innerHTML = `
                    <h4 style="color: #2ac769;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        上传成功
                    </h4>
                    <p>声音样本上传成功！现在您可以在"语音合成"部分选择您的声音进行合成了。</p>
                `;
                
                // 查找上传表单的位置并插入成功提示
                const uploadForm = document.getElementById('uploadForm');
                uploadForm.parentNode.insertBefore(successNote, uploadForm.nextSibling);
                
                // 滚动到语音合成部分
                setTimeout(() => {
                    synthesisPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 800);
            }
        } else {
            let errorMessage = '上传失败';
            
            try {
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } else {
                    const text = await response.text();
                    console.error('错误响应内容:', text.substring(0, 100) + '...');
                }
            } catch (parseError) {
                console.error('解析响应失败:', parseError);
            }
            
            throw new Error(errorMessage);
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 6px;">
                <path d="M12 15V3M12 3L7 8M12 3L17 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            上传声音样本
        `;
    }
}

// 修改语音合成部分，让结果在面板内显示
async function synthesizeVoice(event) {
    event.preventDefault();
    
    const voiceId = document.getElementById('voiceId').value;
    const targetText = document.getElementById('targetText').value;
    
    if (!voiceId || !targetText) {
        showToast('请选择声音并输入目标文本', 'error');
        return;
    }

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>合成中...';
    
    // 添加进度反馈提示
    showToast('开始合成语音，请稍候...', 'info');

    try {
        const formData = new FormData();
        formData.append('voice_id', voiceId);
        formData.append('target_text', targetText);

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

        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        const audioPlayer = document.getElementById('resultAudio');
        audioPlayer.src = audioUrl;
        
        document.querySelector('.result-section').style.display = 'block';
        
        // 设置下载按钮
        const downloadButton = document.getElementById('downloadButton');
        downloadButton.onclick = () => {
            const a = document.createElement('a');
            a.href = audioUrl;
            a.download = `synthesized_${new Date().toISOString().slice(0,10)}.wav`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };

        showToast('语音合成成功！', 'success');
        
        // 平滑滚动到播放器
        document.querySelector('.result-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // 自动播放音频
        try {
            await audioPlayer.play();
        } catch(e) {
            console.log('自动播放失败，需要用户交互');
        }
    } catch (error) {
        console.error('Synthesis error:', error);
        showToast('合成失败: ' + error.message, 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = '生成语音';
    }
}

// 课件处理
async function processCourseware(event) {
    event.preventDefault();
    
    const coursewareFile = document.getElementById('coursewareFile').files[0];
    const voiceSelect = document.getElementById('coursewareVoiceId');
    const voiceOption = voiceSelect.options[voiceSelect.selectedIndex];
    const voiceId = voiceOption.value;
    const isPreset = voiceOption.dataset.isPreset === 'true';
    
    if (!coursewareFile) {
        showToast('请选择课件文件', 'error');
        return;
    }

    if (!voiceId) {
        showToast('请选择声音', 'error');
        return;
    }

    // 验证文件类型
    if (!coursewareFile.name.toLowerCase().match(/\.(ppt|pptx|doc|docx)$/)) {
        showToast('只支持 PPT、PPTX、DOC 或 DOCX 格式的课件文件', 'error');
        return;
    }
    
    // 检查文件大小 (0.5MB~20MB限制)
    if (coursewareFile.size < 0.5 * 1024 * 1024 || coursewareFile.size > 20 * 1024 * 1024) {
        showToast('文件大小需要在0.5MB到20MB之间', 'error');
        return;
    }

    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>处理中...';
    
    // 显示进度指示
    const progressSection = document.getElementById('coursewareProgressSection');
    progressSection.style.display = 'block';
    const progressStatus = document.getElementById('progressStatus');
    progressStatus.textContent = '课件处理中，请耐心等待...';

    const formData = new FormData();
    formData.append('courseware', coursewareFile);
    formData.append('voice_id', voiceId);
    formData.append('is_preset', isPreset); // 添加is_preset参数

    try {
        console.log('开始上传课件:', coursewareFile.name, 'Size:', coursewareFile.size, '是预置声音:', isPreset);
        
        progressStatus.textContent = '上传课件文件中...';
        
        const response = await fetch('/api/courseware/process', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });

        console.log('上传请求完成，状态:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('收到处理结果:', data);
            
            // 开始轮询任务状态
            const taskId = data.task_id;
            const taskResult = await pollTaskStatus(taskId, progressStatus);
            
            // 获取原始文件名和处理日期
            const originalFilename = taskResult.originalFilename || '';
            const processDate = taskResult.processDate || '';
            
            // 显示下载链接
            const coursewareResult = document.getElementById('coursewareResult');
            coursewareResult.style.display = 'block';
            
            const downloadVideoBtn = document.getElementById('downloadVideoBtn');
            downloadVideoBtn.onclick = () => {
                // 修改下载行为，使用AJAX携带认证令牌下载文件
                const token = localStorage.getItem('token');
                const progressStatus = document.getElementById('progressStatus');
                
                if (progressStatus) {
                    progressStatus.textContent = '准备下载中...';
                }
                
                // 构建与服务器一致的文件名
                const fileExt = coursewareFile.name.toLowerCase().endsWith('.doc') || coursewareFile.name.toLowerCase().endsWith('.docx') ? 'wav' : 'mp4';
                const filePrefix = fileExt === 'wav' ? '课件音频' : '课件视频';
                const fileName = `${filePrefix}_${originalFilename}_${processDate}.${fileExt}`;
                
                // 使用fetch API进行认证下载
                fetch(`/api/courseware/download/${taskId}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`下载失败: ${response.status} ${response.statusText}`);
                    }
                    return response.blob();
                })
                .then(blob => {
                    // 创建blob URL并触发下载
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = fileName;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    if (progressStatus) {
                        progressStatus.textContent = '下载完成！';
                    }
                })
                .catch(error => {
                    console.error('下载错误:', error);
                    alert(`下载失败: ${error.message}`);
                    if (progressStatus) {
                        progressStatus.textContent = `下载失败: ${error.message}`;
                    }
                });
            };
            
            showToast('课件处理成功！', 'success');
        } else {
            let errorMessage = '课件处理失败';
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (parseError) {
                console.error('解析响应失败:', parseError);
            }
            
            progressStatus.textContent = '处理失败: ' + errorMessage;
            throw new Error(errorMessage);
        }
    } catch (error) {
        console.error('Courseware processing error:', error);
        showToast('课件处理失败: ' + error.message, 'error');
        progressStatus.textContent = '处理失败: ' + error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = '开始处理';
    }
}

// 轮询任务状态
async function pollTaskStatus(taskId, progressElement) {
    return new Promise((resolve, reject) => {
        let completed = false;
        let lastProgress = 0;
        let originalFilename = '';  // 添加变量存储原始文件名
        let processDate = '';       // 添加变量存储处理日期
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/courseware/status/${taskId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error('获取任务状态失败');
                }
                
                const statusData = await response.json();
                console.log('任务状态:', statusData);
                
                // 保存文件名相关信息
                if (statusData.original_filename) {
                    originalFilename = statusData.original_filename;
                }
                if (statusData.process_date) {
                    processDate = statusData.process_date;
                }
                
                // 更新进度显示
                if (statusData.message) {
                    progressElement.textContent = statusData.message;
                }
                
                if (statusData.progress !== undefined && statusData.progress !== lastProgress) {
                    lastProgress = statusData.progress;
                    progressElement.textContent = `${statusData.message || '处理中...'} (${statusData.progress}%)`;
                    
                    // 添加进度条
                    let progressBar = document.getElementById('progressBar');
                    if (!progressBar) {
                        progressBar = document.createElement('div');
                        progressBar.id = 'progressBar';
                        progressBar.className = 'progress-bar';
                        
                        const progressBarContainer = document.createElement('div');
                        progressBarContainer.className = 'progress-bar-container';
                        progressBarContainer.appendChild(progressBar);
                        
                        progressElement.parentNode.insertBefore(progressBarContainer, progressElement.nextSibling);
                    }
                    progressBar.style.width = `${statusData.progress}%`;
                }
                
                if (statusData.status === 'completed') {
                    progressElement.textContent = '处理完成！';
                    completed = true;
                    resolve({...statusData, originalFilename, processDate});  // 返回包含文件名信息的数据
                } else if (statusData.status === 'failed') {
                    progressElement.textContent = statusData.message || '处理失败';
                    completed = true;
                    reject(new Error(statusData.message || '处理失败'));
                }
            } catch (error) {
                console.error('获取任务状态失败:', error);
                progressElement.textContent = '获取任务状态失败: ' + error.message;
                completed = true;
                reject(error);
            }
            
            if (!completed) {
                // 继续轮询，每3秒查询一次
                setTimeout(checkStatus, 3000);
            }
        };
        
        // 开始轮询
        checkStatus();
    });
}

// 声音置换相关函数
async function uploadVideoForVoiceReplacement(event) {
    event.preventDefault();
    
    const videoFile = document.getElementById('voiceReplaceVideoFile').files[0];
    if (!videoFile) {
        showToast('请选择视频文件', 'error');
        return;
    }
    
    // 验证文件类型
    if (!videoFile.name.toLowerCase().match(/\.(mp4|avi|mov|mkv|webm)$/)) {
        showToast('仅支持MP4、AVI、MOV、MKV和WEBM格式的视频', 'error');
        return;
    }
    
    // 验证文件大小 (最大100MB)
    if (videoFile.size > 100 * 1024 * 1024) {
        showToast('文件大小不能超过100MB', 'error');
        return;
    }
    
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>上传中...';
    
    // 显示进度指示
    const progressSection = document.getElementById('voiceReplaceProgressSection');
    progressSection.style.display = 'block';
    const progressStatus = document.getElementById('voiceReplaceProgressStatus');
    progressStatus.textContent = '正在上传视频文件...';
    
    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('file', videoFile);
        
        // 上传视频文件
        const response = await fetch('/api/voice-replace/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '上传失败');
        }
        
        const data = await response.json();
        const taskId = data.task_id;
        
        progressStatus.textContent = '视频已上传，开始分析音频...';
        
        // 显示分析按钮
        document.getElementById('voiceReplaceAnalyzeSection').style.display = 'block';
        document.getElementById('voiceReplaceTaskId').value = taskId;
        
        showToast('视频上传成功！请点击"开始分析"按钮进行音频分析', 'success');
        
        // 保存任务信息
        window.voiceReplaceCurrentTask = {
            taskId: taskId,
            filename: videoFile.name
        };
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast('上传失败: ' + error.message, 'error');
        progressStatus.textContent = '上传失败: ' + error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 6px;">
                <path d="M12 15V3M12 3L7 8M12 3L17 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            上传视频
        `;
    }
}

async function analyzeVideoAudio(event) {
    event.preventDefault();
    
    const taskId = document.getElementById('voiceReplaceTaskId').value;
    if (!taskId) {
        showToast('任务ID不能为空', 'error');
        return;
    }
    
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>分析中...';
    
    const progressStatus = document.getElementById('voiceReplaceProgressStatus');
    progressStatus.textContent = '正在分析视频中的音频...';
    
    try {
        // 开始分析请求
        const response = await fetch(`/api/voice-replace/analyze/${taskId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '分析失败');
        }
        
        // 获取任务结果
        const result = await pollVoiceReplaceTaskStatus(taskId);
        
        if (result.status === 'analyzed') {
            // 显示识别结果
            document.getElementById('voiceReplaceTextResult').style.display = 'block';
            document.getElementById('recognizedText').value = result.text;
            
            // 显示声音选择部分
            document.getElementById('voiceReplaceSynthesizeSection').style.display = 'block';
            
            showToast('音频分析完成！', 'success');
        } else {
            throw new Error('分析失败: ' + (result.message || '未知错误'));
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        showToast('分析失败: ' + error.message, 'error');
        progressStatus.textContent = '分析失败: ' + error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = '开始分析';
    }
}

async function synthesizeReplacementAudio(event) {
    event.preventDefault();
    
    const taskId = document.getElementById('voiceReplaceTaskId').value;
    if (!taskId) {
        showToast('任务ID不能为空', 'error');
        return;
    }
    
    const voiceSelect = document.getElementById('voiceReplaceVoiceId');
    const voiceOption = voiceSelect.options[voiceSelect.selectedIndex];
    const voiceId = voiceOption.value;
    const isPreset = voiceOption.dataset.isPreset === 'true';
    
    if (!voiceId) {
        showToast('请选择替换声音', 'error');
        return;
    }
    
    // 获取是否添加字幕
    const addSubtitles = document.getElementById('voiceReplaceAddSubtitles').checked;
    
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading-spinner"></span>合成中...';
    
    const progressStatus = document.getElementById('voiceReplaceProgressStatus');
    progressStatus.textContent = '正在合成替换音频...';
    
    try {
        // 创建FormData
        const formData = new FormData();
        formData.append('voice_id', voiceId);
        formData.append('is_preset', isPreset);
        formData.append('add_subtitles', addSubtitles);
        
        // 开始合成请求
        const response = await fetch(`/api/voice-replace/synthesize/${taskId}`, {
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
        
        // 获取任务结果
        const result = await pollVoiceReplaceTaskStatus(taskId);
        
        if (result.status === 'completed') {
            // 显示下载部分
            document.getElementById('voiceReplaceResultSection').style.display = 'block';
            
            // 设置下载视频按钮
            const downloadButton = document.getElementById('voiceReplaceDownloadBtn');
            downloadButton.onclick = () => {
                downloadVoiceReplaceResult(taskId, 'video');
            };
            
            // 设置下载字幕按钮
            const downloadSubtitlesButton = document.getElementById('voiceReplaceDownloadSubtitlesBtn');
            downloadSubtitlesButton.onclick = () => {
                downloadVoiceReplaceResult(taskId, 'subtitles');
            };
            
            showToast('声音置换完成！', 'success');
            progressStatus.textContent = '声音置换完成！您可以下载结果视频和字幕文件。';
        } else {
            throw new Error('合成失败: ' + (result.message || '未知错误'));
        }
        
    } catch (error) {
        console.error('Synthesis error:', error);
        showToast('合成失败: ' + error.message, 'error');
        progressStatus.textContent = '合成失败: ' + error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = '开始合成';
    }
}

async function pollVoiceReplaceTaskStatus(taskId) {
    return new Promise((resolve, reject) => {
        let completed = false;
        let attempts = 0;
        const maxAttempts = 240; // 最多等待20分钟（240 * 5秒）
        
        const progressStatus = document.getElementById('voiceReplaceProgressStatus');
        let progressBar = document.getElementById('voiceReplaceProgressBar');
        let progressBarContainer = document.getElementById('voiceReplaceProgressBarContainer');
        
        if (!progressBarContainer) {
            progressBarContainer = document.createElement('div');
            progressBarContainer.id = 'voiceReplaceProgressBarContainer';
            progressBarContainer.className = 'progress-bar-container';
            
            progressBar = document.createElement('div');
            progressBar.id = 'voiceReplaceProgressBar';
            progressBar.className = 'progress-bar';
            
            progressBarContainer.appendChild(progressBar);
            progressStatus.parentNode.insertBefore(progressBarContainer, progressStatus.nextSibling);
        }
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/voice-replace/status/${taskId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error('获取任务状态失败');
                }
                
                const statusData = await response.json();
                console.log('任务状态:', statusData);
                
                // 更新进度条和状态
                if (progressStatus && statusData.message) {
                    progressStatus.textContent = statusData.message;
                }
                
                if (progressBar && statusData.progress !== undefined) {
                    progressBar.style.width = `${statusData.progress}%`;
                }
                
                // 检查任务状态
                if (statusData.status === 'completed' || statusData.status === 'analyzed') {
                    completed = true;
                    resolve(statusData);
                } else if (statusData.status === 'failed') {
                    completed = true;
                    reject(new Error(statusData.message || '处理失败'));
                }
                
                // 达到最大尝试次数后超时
                attempts++;
                if (attempts >= maxAttempts) {
                    completed = true;
                    reject(new Error('处理超时，请稍后再试'));
                }
                
            } catch (error) {
                console.error('获取任务状态出错:', error);
                attempts++;
                
                // 如果连续多次出错，则结束轮询
                if (attempts >= 5) {
                    completed = true;
                    reject(error);
                }
            }
            
            if (!completed) {
                // 继续轮询
                setTimeout(checkStatus, 5000); // 每5秒查询一次
            }
        };
        
        // 开始轮询
        checkStatus();
    });
}

function downloadVoiceReplaceResult(taskId, type = 'video') {
    const progressStatus = document.getElementById('voiceReplaceProgressStatus');
    if (progressStatus) {
        progressStatus.textContent = `准备下载${type === 'subtitles' ? '字幕' : '视频'}中...`;
    }
    
    // 获取token
    const token = localStorage.getItem('token');
    
    // 创建下载链接 - 根据类型选择不同的API端点
    const downloadUrl = type === 'subtitles' 
        ? `/api/voice-replace/download-subtitles/${taskId}` 
        : `/api/voice-replace/download/${taskId}`;
    
    // 使用fetch API下载文件
    fetch(downloadUrl, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`下载失败: ${response.status} ${response.statusText}`);
        }
        return response.blob();
    })
    .then(blob => {
        // 创建对象URL并触发下载
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // 设置文件名 - 根据类型选择不同的文件扩展名
        const fileName = type === 'subtitles'
            ? `${window.voiceReplaceCurrentTask?.filename || 'video'}_subtitles.srt`
            : `${window.voiceReplaceCurrentTask?.filename || 'video'}_replaced.mp4`;
            
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        if (progressStatus) {
            progressStatus.textContent = `${type === 'subtitles' ? '字幕' : '视频'}下载完成！`;
        }
    })
    .catch(error => {
        console.error('下载错误:', error);
        alert(`下载失败: ${error.message}`);
        
        if (progressStatus) {
            progressStatus.textContent = `下载失败: ${error.message}`;
        }
    });
}

// 退出登录
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('isAdmin');
    showToast('已成功退出登录', 'info');
    setTimeout(() => {
        window.location.href = 'login.html';
    }, 1000);
}

// 检测设备类型
function detectDeviceType() {
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobile = /iphone|ipad|ipod|android|blackberry|windows phone/g.test(userAgent);
    
    if (isMobile) {
        document.body.classList.add('mobile-device');
    } else {
        document.body.classList.add('desktop-device');
    }
}

// 调整表单元素大小
function adjustFormElements() {
    const isMobile = window.innerWidth <= 576;
    
    // 设置上传按钮的文本
    const uploadForms = document.querySelectorAll('input[type="file"]');
    uploadForms.forEach(input => {
        if (isMobile) {
            input.setAttribute('title', '点击选择文件');
        } else {
            input.setAttribute('title', '选择音频文件');
        }
    });
}

// 优化音频播放器
function enhanceAudioPlayer() {
    const audioPlayer = document.getElementById('resultAudio');
    if (audioPlayer) {
        audioPlayer.style.width = '100%';
        audioPlayer.style.maxWidth = window.innerWidth <= 576 ? '100%' : '500px';
    }
}

// 美化文件输入框 - 适应新布局
function enhanceFileInputs() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        const originalTitle = input.title;
        
        // 创建上传图标
        const iconContainer = document.createElement('div');
        iconContainer.className = 'file-upload-icon';
        iconContainer.innerHTML = `
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 15V3M12 3L7 8M12 3L17 8" stroke="#0071e3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M3 15V19C3 20.1046 3.89543 21 5 21H19C20.1046 21 21 20.1046 21 19V15" stroke="#0071e3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
        
        // 创建提示文本
        const textHint = document.createElement('span');
        textHint.className = 'file-text-hint';
        
        if(input.id === 'audioFile') {
            textHint.textContent = '点击或拖拽上传WAV/MP3音频文件';
        } else if(input.id === 'coursewareFile') {
            textHint.textContent = '点击或拖拽上传PPT/DOC课件文件';
        }
        
        // 清空并添加新的子元素
        input.innerHTML = '';
        input.appendChild(iconContainer);
        input.appendChild(textHint);
        
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                const fileSize = (this.files[0].size / (1024 * 1024)).toFixed(2);
                
                // 更新文本提示
                textHint.innerHTML = `已选择: <strong>${fileName}</strong> <span class="file-size">(${fileSize}MB)</span>`;
                
                // 视觉反馈
                iconContainer.innerHTML = `
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 6L9 17L4 12" stroke="#2ac769" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                `;
                this.classList.add('file-selected');
            }
        });
        
        // 重置时恢复原始状态
        input.form?.addEventListener('reset', () => {
            if(input.id === 'audioFile') {
                textHint.textContent = '点击或拖拽上传WAV/MP3音频文件';
            } else if(input.id === 'coursewareFile') {
                textHint.textContent = '点击或拖拽上传PPT/DOC课件文件';
            }
            
            iconContainer.innerHTML = `
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 15V3M12 3L7 8M12 3L17 8" stroke="#0071e3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M3 15V19C3 20.1046 3.89543 21 5 21H19C20.1046 21 21 20.1046 21 19V15" stroke="#0071e3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            `;
            this.classList.remove('file-selected');
        });
        
        // 支持拖拽上传
        input.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        input.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
        });
        
        input.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length) {
                this.files = e.dataTransfer.files;
                
                // 触发change事件
                const changeEvent = new Event('change', { bubbles: true });
                this.dispatchEvent(changeEvent);
            }
        });
    });
}

// 添加文件上传视觉反馈增强
function enhanceFileInputs() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        // 创建上传状态指示器
        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'upload-status';
        
        // 将状态指示器添加到父元素
        input.parentNode.appendChild(statusIndicator);
        
        // 监听文件选择事件
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                const fileSize = (this.files[0].size / (1024 * 1024)).toFixed(2);
                
                // 更新状态指示器
                statusIndicator.innerHTML = `
                    <div class="file-selected-info">
                        <div class="file-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M20 6L9 17L4 12" stroke="#2ac769" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="file-details">
                            <div class="file-name">${fileName}</div>
                            <div class="file-size">${fileSize} MB</div>
                        </div>
                    </div>
                `;
                
                statusIndicator.style.display = 'block';
                this.classList.add('file-selected');
            }
        });
        
        // 支持拖拽上传
        input.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        input.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
        });
        
        input.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length) {
                this.files = e.dataTransfer.files;
                
                const changeEvent = new Event('change', { bubbles: true });
                this.dispatchEvent(changeEvent);
            }
        });
        
        // 重置表单时清除状态
        input.form?.addEventListener('reset', () => {
            statusIndicator.style.display = 'none';
            input.classList.remove('file-selected');
        });
    });
}

// 添加帮助提示
function addHelpTips() {
    // 创建帮助提示元素
    function createHelpTip(element, tipText) {
        const tip = document.createElement('span');
        tip.className = 'help-tip';
        tip.textContent = '?';
        tip.setAttribute('data-tip', tipText);
        element.appendChild(tip);
    }
    
    // 添加各表单字段的帮助提示
    const uploadPromptLabel = document.querySelector('label[for="promptText"]');
    if (uploadPromptLabel) {
        createHelpTip(uploadPromptLabel, '请输入与音频完全匹配的文本，这将帮助系统学习您的声音特征。确保文本准确描述音频内容。');
    }
    
    const targetTextLabel = document.querySelector('label[for="targetText"]');
    if (targetTextLabel) {
        createHelpTip(targetTextLabel, '输入任意文本，系统将使用选择的声音生成对应的语音内容。支持标点符号。');
    }
    
    const voiceIdLabel = document.querySelector('label[for="voiceId"]');
    if (voiceIdLabel) {
        createHelpTip(voiceIdLabel, '选择要使用的声音。预设声音由系统提供，我的声音是您上传的声音样本。');
    }
    
    const coursewareFileLabel = document.querySelector('label[for="coursewareFile"]');
    if (coursewareFileLabel) {
        createHelpTip(coursewareFileLabel, '支持PPT、PPTX、DOC或DOCX格式的课件，大小在0.5MB~20MB之间。系统会提取文字内容并生成语音。');
    }
}

// 增强合成结果显示效果
function enhanceResultDisplay() {
    const resultSection = document.querySelector('.result-section');
    if (resultSection) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'style' && 
                    resultSection.style.display !== 'none' && 
                    !resultSection.classList.contains('animated')) {
                    
                    resultSection.classList.add('animated');
                    resultSection.style.opacity = '0';
                    resultSection.style.transform = 'translateY(20px)';
                    
                    setTimeout(() => {
                        resultSection.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                        resultSection.style.opacity = '1';
                        resultSection.style.transform = 'translateY(0)';
                    }, 10);
                }
            });
        });
        
        observer.observe(resultSection, { attributes: true });
    }
}

// 添加欢迎消息和引导
function addWelcomeGuide() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent || localStorage.getItem('welcomeShown')) return;
    
    const welcomeGuide = document.createElement('div');
    welcomeGuide.className = 'welcome-guide';
    welcomeGuide.innerHTML = `
        <div class="welcome-content">
            <h3>欢迎使用语音合成系统</h3>
            <p>这是您首次使用系统，以下是快速入门引导：</p>
            <ol>
                <li>上传您的语音样本和对应文本</li>
                <li>系统学习您的声音特征</li>
                <li>使用"语音合成"功能，让系统以您的声音生成任意文本的语音</li>
            </ol>
            <p>您还可以使用"课件制作"功能，自动生成带有语音解说的课件视频。</p>
            <button class="got-it-btn">明白了</button>
        </div>
    `;
    
    mainContent.insertBefore(welcomeGuide, mainContent.firstChild);
    
    document.querySelector('.got-it-btn').addEventListener('click', function() {
        welcomeGuide.classList.add('hiding');
        localStorage.setItem('welcomeShown', 'true');
        
        setTimeout(() => {
            welcomeGuide.remove();
        }, 300);
    });
    
    setTimeout(() => {
        welcomeGuide.classList.add('show');
    }, 500);
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 移除已有的提示
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    
    let icon = '';
    switch(type) {
        case 'success':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
            break;
        case 'error':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
            break;
        default:
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 8V12M12 16H12.01M22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 6.47715 2 12 2C17.5228 2 22 6.47715 22 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    }
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message}</div>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// 移除功能面板折叠效果，让所有面板默认展开
function initFeaturePanels() {
    const panels = document.querySelectorAll('.feature-panel');
    
    panels.forEach(panel => {
        // 确保所有面板默认展开且可见
        panel.classList.add('active');
        
        // 添加明显的使用说明标记
        const header = panel.querySelector('.feature-panel-header');
        const usageLabel = document.createElement('div');
        usageLabel.className = 'usage-label';
        usageLabel.textContent = '使用说明';
        
        // 插入到面板头部
        if(header.firstElementChild) {
            header.insertBefore(usageLabel, header.firstElementChild);
        }
    });
}

// 添加页面加载动画
function addPageLoadAnimations() {
    const sections = document.querySelectorAll('.function-card');
    
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            section.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }, 100 + (index * 200));
    });
}

// 增强文件上传体验
function enhanceFileUploadExperience() {
    const fileUploadContainers = document.querySelectorAll('.file-upload-container');
    
    fileUploadContainers.forEach(container => {
        const fileInput = container.querySelector('input[type="file"]');
        const filePreviewContainer = container.querySelector('.file-preview-container');
        const fileTypeName = container.querySelector('.file-type-icon');
        const fileName = container.querySelector('.file-preview-name');
        const fileMeta = container.querySelector('.file-preview-meta');
        const changeFileBtn = container.querySelector('.change-file-btn');
        
        // 处理文件选择
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                displayFilePreview(this.files[0]);
            }
        });
        
        // 处理拖拽事件
        container.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('dragover');
        });
        
        container.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('dragover');
        });
        
        container.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                
                if (fileInput.files[0]) {
                    displayFilePreview(fileInput.files[0]);
                }
                
                // 触发change事件
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
        
        // 更换文件按钮事件
        if (changeFileBtn) {
            changeFileBtn.addEventListener('click', function(e) {
                e.preventDefault();
                fileInput.click();
            });
        }
        
        // 显示文件预览
        function displayFilePreview(file) {
            // 获取文件扩展名并设置类型图标
            const extension = file.name.split('.').pop().toLowerCase();
            fileTypeName.className = 'file-type-icon type-' + extension;
            
            // 设置文件名和大小
            fileName.textContent = file.name;
            
            // 格式化文件大小
            const fileSizeInMB = (file.size / (1024 * 1024)).toFixed(2);
            fileMeta.textContent = `${fileSizeInMB} MB · ${extension.toUpperCase()} 文件`;
            
            // 显示预览容器
            filePreviewContainer.style.display = 'block';
        }
        
        // 表单重置时清除预览
        const form = fileInput.closest('form');
        if (form) {
            form.addEventListener('reset', () => {
                filePreviewContainer.style.display = 'none';
            });
        }
    });
}

// 初始化页面
document.addEventListener('DOMContentLoaded', () => {
    // 检查登录状态
    checkLogin();
    
    // 设置当前用户名
    const currentUser = document.getElementById('currentUser');
    if (currentUser) {
        currentUser.textContent = localStorage.getItem('username');
    }

    // 添加登录表单事件监听器
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // 添加注册表单事件监听器
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }

    // 添加上传表单事件监听器
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', uploadVoice);
    }

    // 添加合成表单事件监听器
    const synthesisForm = document.getElementById('synthesisForm');
    if (synthesisForm) {
        synthesisForm.addEventListener('submit', synthesizeVoice);
    }

    // 添加课件处理表单事件监听器
    const coursewareForm = document.getElementById('coursewareForm');
    if (coursewareForm) {
        coursewareForm.addEventListener('submit', processCourseware);
    }

    // 添加声音置换表单事件监听器
    const voiceReplaceUploadForm = document.getElementById('voiceReplaceUploadForm');
    if (voiceReplaceUploadForm) {
        voiceReplaceUploadForm.addEventListener('submit', uploadVideoForVoiceReplacement);
    }
    
    const voiceReplaceAnalyzeForm = document.getElementById('voiceReplaceAnalyzeForm');
    if (voiceReplaceAnalyzeForm) {
        voiceReplaceAnalyzeForm.addEventListener('submit', analyzeVideoAudio);
    }
    
    const voiceReplaceSynthesizeForm = document.getElementById('voiceReplaceSynthesizeForm');
    if (voiceReplaceSynthesizeForm) {
        voiceReplaceSynthesizeForm.addEventListener('submit', synthesizeReplacementAudio);
    }

    // 添加管理员入口链接
    const header = document.querySelector('header');
    if (header && localStorage.getItem('isAdmin') === 'true' && !window.location.href.includes('admin.html')) {
        console.log('为管理员添加管理后台入口');
        const adminLink = document.createElement('a');
        adminLink.href = 'admin.html';
        adminLink.className = 'admin-link';
        adminLink.style.marginRight = '15px';
        adminLink.textContent = '管理后台';
        
        const userInfo = header.querySelector('.user-info');
        if (userInfo) {
            userInfo.insertBefore(adminLink, userInfo.firstChild);
        }
    }

    // 如果在主页面，加载声音列表并添加引导
    if (window.location.pathname.endsWith('index.html') || window.location.pathname === '/' || window.location.pathname.endsWith('/')) {
        loadVoiceList();
        
        // 初始化功能面板
        initFeaturePanels();
        
        // 美化界面元素
        enhanceFileInputs();
        addHelpTips();
        addWelcomeGuide();
        
        // 添加页面进入动画
        const sections = document.querySelectorAll('.feature-panel');
        sections.forEach((section, index) => {
            section.style.opacity = '0';
            section.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                section.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                section.style.opacity = '1';
                section.style.transform = 'translateY(0)';
            }, 200 + (index * 150));
        });
        
        // 点击"立即开始"按钮时，平滑滚动到功能区
        document.querySelector('a[href="#start-section"]').addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('start-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        
        // 页面加载完毕显示欢迎消息
        setTimeout(() => {
            showToast('欢迎使用语音合成系统！', 'info');
        }, 1000);
    }
    
    // 调用响应式设计辅助函数
    detectDeviceType();
    adjustFormElements();
    enhanceAudioPlayer();
    
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
        adjustFormElements();
        enhanceAudioPlayer();
    });
    
    // 添加新的交互增强
    enhanceFileInputs();
    enhanceResultDisplay();
    addPageLoadAnimations();
    
    // 添加文件上传增强体验
    enhanceFileUploadExperience();

    // 添加CSS样式以支持下载按钮容器
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .download-buttons-container {
            display: flex;
            flex-direction: row;
            gap: 12px;
            margin-top: 16px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .blue-download {
            background-color: #0071e3;
        }
        
        .blue-download:hover {
            background-color: #0077ed;
        }
        
        @media (max-width: 576px) {
            .download-buttons-container {
                flex-direction: column;
            }
        }
    `;
    document.head.appendChild(styleElement);
});

// 添加一些动态CSS
const dynamicStyles = document.createElement('style');
dynamicStyles.textContent = `
    .welcome-guide {
        background: rgba(255, 255, 255, 0.98);
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        padding: 0;
        margin-bottom: 30px;
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.4s ease, opacity 0.4s ease, transform 0.4s ease, margin-bottom 0.4s ease;
        opacity: 0;
        transform: translateY(-20px);
    }
    
    .welcome-guide.show {
        max-height: 400px;
        opacity: 1;
        transform: translateY(0);
    }
    
    .welcome-guide.hiding {
        max-height: 0;
        opacity: 0;
        margin-bottom: 0;
    }
    
    .welcome-content {
        padding: 30px;
    }
    
    .welcome-content h3 {
        font-size: 24px;
        margin-bottom: 16px;
        color: #0071e3;
    }
    
    .welcome-content ol {
        margin: 16px 0;
        padding-left: 24px;
    }
    
    .welcome-content li {
        margin-bottom: 8px;
    }
    
    .got-it-btn {
        margin-top: 16px;
    }
    
    .loading-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 50%;
        border-top-color: white;
        animation: spin 1s linear infinite;
        margin-right: 8px;
        vertical-align: middle;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .toast-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(255, 255, 255, 0.95);
        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        min-width: 280px;
        max-width: 320px;
        transform: translateX(120%);
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        z-index: 1000;
        backdrop-filter: blur(10px);
    }
    
    .toast-notification.show {
        transform: translateX(0);
    }
    
    .toast-notification .toast-icon {
        margin-right: 12px;
    }
    
    .toast-notification.success .toast-icon {
        color: #2ac769;
    }
    
    .toast-notification.error .toast-icon {
        color: #ff3b30;
    }
    
    .toast-notification.info .toast-icon {
        color: #0071e3;
    }
    
    .toast-notification .toast-message {
        font-size: 14px;
        color: #333;
    }
    
    .file-text-hint {
        margin-left: 10px;
        font-size: 15px;
        color: #86868b;
    }
    
    .file-selected {
        border-color: #2ac769 !important;
        background-color: rgba(42, 199, 105, 0.05) !important;
    }
    
    .file-size {
        color: #86868b;
        font-size: 13px;
    }
    
    @media (prefers-color-scheme: dark) {
        .welcome-guide {
            background: rgba(40, 40, 42, 0.98);
        }
        
        .toast-notification {
            background: rgba(40, 40, 42, 0.95);
        }
        
        .toast-notification .toast-message {
            color: #f5f5f7;
        }
    }
`;

document.head.appendChild(dynamicStyles);

// 添加更多动态CSS样式
const additionalStyles = document.createElement('style');
additionalStyles.textContent = `
    /* 功能面板动态效果 */
    .feature-panel-header {
        background-color: #fcfcfc;
        transition: all 0.3s ease;
    }
    
    .feature-panel.upload-panel .feature-panel-header {
        border-left: 4px solid #0071e3;
    }
    
    .feature-panel.synthesis-panel .feature-panel-header {
        border-left: 4px solid #5ac8fa;
    }
    
    .feature-panel.courseware-panel .feature-panel-header {
        border-left: 4px solid #2ac769;
    }
    
    .feature-panel-header::after {
        content: '⟩';
        position: absolute;
        right: 20px;
        transform: rotate(90deg);
        transition: transform 0.3s ease;
        font-size: 20px;
        color: var(--text-secondary);
    }
    
    .feature-panel.active .feature-panel-header::after {
        transform: rotate(-90deg);
    }
    
    .feature-panel-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.5s ease, padding 0.3s ease;
        padding-top: 0;
        padding-bottom: 0;
    }
    
    .feature-panel.active .feature-panel-content {
        max-height: 2000px; /* 足够大的值以容纳内容 */
        padding-top: 20px;
        padding-bottom: 30px;
    }
    
    .drag-over {
        border-color: var(--primary-color) !important;
        background-color: rgba(0, 113, 227, 0.05) !important;
        transform: scale(1.01);
    }
    
    @media (prefers-color-scheme: dark) {
        .feature-panel-header {
            background-color: #2a2a2c;
        }
        
        .feature-panel.upload-panel,
        .feature-panel.synthesis-panel,
        .feature-panel.courseware-panel {
            background: #1c1c1e !important;
        }
        
        .audio-player-container {
            background: #2c2c2e !重要;
        }
    }
    
    /* 文件上传反馈样式 */
    .upload-status {
        display: none;
        margin-top: 16px;
        animation: fadeIn 0.3s ease;
    }
    
    .file-selected-info {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background: rgba(42, 199, 105, 0.05);
        border-radius: var(--border-radius);
        border: 1px solid rgba(42, 199, 105, 0.2);
    }
    
    .file-icon {
        margin-right: 12px;
        color: var(--accent-color);
    }
    
    .file-details {
        flex: 1;
    }
    
    .file-name {
        font-weight: 600;
        margin-bottom: 4px;
        color: var(--text-primary);
        word-break: break-word;
    }
    
    .file-size {
        font-size: 12px;
        color: var(--text-secondary);
    }
    
    .file-selected {
        border-color: var(--accent-color);
    }
    
    .drag-over {
        background-color: rgba(0, 113, 227, 0.05);
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1);
    }
    
    .result-section {
        transition: all 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @media (prefers-color-scheme: dark) {
        .file-selected-info {
            background: rgba(42, 199, 105, 0.1);
            border-color: rgba(42, 199, 105, 0.3);
        }
    }
`;

document.head.appendChild(additionalStyles);