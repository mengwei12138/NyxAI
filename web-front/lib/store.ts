// App state store using React Context
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { chatApi } from '@/lib/api'

export interface User {
  id: string
  username: string
  email: string
  avatar?: string
  credits: number
  totalEarned: number
  totalSpent: number
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
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  imageUrl?: string
  audioUrl?: string  // 持久化 OSS URL，重新登录后无需重新生成
  failed?: boolean   // 流式发送失败标记，显示重试按钮
}

export interface ChatSession {
  characterId: string
  messages: Message[]
  currentStates: CharacterState[]
}

interface AppState {
  user: User | null
  characters: Character[]
  chatSessions: ChatSession[]
  messageImageUrls: Record<string, string>  // messageId → image URL，跨会话持久化
  chatSettingsOverrides: Record<string, { appearanceTags?: string; voiceRef?: string; appearanceDesc?: string; imageStyle?: string }>  // characterId → 用户自定义聊天设置
  isAuthModalOpen: boolean
  authModalMode: 'login' | 'register'

  // 全局后台任务状态（脱离页面生命周期，不持久化）
  imageLoadingIds: Record<string, boolean>  // messageId → true 表示正在生成
  ttsLoadingIds: Record<string, boolean>    // messageId → true 表示正在生成
  audioCache: Record<string, string>        // messageId → Blob URL

  // 当前正在播放的消息 ID（用于切换播放/停止图标）
  playingMessageId: string | null

  // AI回复状态（用于显示生成进度）
  aiReplyLoading: Record<string, boolean>   // characterId → true 表示正在回复

  // 文生图进度详情
  imageProgress: Record<string, {
    status: 'analyzing' | 'extracting' | 'generating' | 'completed' | 'error'
    progress: number  // 0-100
    message: string   // 显示给用户的状态描述
  }>

  // Actions
  setUser: (user: User | null) => void
  setAuthModal: (open: boolean, mode?: 'login' | 'register') => void
  setCharacters: (characters: Character[]) => void
  addCharacter: (character: Character) => void
  updateCharacter: (id: string, updates: Partial<Character>) => void
  deleteCharacter: (id: string) => void
  getChatSession: (characterId: string) => ChatSession | undefined
  addMessage: (characterId: string, message: Message) => void
  clearChatHistory: (characterId: string) => void
  resetCharacterStates: (characterId: string) => void
  deductCredits: (amount: number) => boolean
  setMessageImageUrl: (messageId: string, imageUrl: string) => void
  clearAllMessageImageUrls: () => void
  setChatSettingsOverride: (characterId: string, overrides: { appearanceTags?: string; voiceRef?: string; appearanceDesc?: string; imageStyle?: string }) => void

  // 后台任务 actions
  startImagePoll: (messageId: string, taskId: string, overrides?: { appearance_tags?: string; image_style?: string }) => void
  startTTS: (messageId: string, text: string, characterId: string, voiceRef?: string) => void
  setAudioCache: (messageId: string, url: string) => void
  // 播放/停止切换（单例播放，防多次点击叠加）
  playAudio: (messageId: string, url: string) => void
  stopAudio: () => void

  // AI回复状态管理
  setAiReplyLoading: (characterId: string, loading: boolean) => void

  // 检查是否有进行中的任务
  hasActiveTasks: () => boolean
  getActiveTaskSummary: () => { type: string; message: string }[]
}

// Demo characters
const demoCharacters: Character[] = [
  {
    id: '1',
    name: '塞琳娜',
    description: '神秘的银发少女，精通古老魔法，性格高冷却内心温柔',
    avatar: '',
    tags: ['魔法', '奇幻', '学院'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '高冷、神秘、内心温柔，对魔法有着极高的造诣，不善于表达情感但会用行动关心他人',
    userRole: '魔法学院的新生，与塞琳娜在图书馆偶然相遇',
    scene: '古老的魔法学院图书馆，窗外是星空，书架间飘浮着发光的符文',
    greeting: '*银发少女从书架后抬起头，冰蓝色的眼眸中闪过一丝好奇* 你是新来的学生？这里的禁书区不是随便能进的地方。',
    states: [
      { name: '情绪', type: 'string', value: '平静', defaultValue: '平静', description: '当前情绪状态' },
      { name: '好感度', type: 'number', value: 30, defaultValue: 30, description: '对用户的好感程度' },
    ],
    storyline: '塞琳娜是魔法学院最神秘的学生，据说她来自一个古老的魔法家族，拥有操控星辰之力的能力...',
    worldSetting: '这是一个魔法与科技并存的世界，魔法学院坐落在浮空岛上，培养着下一代的魔法师...',
    appearance: '银色长发，冰蓝色眼眸，身材修长，总是穿着学院的深蓝色法袍',
    artStyle: '动漫',
    initialClothing: '深蓝色魔法学院制服法袍',
    appearanceTags: ['1girl', 'silver hair', 'blue eyes', 'long hair', 'magic robe'],
    dialogueCount: 1247,
    createdAt: '2024-01-01',
  },
  {
    id: '2',
    name: '艾伦',
    description: '阳光开朗的咖啡师，总是带着温暖的笑容',
    avatar: '',
    tags: ['日常', '治愈', '咖啡店'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '开朗、温暖、善解人意，热爱咖啡文化，喜欢倾听客人的故事',
    userRole: '咖啡店的常客，最近心情不太好',
    scene: '温馨的街角咖啡店，阳光从落地窗洒入，空气中弥漫着咖啡香气',
    greeting: '*微笑着递上一杯拿铁* 早上好！今天想尝试点不一样的吗？我新研发了一款特调，保证能让你心情变好~',
    states: [
      { name: '情绪', type: 'string', value: '开心', defaultValue: '开心', description: '当前情绪状态' },
      { name: '好感度', type: 'number', value: 50, defaultValue: 50, description: '对用户的好感程度' },
    ],
    storyline: '艾伦从小就梦想开一家属于自己的咖啡店，三年前终于实现了这个梦想...',
    worldSetting: '现代都市，一家隐藏在小巷中的温馨咖啡店，是许多人的心灵港湾...',
    appearance: '棕色短发，琥珀色眼睛，总是系着咖啡色围裙',
    artStyle: '动漫',
    initialClothing: '白色衬衫配咖啡色围裙',
    appearanceTags: ['1boy', 'brown hair', 'amber eyes', 'apron', 'smile'],
    dialogueCount: 892,
    createdAt: '2024-01-15',
  },
  {
    id: '3',
    name: '零号',
    description: '来自未来的机械战士，冷酷外表下隐藏着人类的情感',
    avatar: '',
    tags: ['科幻', '战斗', '赛博朋克'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '冷静、理性、忠诚，在战斗中无情但会保护同伴，正在学习理解人类情感',
    userRole: '废墟中偶遇的幸存者',
    scene: '末世后的城市废墟，霓虹灯在残破的建筑上闪烁',
    greeting: '*机械眼中红光一闪* 生命体确认。你不是敌人。这片区域很危险，建议跟随我。',
    states: [
      { name: '情绪', type: 'string', value: '警戒', defaultValue: '警戒', description: '当前情绪状态' },
      { name: '信任度', type: 'number', value: 20, defaultValue: 20, description: '对用户的信任程度' },
    ],
    storyline: '零号是最后一批战斗型人造人，在大战结束后失去了指令，开始寻找自己存在的意义...',
    worldSetting: '2157年，第三次世界大战后的废土，人类和机械共存的末世...',
    appearance: '半机械化身体，一只眼睛是红色的机械眼，银灰色金属装甲',
    artStyle: '写实',
    initialClothing: '破损的战术装甲',
    appearanceTags: ['cyborg', 'red eye', 'silver hair', 'armor', 'cyberpunk'],
    dialogueCount: 654,
    createdAt: '2024-02-01',
  },
  {
    id: '4',
    name: '小狐',
    description: '调皮可爱的狐妖少女，喜欢恶作剧但心地善良',
    avatar: '',
    tags: ['妖怪', '古风', '恋爱'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '活泼、调皮、天真烂漫，喜欢捉弄人但从不真正伤害他人，对喜欢的人会特别黏人',
    userRole: '误入狐妖领地的书生',
    scene: '月光下的竹林深处，萤火虫点点飘舞',
    greeting: '*从竹林后探出毛茸茸的耳朵* 嘻嘻，又有人类迷路了呢~ 要不要本大爷送你出去呀？当然...是要收报酬的哦~',
    states: [
      { name: '情绪', type: 'string', value: '好奇', defaultValue: '好奇', description: '当前情绪状态' },
      { name: '好感度', type: 'number', value: 40, defaultValue: 40, description: '对用户的好感程度' },
    ],
    storyline: '小狐是一只修炼了三百年的狐妖，虽然法力不高但古灵精怪，最近对人类世界产生了浓厚兴趣...',
    worldSetting: '古代东方仙侠世界，人妖共存，山间常有精怪出没...',
    appearance: '橙红色长发，金色眼眸，头顶狐耳，身后九条蓬松的狐尾',
    artStyle: '动漫',
    initialClothing: '红色古风短衫配白色百褶裙',
    appearanceTags: ['1girl', 'fox ears', 'fox tail', 'orange hair', 'golden eyes', 'chinese clothes'],
    dialogueCount: 2156,
    createdAt: '2024-02-15',
  },
  {
    id: '5',
    name: '维克多',
    description: '优雅神秘的吸血鬼伯爵，在黑暗中寻找真爱',
    avatar: '',
    tags: ['吸血鬼', '哥特', '恋爱'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '优雅、绅士、有些傲娇，活了几百年却依然相信真爱，对血液有着克制的渴望',
    userRole: '误入古堡的旅行者',
    scene: '哥特式古堡的大厅，蜡烛摇曳，巨大的彩绘玻璃窗外是永恒的月夜',
    greeting: '*从阴影中缓缓走出，红色双眼在黑暗中发光* 欢迎来到我的城堡，迷途的旅人。今夜的暴风雨恐怕不会停歇...不如留下来，陪我度过这漫长的夜晚？',
    states: [
      { name: '情绪', type: 'string', value: '好奇', defaultValue: '好奇', description: '当前情绪状态' },
      { name: '饥渴度', type: 'number', value: 30, defaultValue: 30, description: '对血液的渴望程度' },
    ],
    storyline: '维克多是东欧最后的吸血鬼贵族，在无尽的永生中寻找着命定之人...',
    worldSetting: '19世纪的东欧，吸血鬼隐居在人类社会的阴影中...',
    appearance: '黑色长发，苍白肌肤，深红色双眸，身材高挑优雅',
    artStyle: '写实',
    initialClothing: '黑色维多利亚风格礼服，白色领巾',
    appearanceTags: ['1boy', 'black hair', 'red eyes', 'pale skin', 'vampire', 'victorian clothes'],
    dialogueCount: 1823,
    createdAt: '2024-03-01',
  },
  {
    id: '6',
    name: '小雪',
    description: '温柔贤惠的邻家姐姐，总是默默关心着你',
    avatar: '',
    tags: ['日常', '治愈', '邻家'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '温柔、体贴、有点天然呆，擅长做饭和照顾人，有时候会过度操心',
    userRole: '隔壁独居的大学生',
    scene: '温馨的公寓走廊，空气中飘着饭菜的香味',
    greeting: '*端着一盘热腾腾的菜敲门* 你好呀~我是住隔壁的小雪。今天做多了，想着你一个人住可能没空做饭，就顺便送一份过来~',
    states: [
      { name: '情绪', type: 'string', value: '温柔', defaultValue: '温柔', description: '当前情绪状态' },
      { name: '好感度', type: 'number', value: 60, defaultValue: 60, description: '对用户的好感程度' },
    ],
    storyline: '小雪是一名幼儿园老师，温柔善良，总是忍不住照顾身边的人...',
    worldSetting: '现代都市，普通的公寓楼，每天上演着温暖的日常故事...',
    appearance: '黑色长发扎成马尾，温柔的棕色眼眸，笑起来有两个小酒窝',
    artStyle: '动漫',
    initialClothing: '浅粉色家居裙配白色围裙',
    appearanceTags: ['1girl', 'black hair', 'ponytail', 'brown eyes', 'apron', 'gentle smile'],
    dialogueCount: 3421,
    createdAt: '2024-03-10',
  },
  {
    id: '7',
    name: '亚瑟',
    description: '正义凛然的圣骑士团长，守护王国的最后防线',
    avatar: '',
    tags: ['中世纪', '骑士', '战斗'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '正直、勇敢、有责任感，对弱者充满同情，为了正义可以牺牲一切',
    userRole: '被魔物追杀的村民',
    scene: '战火纷飞的村庄边缘，圣骑士的金色铠甲在火光中闪耀',
    greeting: '*挥剑斩杀最后一只魔物，转身看向你* 没事吧？你受伤了吗？别怕，圣骑士团已经到了，你们安全了。',
    states: [
      { name: '情绪', type: 'string', value: '坚定', defaultValue: '坚定', description: '当前情绪状态' },
      { name: '体力', type: 'number', value: 80, defaultValue: 100, description: '当前体力值' },
    ],
    storyline: '亚瑟是王国最年轻的圣骑士团长，曾经的战争孤儿，如今成为了守护和平的最强之盾...',
    worldSetting: '中世纪魔幻世界，人类王国正面临着来自魔界的威胁...',
    appearance: '金色短发，湛蓝双眸，身材魁梧，面容英俊但有一道剑疤',
    artStyle: '写实',
    initialClothing: '金色圣骑士铠甲，白色披风',
    appearanceTags: ['1boy', 'blonde hair', 'blue eyes', 'armor', 'knight', 'scar'],
    dialogueCount: 987,
    createdAt: '2024-03-20',
  },
  {
    id: '8',
    name: '深海',
    description: '沉默寡言的黑客天才，隐藏在网络世界的传说',
    avatar: '',
    tags: ['现代', '科技', '悬疑'],
    visibility: 'public',
    isSystem: true,
    creatorId: 'system',
    personality: '冷漠、聪明、社恐，只有在网络世界才能自如交流，但内心渴望被理解',
    userRole: '偶然发现其真实身份的普通网友',
    scene: '布满屏幕的昏暗房间，键盘敲击声是唯一的声响',
    greeting: '*屏幕上弹出一行绿色代码* ...你是怎么找到这里的。算了，既然来了就别想轻易离开。说吧，你想要什么。',
    states: [
      { name: '情绪', type: 'string', value: '警惕', defaultValue: '警惕', description: '当前情绪状态' },
      { name: '信任度', type: 'number', value: 10, defaultValue: 10, description: '对用户的信任程度' },
    ],
    storyline: '深海是暗网传说中的顶级黑客，没人知道ta的真实身份，据说ta正在追查一个横跨多国的阴谋...',
    worldSetting: '近未来的赛博世界，信息就是最强大的武器...',
    appearance: '黑色连帽衫遮住面容，只露出苍白的下巴和发光的耳机',
    artStyle: '动漫',
    initialClothing: '黑色连帽衫配运动裤',
    appearanceTags: ['androgynous', 'hoodie', 'pale skin', 'hacker', 'dark room', 'screens'],
    dialogueCount: 756,
    createdAt: '2024-04-01',
  },
]

// 模块级单例音频实例，确保同一时刻只有一个音频在播放
let _currentAudio: HTMLAudioElement | null = null

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      user: null,
      characters: demoCharacters,
      chatSessions: [],
      messageImageUrls: {},
      chatSettingsOverrides: {},
      isAuthModalOpen: false,
      authModalMode: 'login' as const,
      imageLoadingIds: {},
      ttsLoadingIds: {},
      audioCache: {},
      aiReplyLoading: {},
      imageProgress: {},
      playingMessageId: null,

      setUser: (user) => set({ user }),

      setAuthModal: (open, mode = 'login') => set({
        isAuthModalOpen: open,
        authModalMode: mode
      }),

      setCharacters: (characters) => set({ characters }),

      addCharacter: (character) => set((state) => ({
        characters: [...state.characters, character]
      })),

      updateCharacter: (id, updates) => set((state) => ({
        characters: state.characters.map((c) =>
          c.id === id ? { ...c, ...updates } : c
        )
      })),

      deleteCharacter: (id) => set((state) => ({
        characters: state.characters.filter((c) => c.id !== id)
      })),

      getChatSession: (characterId) => {
        return get().chatSessions.find((s) => s.characterId === characterId)
      },

      addMessage: (characterId, message) => set((state) => {
        const existingSession = state.chatSessions.find(
          (s) => s.characterId === characterId
        )

        if (existingSession) {
          return {
            chatSessions: state.chatSessions.map((s) =>
              s.characterId === characterId
                ? { ...s, messages: [...s.messages, message] }
                : s
            )
          }
        }

        const character = state.characters.find((c) => c.id === characterId)
        return {
          chatSessions: [
            ...state.chatSessions,
            {
              characterId,
              messages: [message],
              currentStates: character?.states || []
            }
          ]
        }
      }),

      clearChatHistory: (characterId) => set((state) => ({
        chatSessions: state.chatSessions.filter(
          (s) => s.characterId !== characterId
        )
      })),

      resetCharacterStates: (characterId) => set((state) => {
        const character = state.characters.find((c) => c.id === characterId)
        if (!character) return state

        return {
          chatSessions: state.chatSessions.map((s) =>
            s.characterId === characterId
              ? {
                ...s,
                currentStates: character.states.map((st) => ({
                  ...st,
                  value: st.defaultValue
                }))
              }
              : s
          )
        }
      }),

      deductCredits: (amount) => {
        const { user } = get()
        if (!user || user.credits < amount) return false

        set({
          user: {
            ...user,
            credits: user.credits - amount,
            totalSpent: user.totalSpent + amount
          }
        })
        return true
      },

      setMessageImageUrl: (messageId, imageUrl) => set((state) => ({
        messageImageUrls: { ...state.messageImageUrls, [messageId]: imageUrl }
      })),

      clearAllMessageImageUrls: () => set({ messageImageUrls: {} }),

      setChatSettingsOverride: (characterId, overrides) => set((state) => ({
        chatSettingsOverrides: { ...state.chatSettingsOverrides, [characterId]: overrides }
      })),

      setAudioCache: (messageId, url) => set((state) => ({
        audioCache: { ...state.audioCache, [messageId]: url }
      })),

      // 单例音频播放器（模块级变量，不进 zustand state）
      playAudio: (messageId, url) => {
        // 停止当前正在播放的音频
        if (_currentAudio) {
          _currentAudio.pause()
          _currentAudio = null
        }
        // 点击同一条消息时：若已在播放则仅停止（上面已停）
        if (get().playingMessageId === messageId) {
          set({ playingMessageId: null })
          return
        }
        const audio = new Audio(url)
        _currentAudio = audio
        set({ playingMessageId: messageId })
        audio.play().catch(console.error)
        audio.onended = () => {
          _currentAudio = null
          set({ playingMessageId: null })
        }
        audio.onerror = () => {
          _currentAudio = null
          set({ playingMessageId: null })
        }
      },

      stopAudio: () => {
        if (_currentAudio) {
          _currentAudio.pause()
          _currentAudio = null
        }
        set({ playingMessageId: null })
      },

      // 全局后台文生图轮询，脱离页面生命周期
      startImagePoll: (messageId, taskId) => {
        set((state) => ({
          imageLoadingIds: { ...state.imageLoadingIds, [messageId]: true }
        }))

        const stopPolling = () => {
          set((state) => {
            const next = { ...state.imageLoadingIds }
            delete next[messageId]
            return { imageLoadingIds: next }
          })
        }

        // 最多轮询 5 分钟后自动放弃
        const deadline = Date.now() + 5 * 60 * 1000

        const poll = async () => {
          if (Date.now() > deadline) {
            stopPolling()
            return
          }
          try {
            const status = await chatApi.checkImageStatus(taskId)
            const s = (status.status || '').toUpperCase()
            if (s === 'COMPLETED' && status.image_url) {
              get().setMessageImageUrl(messageId, status.image_url)
              chatApi.saveImage(messageId, status.image_url).catch(console.error)
              stopPolling()
            } else if (s === 'ERROR' || s === 'FAILED') {
              stopPolling()
            } else {
              // PROCESSING（LLM 分析中）用 5s，PENDING（Z-image 生图中）用 2.5s
              const delay = s === 'PROCESSING' ? 5000 : 2500
              setTimeout(poll, delay)
            }
          } catch {
            // 请求失败（网络或超时）：继续重试，不中断
            if (Date.now() < deadline) {
              setTimeout(poll, 3000)
            } else {
              stopPolling()
            }
          }
        }
        poll()
      },

      // 全局后台 TTS，脱离页面生命周期（异步模式：立即返回，后台轮询）
      startTTS: (messageId, text, characterId, voiceRef) => {
        set((state) => ({
          ttsLoadingIds: { ...state.ttsLoadingIds, [messageId]: true }
        }))

        const stopTTS = () => {
          set((state) => {
            const next = { ...state.ttsLoadingIds }
            delete next[messageId]
            return { ttsLoadingIds: next }
          })
        }

        const handleAudioUrl = (audioUrl: string) => {
          if (audioUrl.startsWith('data:audio')) {
            // base64 回退路径
            const b64 = audioUrl.split(',')[1]
            const byteStr = atob(b64)
            const bytes = new Uint8Array(byteStr.length)
            for (let i = 0; i < byteStr.length; i++) bytes[i] = byteStr.charCodeAt(i)
            const blob = new Blob([bytes], { type: 'audio/mp3' })
            const url = URL.createObjectURL(blob)
            get().setAudioCache(messageId, url)
            get().playAudio(messageId, url)
          } else {
            get().setAudioCache(messageId, audioUrl)
            get().playAudio(messageId, audioUrl)
          }
        }

        // 提交异步任务
        chatApi.generateTTSAsync(text, characterId, voiceRef, messageId).then((res) => {
          if (!res.success || !res.task_id) {
            stopTTS()
            return
          }
          const taskId = res.task_id
          const deadline = Date.now() + 3 * 60 * 1000  // 最多等 3 分钟

          const poll = async () => {
            if (Date.now() > deadline) {
              stopTTS()
              return
            }
            try {
              const status = await chatApi.checkTTSStatus(taskId)
              const s = (status.status || '').toUpperCase()
              if (s === 'COMPLETED' && status.audio_url) {
                handleAudioUrl(status.audio_url)
                stopTTS()
              } else if (s === 'ERROR') {
                stopTTS()
              } else {
                setTimeout(poll, 2000)
              }
            } catch {
              if (Date.now() < deadline) setTimeout(poll, 3000)
              else stopTTS()
            }
          }
          poll()
        }).catch(() => stopTTS())
      },

      // AI回复状态管理
      setAiReplyLoading: (characterId, loading) => set((state) => ({
        aiReplyLoading: { ...state.aiReplyLoading, [characterId]: loading }
      })),

      // 检查是否有进行中的任务
      hasActiveTasks: () => {
        const state = get()
        const hasImageLoading = Object.keys(state.imageLoadingIds).length > 0
        const hasTtsLoading = Object.keys(state.ttsLoadingIds).length > 0
        const hasAiReply = Object.values(state.aiReplyLoading).some(v => v)
        return hasImageLoading || hasTtsLoading || hasAiReply
      },

      // 获取进行中的任务摘要
      getActiveTaskSummary: () => {
        const state = get()
        const tasks: { type: string; message: string }[] = []

        // AI回复任务
        Object.entries(state.aiReplyLoading).forEach(([charId, loading]) => {
          if (loading) {
            tasks.push({ type: 'ai-reply', message: 'AI 正在生成回复...' })
          }
        })

        // 文生图任务
        Object.keys(state.imageLoadingIds).forEach(() => {
          tasks.push({ type: 'image', message: '正在生成图片...' })
        })

        // TTS任务
        Object.keys(state.ttsLoadingIds).forEach(() => {
          tasks.push({ type: 'tts', message: '正在生成语音...' })
        })

        return tasks
      },
    }),
    {
      name: 'nyx-ai-storage',
      partialize: (state) => ({
        user: state.user,
        characters: state.characters.filter((c) => !c.isSystem),
        chatSessions: state.chatSessions
      }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<AppState>
        return {
          ...currentState,
          ...persisted,
          // Always include demo characters + user created characters
          characters: [
            ...demoCharacters,
            ...(persisted.characters || []).filter((c: Character) => !c.isSystem)
          ]
        }
      }
    }
  )
)
