// 检查是否是管理员
async function checkAdminAccess() {
    try {
        // 添加调试日志
        const token = localStorage.getItem('token');
        const isAdmin = localStorage.getItem('isAdmin') === 'true';
        console.log('管理页面检查管理员权限:', {
            'token存在': !!token,
            'token长度': token ? token.length : 0,
            'isAdmin标记值': localStorage.getItem('isAdmin'),
            'isAdmin转换为布尔值': isAdmin
        });
        
        // 发送请求到服务器验证
        console.log('正在向服务器发送管理员验证请求...');
        const response = await fetch('/api/admin/check', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        console.log('服务器响应状态:', response.status);
        
        if (response.ok) {
            // 解析响应数据
            const data = await response.json();
            console.log('服务器响应数据:', data);
            
            // 更新本地存储
            localStorage.setItem('isAdmin', 'true');
            console.log('管理员权限验证成功，已更新本地存储');
        } else {
            // 尝试获取错误信息
            try {
                const errorData = await response.json();
                console.error('管理员验证失败:', errorData);
                localStorage.removeItem('isAdmin');
                alert('您没有管理员权限: ' + (errorData.detail || ''));
            } catch (parseError) {
                console.error('无法解析错误响应:', parseError);
                localStorage.removeItem('isAdmin');
                alert('您没有管理员权限');
            }
            window.location.href = 'index.html';
        }
    } catch (error) {
        console.error('管理员权限验证异常:', error);
        localStorage.removeItem('isAdmin');
        alert('验证管理员权限时出现错误');
        window.location.href = 'login.html';
    }
}

// 图表颜色配置
const chartColors = {
    cpu: {
        backgroundColor: 'rgba(0, 113, 227, 0.1)',
        borderColor: 'rgba(0, 113, 227, 0.8)'
    },
    memory: {
        backgroundColor: 'rgba(42, 199, 105, 0.1)',
        borderColor: 'rgba(42, 199, 105, 0.8)'
    },
    disk: {
        backgroundColor: 'rgba(255, 159, 10, 0.1)',
        borderColor: 'rgba(255, 159, 10, 0.8)'
    },
    gpu: {
        backgroundColor: 'rgba(76, 175, 80, 0.1)',
        borderColor: 'rgba(76, 175, 80, 0.8)'
    }
};

// 创建资源监控图表
let cpuChart, memoryChart, diskChart, gpuChart;
let chartData = {
    cpu: {
        labels: Array(60).fill(''),
        datasets: [{
            label: 'CPU使用率',
            data: Array(60).fill(null),
            backgroundColor: chartColors.cpu.backgroundColor,
            borderColor: chartColors.cpu.borderColor,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0.3,
            fill: true
        }]
    },
    memory: {
        labels: Array(60).fill(''),
        datasets: [{
            label: '内存使用率',
            data: Array(60).fill(null),
            backgroundColor: chartColors.memory.backgroundColor,
            borderColor: chartColors.memory.borderColor,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0.3,
            fill: true
        }]
    },
    disk: {
        labels: Array(60).fill(''),
        datasets: [{
            label: '磁盘使用率',
            data: Array(60).fill(null),
            backgroundColor: chartColors.disk.backgroundColor,
            borderColor: chartColors.disk.borderColor,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0.3,
            fill: true
        }]
    },
    gpu: {
        labels: Array(60).fill(''),
        datasets: [{
            label: 'GPU显存使用率',
            data: Array(60).fill(null),
            backgroundColor: chartColors.gpu.backgroundColor,
            borderColor: chartColors.gpu.borderColor,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 3,
            tension: 0.3,
            fill: true
        }]
    }
};

// 初始化图表
function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    callback: function(value) {
                        return value + '%';
                    }
                }
            },
            x: {
                display: false
            }
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.raw + '%';
                    }
                }
            }
        },
        animation: {
            duration: 500
        }
    };

    // 创建CPU图表
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: chartData.cpu,
        options: chartOptions
    });

    // 创建内存图表
    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: chartData.memory,
        options: chartOptions
    });

    // 创建磁盘图表
    const diskCtx = document.getElementById('diskChart').getContext('2d');
    diskChart = new Chart(diskCtx, {
        type: 'line',
        data: chartData.disk,
        options: chartOptions
    });
    
    // 创建GPU图表
    const gpuCtx = document.getElementById('gpuChart').getContext('2d');
    gpuChart = new Chart(gpuCtx, {
        type: 'line',
        data: chartData.gpu,
        options: chartOptions
    });

    // 用户增长趋势图表
    const growthCtx = document.getElementById('userGrowthChart').getContext('2d');
    window.userGrowthChart = new Chart(growthCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '新增用户数',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }, {
                label: '增长率(%)',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1,
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '新增用户数'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '增长率(%)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });

    // 用户身份分布图表
    const roleCtx = document.getElementById('userRoleChart').getContext('2d');
    window.userRoleChart = new Chart(roleCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// 更新图表数据
function updateCharts(cpuUsage, memoryUsage, diskUsage, gpuUsage) {
    // 添加新数据
    chartData.cpu.datasets[0].data.push(cpuUsage);
    chartData.cpu.datasets[0].data.shift();
    
    chartData.memory.datasets[0].data.push(memoryUsage);
    chartData.memory.datasets[0].data.shift();
    
    chartData.disk.datasets[0].data.push(diskUsage);
    chartData.disk.datasets[0].data.shift();
    
    chartData.gpu.datasets[0].data.push(gpuUsage);
    chartData.gpu.datasets[0].data.shift();
    
    // 更新图表
    cpuChart.update();
    memoryChart.update();
    diskChart.update();
    gpuChart.update();
}

// 加载统计数据
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/admin/stats', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const stats = await response.json();
            console.log('获取到系统统计数据:', stats);
            
            // 更新统计数字
            document.getElementById('totalUsers').textContent = stats.users_count || '0';
            document.getElementById('totalVoices').textContent = stats.voices_count || '0';
            document.getElementById('totalCoursewares').textContent = stats.coursewares_count || '0';
            document.getElementById('totalSynthesisCount').textContent = stats.total_synthesis_count || '0';
            
            // 更新合成次数详情
            document.getElementById('voiceSynthesisCount').textContent = stats.voice_synthesis_count || '0';
            document.getElementById('coursewareSynthesisCount').textContent = stats.courseware_synthesis_count || '0';
            
            // 更新系统状态
            if (stats.system_status) {
                // CPU信息
                document.getElementById('cpuUsage').textContent = stats.system_status.cpu.usage_str;
                document.getElementById('cpuDetails').textContent = `核心数: ${stats.system_status.cpu.cores} (物理: ${stats.system_status.cpu.physical_cores})`;
                
                // 内存信息
                document.getElementById('memoryUsage').textContent = stats.system_status.memory.usage_str;
                document.getElementById('memoryDetails').textContent = `${stats.system_status.memory.used_str} / ${stats.system_status.memory.total_str}`;
                
                // 磁盘信息
                document.getElementById('diskUsage').textContent = stats.system_status.disk.usage_str;
                document.getElementById('diskDetails').textContent = `${stats.system_status.disk.used_str} / ${stats.system_status.disk.total_str}`;
                
                // GPU显存信息
                const gpuMemory = stats.system_status.gpu_memory;
                if (gpuMemory && gpuMemory.available) {
                    document.getElementById('gpuUsage').textContent = gpuMemory.usage_str;
                    document.getElementById('gpuDetails').textContent = 
                        `${gpuMemory.memory_used_str} / ${gpuMemory.memory_total_str}`;
                    
                    // 更新详细GPU信息
                    updateGpuDetailedInfo(gpuMemory);
                    
                    // 更新图表
                    updateCharts(
                        stats.system_status.cpu.usage,
                        stats.system_status.memory.usage,
                        stats.system_status.disk.usage,
                        gpuMemory.usage
                    );
                } else {
                    document.getElementById('gpuUsage').textContent = '不可用';
                    document.getElementById('gpuDetails').textContent = gpuMemory?.message || '未检测到GPU';
                    document.getElementById('gpuDetailedInfo').innerHTML = 
                        '<div class="no-gpu-message">系统未检测到可用的GPU设备</div>';
                    
                    // 更新图表（GPU为0）
                    updateCharts(
                        stats.system_status.cpu.usage,
                        stats.system_status.memory.usage,
                        stats.system_status.disk.usage,
                        0
                    );
                }
                
                // 运行时间
                document.getElementById('uptime').textContent = stats.system_status.uptime;
            }

            // 加载用户增长统计数据
            await loadUserGrowthStats();
            
            // 加载用户身份统计数据
            await loadUserRoleStats();
        } else {
            console.error('获取统计数据失败:', response.status);
            document.querySelectorAll('.stat-value').forEach(el => {
                el.textContent = '获取失败';
            });
        }
    } catch (error) {
        console.error('加载统计数据出错:', error);
        document.querySelectorAll('.stat-value').forEach(el => {
            el.textContent = '获取失败';
        });
    }
}

// 更新GPU详细信息
function updateGpuDetailedInfo(gpuMemory) {
    const gpuDetailedInfo = document.getElementById('gpuDetailedInfo');
    
    if (!gpuMemory || !gpuMemory.available || !gpuMemory.gpus) {
        gpuDetailedInfo.innerHTML = '<div class="no-gpu-message">无可用GPU信息</div>';
        return;
    }
    
    let html = '';
    
    // 添加GPU数量信息
    html += `<div class="gpu-item">
                <span class="gpu-label">可用GPU数量</span>
                <span class="gpu-value">${gpuMemory.gpu_count}</span>
             </div>`;
    
    // 添加每个GPU的详细信息
    for (const gpu of gpuMemory.gpus) {
        html += `
            <div class="gpu-item">
                <span class="gpu-label">GPU ${gpu.index}</span>
                <span class="gpu-value">${gpu.usage_str} (${gpu.memory_used_str} / ${gpu.memory_total_str})</span>
            </div>
        `;
    }
    
    gpuDetailedInfo.innerHTML = html;
}

// 加载系统资源监控数据
async function loadSystemMonitor() {
    try {
        const response = await fetch('/api/admin/system-monitor', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const monitorData = await response.json();
            
            // 更新图表
            updateCharts(
                monitorData.cpu_usage,
                monitorData.memory_usage,
                monitorData.disk_usage,
                monitorData.gpu_usage
            );
        }
    } catch (error) {
        console.error('加载系统监控数据出错:', error);
    }
}

// 调整表格显示以适应小屏幕
function adjustTableForSmallScreens() {
    const userTable = document.getElementById('userTable');
    if (!userTable) return;
    
    const tableWrapper = userTable.parentElement;
    
    // 检测屏幕宽度
    if (window.innerWidth <= 768) {
        tableWrapper.style.overflowX = 'auto';
        userTable.style.minWidth = '600px';
        
        // 调整操作按钮
        const actionButtons = document.querySelectorAll('.user-action-btn');
        actionButtons.forEach(button => {
            button.style.padding = '6px 10px';
            button.style.fontSize = '14px';
        });
    } else {
        userTable.style.minWidth = 'auto';
        
        // 恢复操作按钮
        const actionButtons = document.querySelectorAll('.user-action-btn');
        actionButtons.forEach(button => {
            button.style.padding = '';
            button.style.fontSize = '';
        });
    }
}

// 调整模态框大小
function adjustModalSize() {
    const modals = document.querySelectorAll('.modal-content');
    
    modals.forEach(modal => {
        if (window.innerWidth <= 768) {
            modal.style.width = '90%';
            modal.style.margin = '10% auto';
        } else {
            modal.style.width = '60%';
            modal.style.margin = '5% auto';
        }
    });
}

// 加载用户列表
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const users = await response.json();
            const tableBody = document.getElementById('userTableBody');
            tableBody.innerHTML = '';

            users.forEach(user => {
                const row = document.createElement('tr');
                
                // 用户ID
                const idCell = document.createElement('td');
                idCell.textContent = user.id;
                row.appendChild(idCell);
                
                // 用户名
                const usernameCell = document.createElement('td');
                usernameCell.textContent = user.username;
                if (user.is_admin) {
                    const adminBadge = document.createElement('span');
                    adminBadge.textContent = '管理员';
                    adminBadge.className = 'badge badge-admin';
                    usernameCell.appendChild(adminBadge);
                }
                // 为system用户添加标识
                if (user.username === 'system') {
                    const systemBadge = document.createElement('span');
                    systemBadge.textContent = '系统账户';
                    systemBadge.className = 'badge badge-system';
                    usernameCell.appendChild(systemBadge);
                }
                row.appendChild(usernameCell);
                
                // 创建时间
                const createdAtCell = document.createElement('td');
                const date = new Date(user.created_at);
                createdAtCell.textContent = date.toLocaleString('zh-CN');
                row.appendChild(createdAtCell);
                
                // 声音数量 - 确保正确处理声音数量数据
                const voicesCountCell = document.createElement('td');
                
                // 如果后端直接返回voices_count字段，则使用该字段
                if (user.voices_count !== undefined) {
                    voicesCountCell.textContent = user.voices_count;
                }
                // 如果后端返回的是voices数组，则使用数组长度
                else if (user.voices && Array.isArray(user.voices)) {
                    voicesCountCell.textContent = user.voices.length;
                }
                // 如果有voice_count字段(单数形式)
                else if (user.voice_count !== undefined) {
                    voicesCountCell.textContent = user.voice_count;
                }
                // 后备选项，显示0
                else {
                    voicesCountCell.textContent = '0';
                    console.warn(`用户 ${user.username} (ID: ${user.id}) 没有声音数量信息`);
                }
                
                row.appendChild(voicesCountCell);
                
                // 操作按钮
                const actionCell = document.createElement('td');
                
                // 编辑按钮
                const editButton = document.createElement('button');
                editButton.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                    </svg>
                    编辑
                `;
                editButton.className = 'user-action-btn edit-btn';
                editButton.onclick = () => showEditUserModal(user);
                
                // 系统用户不能编辑
                if (user.username === 'system') {
                    editButton.disabled = true;
                    editButton.title = '系统用户不可编辑';
                    editButton.style.opacity = '0.5';
                    editButton.style.cursor = 'not-allowed';
                }
                actionCell.appendChild(editButton);
                
                // 删除按钮
                const deleteButton = document.createElement('button');
                deleteButton.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                    删除
                `;
                deleteButton.className = 'user-action-btn delete-btn';
                
                // 系统用户不能删除
                if (user.username === 'system') {
                    deleteButton.disabled = true;
                    deleteButton.title = '系统用户不可删除';
                    deleteButton.style.opacity = '0.5';
                    deleteButton.style.cursor = 'not-allowed';
                } else {
                    deleteButton.onclick = () => deleteUser(user.id, user.username);
                }
                actionCell.appendChild(deleteButton);
                
                row.appendChild(actionCell);
                
                tableBody.appendChild(row);
            });
        } else {
            const error = await response.json();
            throw new Error(error.detail || '获取用户列表失败');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        document.querySelector('#usersTable tbody').innerHTML = `
            <tr><td colspan="5">
                <div class="error-message">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff3b30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    加载用户数据失败: ${error.message}
                </div>
            </td></tr>
        `;
    }
}

// 加载声音数据
function loadVoiceData() {
    const token = localStorage.getItem('token');
    fetch('/api/admin/voices', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('获取声音数据失败');
        }
        return response.json();
    })
    .then(voices => {
        const tbody = document.querySelector('#voicesTable tbody');
        tbody.innerHTML = '';
        
        if (voices.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="6" style="text-align: center; padding: 20px;">暂无声音数据</td></tr>
            `;
            return;
        }
        
        voices.forEach(voice => {
            const row = document.createElement('tr');
            
            // 格式化日期
            const createdAt = new Date(voice.created_at).toLocaleString();
            
            // 修复所有者名称显示逻辑
            let ownerUsername = '未知';
            
            // 如果是预置声音或声音属于system用户，显示"system"
            if (voice.is_preset || (voice.user_id === 1)) {
                ownerUsername = 'system';
            }
            // 使用owner_username字段（后端提供）
            else if (voice.owner_username) {
                ownerUsername = voice.owner_username;
            }
            // 备选：从voice.owner对象获取username
            else if (voice.owner && voice.owner.username) {
                ownerUsername = voice.owner.username;
            }
            
            row.innerHTML = `
                <td>${voice.id}</td>
                <td>${voice.name || '未命名'}</td>
                <td>${ownerUsername}</td>
                <td>${voice.is_preset ? '<span class="badge badge-admin">是</span>' : '否'}</td>
                <td>${createdAt}</td>
                <td>
                    <button class="user-action-btn delete-btn" 
                            ${voice.is_preset || ownerUsername === 'system' ? 'disabled title="预置声音不可删除" style="opacity:0.5;cursor:not-allowed;"' : ''}
                            onclick="deleteVoice(${voice.id}, '${voice.name || '未命名'}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                        删除
                    </button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    })
    .catch(error => {
        console.error('Error loading voices:', error);
        document.querySelector('#voicesTable tbody').innerHTML = `
            <tr><td colspan="6">
                <div class="error-message">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff3b30" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    加载声音数据失败: ${error.message}
                </div>
            </td></tr>
        `;
    });
}

// 删除声音
function deleteVoice(voiceId, voiceName) {
    if (confirm(`确定要删除声音 "${voiceName}" 吗？此操作将同时删除使用该声音的所有课件，且不可撤销。`)) {
        const token = localStorage.getItem('token');
        
        // 显示加载状态
        document.querySelector('#voicesTable tbody').innerHTML = `
            <tr><td colspan="6">
                <div class="loading-indicator">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                    删除声音中，请稍候...
                </div>
            </td></tr>
        `;
        
        fetch(`/api/admin/voices/${voiceId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || '删除声音失败');
                });
            }
            return response.json();
        })
        .then(data => {
            alert('声音已成功删除');
            loadVoiceData();  // 重新加载声音数据
        })
        .catch(error => {
            console.error('Error deleting voice:', error);
            alert('删除声音失败: ' + error.message);
            loadVoiceData();  // 恢复显示
        });
    }
}

// 显示添加用户模态框
function showAddUserModal() {
    document.getElementById('addUserForm').reset();
    document.getElementById('addUserModal').style.display = 'block';
    adjustModalSize(); // 调整模态框大小
}

// 显示编辑用户模态框
function showEditUserModal(user) {
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUsername').value = user.username;
    document.getElementById('editPassword').value = '';
    document.getElementById('editIsAdmin').checked = user.is_admin;
    document.getElementById('editUserModal').style.display = 'block';
    adjustModalSize(); // 调整模态框大小
}

// 关闭模态框
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 添加新用户
async function addUser(event) {
    event.preventDefault();
    
    const username = document.getElementById('newUsername').value;
    const password = document.getElementById('newPassword').value;
    const isAdmin = document.getElementById('isAdmin').checked;

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        // 明确传递 'true' 或 'false' 字符串，确保服务器端正确解析布尔值
        formData.append('is_admin', isAdmin ? 'true' : 'false');

        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });

        if (response.ok) {
            alert('添加用户成功！');
            closeModal('addUserModal');
            loadUsers();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || '添加用户失败');
        }
    } catch (error) {
        console.error('Error adding user:', error);
        alert('添加用户失败: ' + error.message);
    }
}

// 编辑用户
async function editUser(event) {
    event.preventDefault();
    
    const userId = document.getElementById('editUserId').value;
    const username = document.getElementById('editUsername').value;
    const password = document.getElementById('editPassword').value;
    const isAdmin = document.getElementById('editIsAdmin').checked;

    try {
        const formData = new FormData();
        formData.append('username', username);
        if (password) {
            formData.append('password', password);
        }
        // 明确传递 'true' 或 'false' 字符串，确保服务器端正确解析布尔值
        formData.append('is_admin', isAdmin ? 'true' : 'false');
        
        console.log(`提交表单数据: userId=${userId}, username=${username}, is_admin=${isAdmin ? 'true' : 'false'}`);

        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
        });

        if (response.ok) {
            alert('更新用户成功！');
            closeModal('editUserModal');
            loadUsers();
        } else {
            let errorDetail = '更新用户失败';
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorDetail;
            } catch (parseError) {
                console.error('解析错误响应失败:', parseError);
            }
            throw new Error(errorDetail);
        }
    } catch (error) {
        console.error('Error updating user:', error);
        alert('更新用户失败: ' + error.message);
    }
}

// 删除用户
async function deleteUser(userId, username) {
    if (!confirm(`确定要删除用户 "${username}" 吗？用户的所有声音数据也将被删除！`)) {
        return;
    }

    try {
        // 显示加载状态
        document.querySelector('#usersTable tbody').innerHTML = `
            <tr><td colspan="5">
                <div class="loading-indicator">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                    删除用户中，请稍候...
                </div>
            </td></tr>
        `;

        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            showToast('删除用户成功！', 'success');
            loadUsers();
            loadVoiceData(); // 同时刷新声音列表，因为可能有级联删除
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || '删除用户失败');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showToast('删除用户失败: ' + error.message, 'error');
        loadUsers(); // 恢复显示
    }
}

// 显示提示消息
function showToast(message, type = 'info') {
    // 仅在main.js未提供此函数时添加
    if (typeof window.showToast !== 'function') {
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
                icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                break;
            case 'error':
                icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                break;
            default:
                icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V12M12 16H12.01M22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
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
    } else {
        // 如果main.js已提供，则使用它
        window.showToast(message, type);
    }
}

// 加载用户增长统计数据
async function loadUserGrowthStats() {
    try {
        const response = await fetch('/api/admin/user-growth-stats', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            
            // 更新图表数据
            window.userGrowthChart.data.labels = data.map(item => item.date);
            window.userGrowthChart.data.datasets[0].data = data.map(item => item.new_users);
            window.userGrowthChart.data.datasets[1].data = data.map(item => item.growth_rate);
            window.userGrowthChart.update();
        }
    } catch (error) {
        console.error('加载用户增长统计数据出错:', error);
    }
}

// 加载用户身份统计数据
async function loadUserRoleStats() {
    try {
        const response = await fetch('/api/admin/user-role-stats', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            
            // 更新图表数据
            window.userRoleChart.data.labels = data.map(item => item.role);
            window.userRoleChart.data.datasets[0].data = data.map(item => item.count);
            window.userRoleChart.update();
        }
    } catch (error) {
        console.error('加载用户身份统计数据出错:', error);
    }
}

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查登录状态
    checkLogin();
    
    // 检查管理员权限
    checkAdminAccess();
    
    // 设置当前用户名
    const currentUser = document.getElementById('currentUser');
    if (currentUser) {
        currentUser.textContent = localStorage.getItem('username');
    }
    
    // 初始化图表
    initCharts();
    
    // 加载统计数据
    loadDashboardStats();
    
    // 加载用户列表
    loadUsers();
    
    // 加载声音数据
    loadVoiceData();
    
    // 添加用户表单事件监听
    document.getElementById('addUserForm').addEventListener('submit', addUser);
    
    // 编辑用户表单事件监听
    document.getElementById('editUserForm').addEventListener('submit', editUser);
    
    // 关闭模态框
    window.onclick = function(event) {
        const addModal = document.getElementById('addUserModal');
        const editModal = document.getElementById('editUserModal');
        
        if (event.target === addModal) {
            addModal.style.display = 'none';
        } else if (event.target === editModal) {
            editModal.style.display = 'none';
        }
    };
    
    // 调用响应式设计辅助函数
    adjustTableForSmallScreens();
    adjustModalSize();
    
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
        adjustTableForSmallScreens();
        adjustModalSize();
    });
    
    // 添加标签切换功能
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 移除所有标签的活动状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // 隐藏所有内容
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 激活当前标签
            this.classList.add('active');
            
            // 显示对应内容
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // 自动刷新统计数据
    setInterval(loadDashboardStats, 60000); // 每分钟刷新一次
    
    // 自动刷新系统监控数据
    setInterval(loadSystemMonitor, 1000); // 每秒刷新一次
});
