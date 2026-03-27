// API Client for Nyx AI Backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Helper to get auth token
const getToken = () => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('token')
    }
    return null
}

// Generic fetch wrapper
async function fetchApi<T>(
    endpoint: string,
    options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    const token = getToken()

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    // 超时优先级：options.timeoutMs > 接口特定值 > 默认 30 秒
    // 图片状态轮询 8 秒，文生图启动 30 秒，其他 30 秒（Supabase 孟买节点冷启动可达 3-5s）
    const isImageStatus = endpoint.includes('/image-status/')
    const isGenerateImage = endpoint.includes('/generate-image/')
    const defaultTimeout = isImageStatus ? 8000 : isGenerateImage ? 30000 : 30000
    const timeoutMs = options.timeoutMs ?? defaultTimeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    try {
        const response = await fetch(url, {
            ...options,
            headers,
            signal: controller.signal,
        })

        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('token')
                // 使用 Next.js 路由而非强制刷新，避免打断其他页面渲染
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('auth:logout'))
                }
            }
            const error = await response.json().catch(() => ({ detail: '请求失败' }))
            throw new Error(error.detail || `HTTP ${response.status}`)
        }

        return response.json()
    } catch (error) {
        // 处理超时取消的错误，转换为友好的错误信息
        if (error instanceof Error && error.name === 'AbortError') {
            throw new Error('请求超时，请稍后重试')
        }
        throw error
    } finally {
        clearTimeout(timeoutId)
    }
}

// Types matching backend models
export interface User {
    id: number | string
    username: string
    email?: string
    credits?: number
    totalEarned?: number
    totalSpent?: number
}

export interface CharacterState {
    name: string
    type: 'string' | 'number'
    value: string | number
    defaultValue: string | number
    description: string
}

export interface Character {
    id: string
    name: string
    title?: string
    description: string
    avatar?: string
    tags: string[]
    visibility: 'public' | 'private'
    isSystem: boolean
    creatorId: string
    personality: string
    userRole: string
    scene: string
    greeting: string
    states: CharacterState[]
    storyline: string
    worldSetting: string
    appearance: string
    artStyle: string
    initialClothing: string
    appearanceTags: string[]
    voiceRef?: string
    dialogueCount: number
    createdAt: string
    plot_milestones?: string
}

export interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: string
    imageUrl?: string
}

export interface ChatSession {
    characterId: string
    messages: Message[]
    currentStates: CharacterState[]
}

// Auth API
export const authApi = {
    register: (data: { username: string; password: string; confirm_password: string }) =>
        fetchApi<{ success: boolean; message: string; user_id: number; username: string }>('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    login: (data: { username: string; password: string }) =>
        fetchApi<{ access_token: string; token_type: string; user_id: number; username: string; email?: string; is_admin: boolean; credits: number; total_earned: number; total_spent: number }>('/auth/login', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    getMe: () =>
        fetchApi<{ success: boolean; data: User }>('/auth/me'),

    updateMe: (data: { username?: string; email?: string }) =>
        fetchApi<{ success: boolean; message: string; data: { id: number; username: string; email: string | null } }>('/auth/me', {
            method: 'PATCH',
            body: JSON.stringify(data),
        }),

    changePassword: (data: { old_password: string; new_password: string }) =>
        fetchApi<{ success: boolean; message: string }>('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    getStats: () =>
        fetchApi<{ success: boolean; data: { total_roles: number; total_chats: number; total_messages: number } }>('/auth/stats'),
}

// ===== 字段映射：后端 snake_case ↔ 前端 camelCase =====

// 后端 RoleResponse → 前端 Character
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapBackendRole(data: any): Character {
    const parseTags = (val: unknown): string[] => {
        if (!val) return []
        if (Array.isArray(val)) return val
        if (typeof val === 'string') return val.split(',').map((t: string) => t.trim()).filter(Boolean)
        return []
    }
    return {
        id: String(data.id),
        name: data.name || '',
        title: data.title || undefined,
        description: data.public_summary || '',
        avatar: data.public_avatar || undefined,
        tags: parseTags(data.tags),
        visibility: data.visibility || 'public',
        isSystem: data.is_system || false,
        creatorId: String(data.user_id || ''),
        personality: data.persona || '',
        userRole: data.user_persona || '',
        scene: data.scenario || '',
        greeting: data.greeting || '',
        states: [],
        storyline: data.storyline || '',
        worldSetting: data.world_setting || '',
        appearance: data.appearance_tags || '',
        artStyle: data.image_style || '',
        initialClothing: data.clothing_state || '',
        appearanceTags: parseTags(data.appearance_tags),
        voiceRef: data.voice_reference_id || undefined,
        dialogueCount: data.state_count || 0,
        createdAt: data.created_at || '',
        plot_milestones: data.plot_milestones || undefined,
    }
}

// 前端 Character → 后端 snake_case
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapCharacterToBackend(char: Partial<Character>): Record<string, any> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result: Record<string, any> = {}
    if (char.name !== undefined) result.name = char.name
    if (char.title !== undefined) result.title = char.title
    if (char.description !== undefined) result.public_summary = char.description
    if (char.avatar !== undefined) result.public_avatar = char.avatar
    if (char.tags !== undefined) {
        result.tags = Array.isArray(char.tags) ? char.tags.join(',') : char.tags
    }
    if (char.visibility !== undefined) result.visibility = char.visibility
    if (char.personality !== undefined) result.persona = char.personality
    if (char.userRole !== undefined) result.user_persona = char.userRole
    if (char.scene !== undefined) result.scenario = char.scene
    if (char.greeting !== undefined) result.greeting = char.greeting
    if (char.states !== undefined) result.states = char.states
    if (char.storyline !== undefined) result.storyline = char.storyline
    if (char.worldSetting !== undefined) result.world_setting = char.worldSetting
    if (char.appearance !== undefined) result.appearance_tags = char.appearance
    if (char.artStyle !== undefined) result.image_style = char.artStyle
    if (char.initialClothing !== undefined) result.clothing_state = char.initialClothing
    if (char.voiceRef !== undefined) result.voice_reference_id = char.voiceRef
    if (char.plot_milestones !== undefined) result.plot_milestones = char.plot_milestones
    return result
}

// Characters API
export const charactersApi = {
    getList: async (mode: 'public' | 'my' = 'public') => {
        const res = await fetchApi<{ success: boolean; data: unknown[]; is_logged_in: boolean }>(`/roles?mode=${mode}`)
        return {
            success: res.success,
            data: res.data.map(mapBackendRole),
            is_logged_in: res.is_logged_in,
        }
    },

    getById: async (id: string) => {
        const data = await fetchApi<unknown>(`/roles/${id}`)
        return mapBackendRole(data)
    },

    create: async (data: Partial<Character>) => {
        const backendData = mapCharacterToBackend(data)
        const res = await fetchApi<unknown>('/roles', {
            method: 'POST',
            body: JSON.stringify(backendData),
        })
        const character = mapBackendRole(res)
        return { success: true, data: character }
    },

    update: async (id: string, data: Partial<Character>) => {
        const backendData = mapCharacterToBackend(data)
        const res = await fetchApi<unknown>(`/roles/${id}`, {
            method: 'PUT',
            body: JSON.stringify(backendData),
        })
        const character = mapBackendRole(res)
        return { success: true, data: character }
    },

    delete: (id: string) =>
        fetchApi<{ success: boolean }>(`/roles/${id}`, {
            method: 'DELETE',
        }),

    generate: (description: string) =>
        fetchApi<{ success: boolean; data: Partial<Character> }>('/roles/generate', {
            method: 'POST',
            body: JSON.stringify({ description }),
        }),

    generateTags: (description: string) =>
        fetchApi<{ success: boolean; tags: string }>('/roles/generate-tags', {
            method: 'POST',
            body: JSON.stringify({ description }),
        }),

    getStates: (id: string) =>
        fetchApi<{ success: boolean; data: CharacterState[] }>(`/roles/${id}/states`),

    // 上传头像图片（multipart/form-data）
    uploadAvatar: async (file: File): Promise<{ success: boolean; url: string }> => {
        const form = new FormData()
        form.append('file', file)
        const token = getToken()
        const res = await fetch(`${API_BASE_URL}/roles/upload-avatar`, {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: form,
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: '上传失败' }))
            throw new Error(err.detail || `HTTP ${res.status}`)
        }
        return res.json()
    },

    // 触发 AI 生成角色头像（Z-image，消耗积分）
    generateAvatar: (roleId: string) =>
        fetchApi<{ success: boolean; task_id: string }>(`/roles/${roleId}/generate-avatar`, {
            method: 'POST',
            timeoutMs: 30000,
        }),

    // 将生成完成的头像保存到角色
    saveAvatar: (roleId: string, imageUrl: string) =>
        fetchApi<{ success: boolean; avatar_url: string }>(`/roles/${roleId}/save-avatar`, {
            method: 'POST',
            body: JSON.stringify({ image_url: imageUrl }),
        }),
}

// Chat API
export const chatApi = {
    getSessions: () =>
        fetchApi<{ success: boolean; data: { role_id: number; character: { id: number; name: string; avatar?: string; greeting: string }; message_count: number; last_message: { content: string; timestamp: string } | null }[] }>('/chat/sessions'),

    getHistory: (characterId: string, limit = 20, beforeId = 0) => {
        const params = new URLSearchParams({ limit: String(limit) })
        if (beforeId > 0) params.set('before_id', String(beforeId))
        return fetchApi<Message[]>(`/chat/history/${characterId}?${params}`)
    },

    sendMessage: (characterId: string, message: string, storyMode?: boolean) =>
        fetchApi<{ success: boolean; message: string; data: { id: number; content: string; role: string; created_at: string; states?: CharacterState[] }; choices: string[] }>(`/chat/send/${characterId}`, {
            method: 'POST',
            body: JSON.stringify({ message, story_mode: storyMode || false }),
            timeoutMs: 180000,  // AI 对话需要较长时间（最多 180 秒，含重试）
        }),

    /**
     * 流式发送消息（SSE），通过回调逐 token 推送
     * @param onToken   每个 token 到来时回调
     * @param onDone    流完成时回调，携带 message_id 和 choices
     * @param onError   出错回调
     * @returns AbortController，可调用 .abort() 中断
     */
    sendMessageStream: (
        characterId: string,
        message: string,
        storyMode: boolean,
        onToken: (token: string) => void,
        onDone: (messageId: number, choices: string[]) => void,
        onError: (detail: string) => void
    ): AbortController => {
        const controller = new AbortController()
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (token) headers['Authorization'] = `Bearer ${token}`

        fetch(`${API_BASE_URL}/chat/send-stream/${characterId}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ message, story_mode: storyMode }),
            signal: controller.signal,
        }).then(async (res) => {
            if (!res.ok) {
                const errText = await res.text().catch(() => '')
                onError(`请求失败 ${res.status}: ${errText.slice(0, 100)}`)
                return
            }
            const reader = res.body?.getReader()
            if (!reader) { onError('不支持流式读取'); return }
            const decoder = new TextDecoder()
            let buffer = ''
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                buffer += decoder.decode(value, { stream: true })
                // 按 SSE 消息边界（双换行）分割，避免在消息中间截断
                const parts = buffer.split('\n\n')
                buffer = parts.pop() ?? ''
                for (const part of parts) {
                    for (const line of part.split('\n')) {
                        if (!line.startsWith('data: ')) continue
                        const dataStr = line.slice(6).trim()
                        if (!dataStr) continue
                        try {
                            const evt = JSON.parse(dataStr)
                            if (evt.type === 'token') onToken(evt.content)
                            else if (evt.type === 'done') onDone(evt.message_id, evt.choices ?? [])
                            else if (evt.type === 'error') onError(evt.detail)
                        } catch { /* 忽略解析失败 */ }
                    }
                }
            }
            // 处理流结束时 buffer 中的剩余数据
            if (buffer.trim()) {
                for (const line of buffer.split('\n')) {
                    if (!line.startsWith('data: ')) continue
                    const dataStr = line.slice(6).trim()
                    if (!dataStr) continue
                    try {
                        const evt = JSON.parse(dataStr)
                        if (evt.type === 'token') onToken(evt.content)
                        else if (evt.type === 'done') onDone(evt.message_id, evt.choices ?? [])
                        else if (evt.type === 'error') onError(evt.detail)
                    } catch { /* 忽略解析失败 */ }
                }
            }
        }).catch((err) => {
            if (err.name !== 'AbortError') onError(err.message || '网络错误')
        })

        return controller
    },


    clearHistory: (characterId: string) =>
        fetchApi<{ success: boolean; message: string }>(`/chat/history/${characterId}`, {
            method: 'DELETE',
        }),

    getStates: (characterId: string) =>
        fetchApi<{ success: boolean; role_id: number; role_name: string; states: Record<string, { value: string; desc: string; min?: string; max?: string }> }>(`/chat/states/${characterId}`),

    resetStates: (characterId: string) =>
        fetchApi<{ success: boolean; message: string }>(`/chat/reset-states/${characterId}`, {
            method: 'POST',
        }),

    generateTTS: (text: string, characterId: string, voiceRef?: string, messageId?: string) =>
        fetchApi<{ success: boolean; audio_url?: string; audio?: string; format?: string; error?: string }>('/chat/tts', {
            method: 'POST',
            body: JSON.stringify({ text, role_id: characterId, voice_ref: voiceRef || undefined, message_id: messageId ? parseInt(messageId) : undefined }),
            timeoutMs: 60000,  // TTS 需要调 Fish Audio API，给 60 秒
        }),

    generateTTSAsync: (text: string, characterId: string, voiceRef?: string, messageId?: string) =>
        fetchApi<{ success: boolean; task_id?: string; error?: string }>('/chat/tts-async', {
            method: 'POST',
            body: JSON.stringify({ text, role_id: characterId, voice_ref: voiceRef || undefined, message_id: messageId ? parseInt(messageId) : undefined }),
        }),

    checkTTSStatus: (taskId: string) =>
        fetchApi<{ status: string; audio_url?: string; error?: string }>(`/chat/tts-status/${taskId}`),

    generateImage: (messageId: string, overrides?: { appearance_tags?: string; clothing_state?: string; image_style?: string }) =>
        fetchApi<{ success: boolean; task_id: string }>(`/chat/generate-image/${messageId}`, {
            method: 'POST',
            body: JSON.stringify(overrides || {}),
        }),

    checkImageStatus: (taskId: string) =>
        fetchApi<{ status: string; image_url?: string; error?: string }>(`/chat/image-status/${taskId}`),

    saveImage: (messageId: string, imageUrl: string) =>
        fetchApi<{ success: boolean }>(`/chat/save-image/${messageId}`, {
            method: 'POST',
            body: JSON.stringify({ image_url: imageUrl }),
        }),

    getChatSettings: (roleId: string | number) =>
        fetchApi<{ success: boolean; data: { appearance_tags: string | null; voice_ref: string | null; image_style: string | null } }>(`/chat/settings/${roleId}`),

    saveChatSettings: (roleId: string | number, settings: { appearance_tags?: string; voice_ref?: string; image_style?: string }) =>
        fetchApi<{ success: boolean }>(`/chat/settings/${roleId}`, {
            method: 'POST',
            body: JSON.stringify(settings),
        }),

    polishAppearance: (text: string) =>
        fetchApi<{ success: boolean; polished: string }>('/chat/polish-appearance', {
            method: 'POST',
            body: JSON.stringify({ text }),
            timeoutMs: 30000,
        }),

    getVoicePresets: () =>
        fetchApi<{ success: boolean; presets: Array<{ id: string; name: string; description: string; reference_id: string; preview_url: string }> }>('/chat/voice-presets'),

    getVoicePreviewUrl: (voiceId: string) => `/api/chat/voice-preview/${voiceId}`,
}

// Credits API
export const creditsApi = {
    getBalance: () =>
        fetchApi<{ success: boolean; data: { balance: number; total_earned: number; total_spent: number } }>('/credits/balance'),

    getCosts: () =>
        fetchApi<{ success: boolean; data: { chat: number; tts: number; tti: number; create_role: number } }>('/credits/costs'),
}

// Payment API（爱发电版）
export interface PaymentPackage {
    id: string
    plan_id: string        // 爱发电方案 ID
    name: string
    amount: number
    credits: number
    desc: string
    popular?: boolean
}

export interface PrepareOrderResult {
    success: boolean
    pay_url: string            // 爱发电付款链接，前端直接跳转
    custom_order_id: string    // 用于轮询支付状态
    user_id: number            // 当前用户ID（前端校验用）
}

export interface OrderStatus {
    custom_order_id: string
    status: 'pending' | 'paid' | 'failed'
    credits?: number
    message: string
}

export const paymentApi = {
    getPackages: () =>
        fetchApi<{ success: boolean; data: PaymentPackage[] }>('/payment/packages'),

    prepareOrder: (packageId: string) =>
        fetchApi<PrepareOrderResult>('/payment/prepare-order', {
            method: 'POST',
            body: JSON.stringify({ package_id: packageId }),
        }),

    getOrderStatus: (customOrderId: string) =>
        fetchApi<OrderStatus>(`/payment/order/${customOrderId}/status`),
}

// Checkin API
export interface CheckinStatus {
    has_checked_in_today: boolean
    streak_days: number
    today_points: number
    total_checkins: number
}

export interface CheckinResult {
    is_new: boolean
    points_earned: number
    streak_days: number
    total_checkins: number
}

export const checkinApi = {
    checkin: () =>
        fetchApi<{ success: boolean; data: CheckinResult; message: string }>('/checkin/', {
            method: 'POST',
        }),

    getStatus: () =>
        fetchApi<{ success: boolean; data: CheckinStatus }>('/checkin/status'),
}

export default {
    auth: authApi,
    characters: charactersApi,
    chat: chatApi,
    credits: creditsApi,
    payment: paymentApi,
    checkin: checkinApi,
}
