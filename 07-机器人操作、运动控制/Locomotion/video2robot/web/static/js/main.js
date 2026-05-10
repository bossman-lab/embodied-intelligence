/**
 * video2robot web frontend
 */

// Base prompt for robot motion retargeting
const BASE_PROMPT = `Full-body shot of a single adult humanoid subject, with the entire body visible from head to feet at all times.

The subject is wearing tight-fitting motion capture style clothing: a short-sleeve shirt and slim athletic pants.
No coat, no jacket, no robe, no cloak, no skirt, no loose clothing, no accessories.

Static camera, eye-level, neutral perspective.
The subject remains fully inside the frame throughout the entire video.

The scene takes place in a realistic indoor room environment.
The room has clearly visible walls, floor, and corners.
The boundary between the floor and the walls is clearly visible.
The floor plane is clearly defined and fully visible.
The background is NOT a seamless white backdrop, NOT a studio cyclorama, and NOT an infinite background.

The room resembles a simple laboratory, motion analysis room, or empty interior space.
Surfaces are plain but spatially well-defined.

Even, neutral indoor lighting with no dramatic shadows or highlights.
No cinematic effects.

Motion is biomechanically accurate and physically realistic.
Natural human joint limits, correct center-of-mass movement, realistic balance, gravity, inertia, and ground contact.
No exaggerated motion, no stylized animation.

No camera movement, no cuts, no slow motion, no motion blur.`;

// State
let currentProject = null;
let activeTasks = [];
let pollInterval = null;
let uiUpdateInterval = null;
let visualizationManuallyHidden = false;
let activeViserProject = null;
let viserStarting = false;
let viserFrameToken = null;
let viserFrameReady = false;
let viserReconnectAttempts = 0;

// Elements
const projectList = document.getElementById('project-list');
const newProjectForm = document.getElementById('new-project-form');
const taskStatus = document.getElementById('task-status');
const taskContent = document.getElementById('task-content');
const projectDetail = document.getElementById('project-detail');
const detailTitle = document.getElementById('detail-title');
const detailContent = document.getElementById('detail-content');
const detailActions = document.getElementById('detail-actions');
const detailBadges = document.getElementById('detail-badges');
const visualization = document.getElementById('visualization');
const viserFrame = document.getElementById('viser-frame');
const viserLoading = document.getElementById('viser-loading');

// API helpers
async function api(method, path, body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const res = await fetch(`/api${path}`, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.json();
}

function enqueueTask(task, extras = {}) {
    const merged = { ...task, ...extras };
    merged._localLastProgress = typeof merged.progress === 'number' ? merged.progress : 0;
    merged._localLastProgressAt = Date.now();
    // Local timer (increments every second)
    merged._localElapsed = 0;
    activeTasks.push(merged);
    return merged;
}

// Load projects
async function loadProjects() {
    try {
        const projects = await api('GET', '/projects');
        renderProjectList(projects);
    } catch (e) {
        projectList.innerHTML = `<div class="px-4 py-4 text-red-500 text-sm">${e.message}</div>`;
    }
}

function renderProjectList(projects) {
    if (projects.length === 0) {
        projectList.innerHTML = `<div class="px-4 py-8 text-center text-gray-500 text-sm">暂无项目</div>`;
        return;
    }

    projectList.innerHTML = projects.map(p => `
        <div class="project-item px-4 py-3 ${currentProject === p.name ? 'selected' : ''}"
             data-name="${p.name}" onclick="selectProject('${p.name}')">
            <div class="flex items-center justify-between">
                <span class="font-medium text-sm text-gray-900">${p.name}</span>
                <div class="flex gap-1">
                    ${p.has_video ? '<span class="badge badge-success">视频</span>' : '<span class="badge badge-pending">视频</span>'}
                    ${p.has_pose ? '<span class="badge badge-success">姿态</span>' : '<span class="badge badge-pending">姿态</span>'}
                    ${p.has_robot ? `<span class="badge badge-success">${p.robot_type || 'Unitree G1'}</span>` : ''}
                </div>
            </div>
            ${p.prompt ? `<p class="text-xs text-gray-500 mt-1 truncate-2">${escapeHtml(p.prompt.substring(0, 100))}</p>` : ''}
        </div>
    `).join('');
}

// Select project
async function selectProject(name) {
    if (currentProject !== name) {
        visualizationManuallyHidden = false;
        await stopCurrentVisualization({ silent: true });
    }
    currentProject = name;

    // Update list selection
    document.querySelectorAll('.project-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.name === name);
    });

    // Render task status for this project
    renderTaskStatus();

    // Load detail
    try {
        const detail = await api('GET', `/projects/${name}`);
        renderProjectDetail(detail);
        await handleProjectVisualization(detail);
    } catch (e) {
        detailContent.innerHTML = `<p class="text-red-500 text-sm">${e.message}</p>`;
    }
}

function renderProjectDetail(detail) {
    detailTitle.textContent = detail.name;
    detailActions.classList.remove('hidden');

    // Enable/disable buttons based on state
    document.getElementById('btn-extract-pose').disabled = !detail.has_video;
    document.getElementById('btn-retarget').disabled = !detail.has_pose;
    document.getElementById('btn-visualize').disabled = !detail.has_robot;

    // Status badges in header
    detailBadges.innerHTML = `
        ${detail.has_video ? '<span class="badge badge-success">视频</span>' : '<span class="badge badge-pending">视频</span>'}
        ${detail.has_pose ? '<span class="badge badge-success">姿态</span>' : '<span class="badge badge-pending">姿态</span>'}
        ${detail.has_robot ? `<span class="badge badge-success">${detail.robot_type || 'Unitree G1'}</span>` : ''}
    `;

    // Content area: prompt + video
    let html = '<div class="space-y-4">';

    // Prompt with expand/collapse
    if (detail.prompt) {
        html += `
            <div>
                <p id="prompt-text" class="text-sm text-gray-700 line-clamp-2">${escapeHtml(detail.prompt)}</p>
                <button id="btn-toggle-prompt" class="text-xs text-blue-600 hover:underline mt-1">展开</button>
            </div>
        `;
    }

    // Video preview
    if (detail.has_video) {
        html += `
            <video controls class="w-full bg-black rounded" style="max-height: 500px;">
                <source src="/api/files/video/${detail.name}" type="video/mp4">
            </video>
        `;
    } else {
        html += `<p class="text-gray-400 text-sm text-center py-12">暂无视频</p>`;
    }

    html += '</div>';
    detailContent.innerHTML = html;

    // Setup prompt toggle
    setupPromptToggle();
}

async function handleProjectVisualization(detail) {
    if (!detail.has_robot) {
        await stopCurrentVisualization({ silent: true });
        return;
    }
    if (visualizationManuallyHidden) {
        return;
    }
    await openVisualization(detail.name);
}

function setupPromptToggle() {
    const btn = document.getElementById('btn-toggle-prompt');
    const text = document.getElementById('prompt-text');
    if (!btn || !text) return;

    let expanded = false;
    btn.addEventListener('click', () => {
        expanded = !expanded;
        text.classList.toggle('line-clamp-2', !expanded);
        btn.textContent = expanded ? '收起' : '展开';
    });
}

// Mode toggle
document.querySelectorAll('input[name="input-mode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        const isPrompt = e.target.value === 'prompt';
        document.getElementById('prompt-section').classList.toggle('hidden', !isPrompt);
        document.getElementById('upload-section').classList.toggle('hidden', isPrompt);
    });
});

// Start pipeline
document.getElementById('btn-start-pipeline').addEventListener('click', async () => {
    const btn = document.getElementById('btn-start-pipeline');
    const mode = document.querySelector('input[name="input-mode"]:checked').value;

    btn.disabled = true;
    btn.textContent = '处理中...';

    await stopCurrentVisualization({ silent: true });

    // Reset UI
    currentProject = null;
    document.querySelectorAll('.project-item').forEach(el => el.classList.remove('selected'));

    detailTitle.textContent = '请选择项目';
    detailBadges.innerHTML = '';
    detailContent.innerHTML = '<p class="text-gray-500 text-sm">请在左侧选择项目</p>';
    detailActions.classList.add('hidden');

    visualization.classList.add('hidden');

    try {
        if (mode === 'prompt') {
            const action = document.getElementById('input-action').value.trim();
            const model = document.getElementById('input-model').value;
            const duration = parseInt(document.getElementById('input-duration').value);
            const robot = document.getElementById('input-robot').value;
            const staticCamera = isStaticCamera();

            if (!action) {
                alert('请输入动作描述');
                return;
            }

            // Create project
            const project = await api('POST', '/projects', {});
            currentProject = project.name;

            // Start video generation
            const videoParams = {
                project: project.name,
                model: model,
                duration: duration,
            };
            // Send action or raw_prompt based on base prompt toggle
            if (isBasePromptEnabled()) {
                videoParams.action = action;
            } else {
                videoParams.raw_prompt = action;
            }
            const task = await api('POST', '/pipeline/generate-video', videoParams);

            enqueueTask(task, { nextStep: 'pose', robot, staticCamera });
            startTaskPolling();

            // Refresh project list and select new project
            await loadProjects();
            await selectProject(project.name);

        } else {
            // Upload mode
            const fileInput = document.getElementById('input-video');
            const robot = document.getElementById('input-robot').value;
            const staticCamera = isStaticCamera();

            if (!fileInput.files.length) {
                alert('请选择视频文件');
                return;
            }

            // Create project
            const project = await api('POST', '/projects', {});
            currentProject = project.name;

            // Upload file
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const uploadRes = await fetch(`/api/files/upload/${project.name}`, {
                method: 'POST',
                body: formData,
            });

            if (!uploadRes.ok) {
                throw new Error('上传失败');
            }

            // Start pose extraction
            const task = await api('POST', '/pipeline/extract-pose', {
                project: project.name,
                static_camera: staticCamera,
            });

            enqueueTask(task, { nextStep: 'robot', robot, staticCamera });
            startTaskPolling();

            // Refresh project list and select new project
            await loadProjects();
            await selectProject(project.name);
        }

    } catch (e) {
        alert(`错误：${e.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = '开始执行流程';
    }
});

// Task polling
function startTaskPolling() {
    // Server polling (every 2 seconds)
    if (!pollInterval) {
        pollInterval = setInterval(pollTasks, 2000);
    }
    // Timer update (every 1 second)
    if (!uiUpdateInterval) {
        uiUpdateInterval = setInterval(tickTimer, 1000);
    }
}

function stopTaskPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    if (uiUpdateInterval) {
        clearInterval(uiUpdateInterval);
        uiUpdateInterval = null;
    }
}

function tickTimer() {
    // Increment local timer for running tasks
    for (const task of activeTasks) {
        if (task.status === 'running') {
            task._localElapsed = (task._localElapsed || 0) + 1;
        }
    }
    renderTaskStatus();
}

async function pollTasks() {
    if (activeTasks.length === 0) {
        stopTaskPolling();
        return;
    }

    for (let i = activeTasks.length - 1; i >= 0; i--) {
        const task = activeTasks[i];
        try {
            const updated = await api('GET', `/pipeline/tasks/${task.id}`);
            const previousProgress = typeof task.progress === 'number' ? task.progress : 0;
            const previousTimestamp = task._localLastProgressAt || Date.now();
            const localElapsed = task._localElapsed;
            Object.assign(task, updated);
            // Preserve local timer
            task._localElapsed = localElapsed || 0;
            if (typeof task.progress === 'number' && task.progress > previousProgress + 0.001) {
                task._localLastProgress = task.progress;
                task._localLastProgressAt = Date.now();
            } else if (!task._localLastProgressAt) {
                task._localLastProgressAt = previousTimestamp;
                task._localLastProgress = previousProgress;
            }

            if (updated.status === 'completed') {
                // Start next step
                if (task.nextStep === 'pose') {
                    const newTask = await api('POST', '/pipeline/extract-pose', {
                        project: task.project,
                        static_camera: task.staticCamera || false,
                    });
                    enqueueTask(newTask, { nextStep: 'robot', robot: task.robot, staticCamera: task.staticCamera });
                } else if (task.nextStep === 'robot') {
                    const newTask = await api('POST', '/pipeline/retarget', {
                        project: task.project,
                        robot_type: task.robot || 'unitree_g1',
                    });
                    enqueueTask(newTask, { nextStep: null });
                }
                activeTasks.splice(i, 1);
                loadProjects();
                if (currentProject === task.project) {
                    selectProject(task.project);
                }
            } else if (updated.status === 'failed') {
                activeTasks.splice(i, 1);
            }

        } catch (e) {
            console.error('Poll error:', e);
            // Remove task on 404 error
            if (e.message.includes('404')) {
                activeTasks.splice(i, 1);
            }
        }
    }

    renderTaskStatus();

    if (activeTasks.length === 0) {
        setTimeout(() => {
            taskStatus.classList.add('hidden');
        }, 3000);
    }
}

function renderTaskStatus() {
    // Filter tasks for current project
    const projectTasks = activeTasks.filter(t => t.project === currentProject);

    if (projectTasks.length === 0) {
        taskStatus.classList.add('hidden');
        return;
    }

    taskStatus.classList.remove('hidden');
    taskContent.innerHTML = projectTasks.map(t => {
        const rawProgress = typeof t.progress === 'number' ? t.progress : 0;
        const percent = Math.round(rawProgress * 100);
        const displayPercent = t.status === 'completed' ? 100 : percent;

        // Local timer display
        const elapsed = t._localElapsed > 0 ? formatTime(t._localElapsed) : '';
        const isRunning = t.status === 'running';

        return `
            <div class="task-item">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-sm font-medium">${getTaskTypeLabel(t.type)}</span>
                    <div class="flex items-center gap-2">
                        ${elapsed ? `<span class="text-xs text-gray-400">${elapsed}</span>` : ''}
                        <span class="text-sm font-bold text-blue-600">${displayPercent}%</span>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill ${isRunning ? 'animate-pulse' : ''}" style="width: ${displayPercent}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

function formatTime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function getTaskTypeLabel(type) {
    const labels = {
        'generate_video': '视频生成',
        'extract_pose': '姿态提取',
        'retarget': '机器人重定向',
    };
    return labels[type] || type;
}

function getStatusLabel(status) {
    const labels = {
        'pending': '等待中',
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
    };
    return labels[status] || status;
}

function getStatusBadgeClass(status) {
    const classes = {
        'pending': 'badge-pending',
        'running': 'badge-running',
        'completed': 'badge-success',
        'failed': 'badge-error',
    };
    return classes[status] || 'badge-pending';
}

// Action buttons
document.getElementById('btn-extract-pose').addEventListener('click', async () => {
    if (!currentProject) return;
    try {
        const staticCamera = isStaticCamera();
        const task = await api('POST', '/pipeline/extract-pose', {
            project: currentProject,
            static_camera: staticCamera,
        });
        enqueueTask(task, { nextStep: null, staticCamera });
        startTaskPolling();
        renderTaskStatus();
    } catch (e) {
        alert(`错误：${e.message}`);
    }
});

document.getElementById('btn-retarget').addEventListener('click', async () => {
    if (!currentProject) return;
    try {
        const task = await api('POST', '/pipeline/retarget', {
            project: currentProject,
        });
        enqueueTask(task, { nextStep: null });
        startTaskPolling();
        renderTaskStatus();
    } catch (e) {
        alert(`错误：${e.message}`);
    }
});

// Visualization controls
async function openVisualization(project, options = {}) {
    const { forceRestart = false } = options;
    if (!project) return;
    if (forceRestart && activeViserProject === project) {
        await stopCurrentVisualization({ silent: true });
    } else if (activeViserProject === project && viserFrameReady) {
        visualization.classList.remove('hidden');
        viserLoading.classList.add('hidden');
        return;
    }
    if (viserStarting) return;

    const btn = document.getElementById('btn-visualize');
    viserStarting = true;
    btn.disabled = true;
    btn.textContent = '启动中...';

    visualization.classList.remove('hidden');
    showViserLoading('正在启动 3D 可视化服务...');

    const requestedProject = project;

    try {
        const result = await api('POST', '/viser/start', {
            project,
            all_tracks: true,
            material_mode: getRobotAppearanceMode(),
        });

        if (currentProject !== requestedProject) {
            const stopProject = result.session?.project || requestedProject;
            await api('POST', '/viser/stop', { project: stopProject }).catch(() => {});
            return;
        }

        const session = result.session || {};
        activeViserProject = session.project || project;
        visualizationManuallyHidden = false;

        if (session.url) {
            setViserFrameSource(session.url);
        } else {
            showViserLoading('未获取到可视化地址', true);
        }
    } catch (e) {
        showViserLoading(e.message, true);
    } finally {
        btn.textContent = '可视化';
        btn.disabled = false;
        viserStarting = false;
    }
}

document.getElementById('btn-visualize').addEventListener('click', () => {
    visualizationManuallyHidden = false;
    if (currentProject) {
        openVisualization(currentProject);
    }
});

document.getElementById('btn-close-viser').addEventListener('click', async () => {
    visualizationManuallyHidden = true;
    await stopCurrentVisualization();
});

async function stopCurrentVisualization({ silent = false } = {}) {
    const project = activeViserProject;
    if (!project) {
        resetVisualizationFrame();
        return;
    }

    try {
        await api('POST', '/viser/stop', { project });
    } catch (e) {
        if (!silent) {
            console.error('Viser stop error:', e);
        }
    } finally {
        activeViserProject = null;
        resetVisualizationFrame();
    }
}

function showViserLoading(message, isError = false) {
    visualization.classList.remove('hidden');
    viserLoading.classList.remove('hidden');
    viserLoading.innerHTML = `<span class="${isError ? 'text-red-500' : 'text-gray-500'}">${message}</span>`;
}

function resetVisualizationFrame() {
    viserFrameToken = null;
    viserFrameReady = false;
    viserFrame.src = 'about:blank';
    viserLoading.classList.add('hidden');
    visualization.classList.add('hidden');
}

function setViserFrameSource(url) {
    if (!url) {
        showViserLoading('无法设置可视化地址', true);
        return;
    }

    const locationHost = window.location.hostname || 'localhost';
    if (url.includes('://0.0.0.0')) {
        const safeHost = locationHost === '0.0.0.0' ? '127.0.0.1' : locationHost;
        url = url.replace('://0.0.0.0', `://${safeHost}`);
    } else if (url.includes('://127.0.0.1') && locationHost && locationHost !== '127.0.0.1') {
        url = url.replace('://127.0.0.1', `://${locationHost}`);
    }

    viserFrameToken = url;
    viserFrameReady = false;
    viserReconnectAttempts = 0;
    showViserLoading('正在连接可视化服务...');
    viserFrame.src = url;
}

viserFrame.addEventListener('load', () => {
    if (!viserFrameToken) {
        return;
    }
    viserFrameReady = true;
    viserReconnectAttempts = 0;
    viserLoading.classList.add('hidden');
});

viserFrame.addEventListener('error', () => {
    if (!viserFrameToken) {
        return;
    }
    viserFrameReady = false;
    if (viserReconnectAttempts >= 2 || !currentProject) {
        viserLoading.classList.remove('hidden');
        viserLoading.innerHTML = '<span class="text-red-500">可视化连接失败，请点击“可视化”重试</span>';
        return;
    }
    viserReconnectAttempts += 1;
    viserLoading.classList.remove('hidden');
    viserLoading.innerHTML = '<span class="text-red-500">可视化连接中断，正在重连...</span>';
    setTimeout(async () => {
        try {
            const result = await api('POST', '/viser/start', {
                project: currentProject,
                all_tracks: true,
                material_mode: getRobotAppearanceMode(),
            });
            const session = result.session || {};
            if (session.url) {
                setViserFrameSource(session.url);
            }
        } catch (e) {
            viserLoading.innerHTML = `<span class="text-red-500">${e.message || '重连失败'}</span>`;
        }
    }, 1200);
});

// Helpers
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Base prompt toggle
const basePromptToggle = document.getElementById('toggle-base-prompt');
const basePromptDisplay = document.getElementById('base-prompt-display');
const basePromptText = document.getElementById('base-prompt-text');
const staticCameraToggle = document.getElementById('toggle-static-camera');

// Initial state (default: base prompt ON)
basePromptText.value = BASE_PROMPT;
basePromptDisplay.classList.remove('hidden');

basePromptToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        // Base prompt ON: show content, force static camera
        basePromptText.value = BASE_PROMPT;
        basePromptDisplay.classList.remove('hidden');
        staticCameraToggle.checked = true;
        staticCameraToggle.disabled = true;
    } else {
        // Base prompt OFF: hide content, enable camera toggle
        basePromptDisplay.classList.add('hidden');
        staticCameraToggle.disabled = false;
    }
});

// Helper functions
function isBasePromptEnabled() {
    return document.getElementById('toggle-base-prompt').checked;
}

function isStaticCamera() {
    return document.getElementById('toggle-static-camera').checked;
}

function getRobotAppearanceMode() {
    const el = document.getElementById('input-robot-appearance');
    if (!el) return 'color';
    return el.value === 'metal' ? 'metal' : 'color';
}

const robotAppearanceSelect = document.getElementById('input-robot-appearance');
if (robotAppearanceSelect) {
    robotAppearanceSelect.addEventListener('change', async () => {
        if (!currentProject || !activeViserProject) return;
        visualizationManuallyHidden = false;
        await openVisualization(currentProject, { forceRestart: true });
    });
}

// Init
loadProjects();
