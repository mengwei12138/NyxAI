'use client'

import { use, useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { CreditsDialog } from '@/components/credits-dialog'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { useAppStore, Message } from '@/lib/store'
import { charactersApi, chatApi } from '@/lib/api'
import type { Character, CharacterState } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'
import {
  ArrowLeft,
  Send,
  Volume2,
  Image as ImageIcon,
  RotateCcw,
  Trash2,
  MoreVertical,
  Loader2,
  Activity,
  X,
  Settings,
  Palette,
  AlertTriangle,
  Play,
  Square,
  Sparkles,
  Mic,
  RefreshCcw,
} from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { Switch } from '@/components/ui/switch'

export default function ChatPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const router = useRouter()
  const { toast } = useToast()
  const streamControllerRef = useRef<AbortController | null>(null)
  const {
    user,
    setAuthModal,
    getChatSession,
    addMessage,
    clearChatHistory,
    resetCharacterStates,
    deductCredits,
    chatSessions,
    messageImageUrls: persistedImageUrls,
    setMessageImageUrl,
    clearAllMessageImageUrls,
    chatSettingsOverrides,
    setChatSettingsOverride,
    imageLoadingIds,
    ttsLoadingIds,
    audioCache,
    playingMessageId,
    startImagePoll,
    startTTS,
    playAudio,
    aiReplyLoading,
    setAiReplyLoading,
    hasActiveTasks,
    getActiveTaskSummary,
  } = useAppStore()

  const [character, setCharacter] = useState<Character | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Get messages from store
  const session = getChatSession(id)
  const storeMessages = session?.messages || []
  const [currentStates, setCurrentStates] = useState<CharacterState[]>([])
  const [loading, setLoading] = useState(true)         // 角色信息加载中（控制骨架屏）
  const [historyLoading, setHistoryLoading] = useState(true)  // 历史消息加载中（消息区骨架）
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const isSendingRef = useRef(false)  // 同步锁，防止快速双击重复提交
  const [showCreditsDialog, setShowCreditsDialog] = useState(false)
  const [creditsAction, setCreditsAction] = useState({ amount: 0, action: '', callback: () => { } })
  const [showChatSettings, setShowChatSettings] = useState(false)
  // 退出确认弹窗
  const [showExitConfirm, setShowExitConfirm] = useState(false)
  const [pendingNavigation, setPendingNavigation] = useState<(() => void) | null>(null)
  // AI润色状态
  const [isPolishing, setIsPolishing] = useState(false)
  const [chatSettings, _setChatSettings] = useState({
    appearanceTags: '',
    voiceRef: '',
    appearanceDesc: '',  // 自然语言外貌描述（用于 AI 生成 tags）
    imageStyle: '',      // 画风（anime/realistic/illustration/fantasy/painterly）
  })
  // 防抖定时器 ref
  const saveSettingsTimerRef = useRef<NodeJS.Timeout | null>(null)
  // 组件挂载状态 ref，用于在离开页面后终止异步操作
  const isMountedRef = useRef(true)
  // 包装一层，每次修改同时持久化到 store + DB
  const setChatSettings = (next: typeof chatSettings | ((prev: typeof chatSettings) => typeof chatSettings)) => {
    // 先计算新值，再分别更新两个 state（避免在 updater 函数内调用其他 setState）
    const newVal = typeof next === 'function' ? next(chatSettings) : next
    _setChatSettings(newVal)
    // 1. 写入 localStorage store
    setChatSettingsOverride(id, newVal)
    // 2. 防抖写入 DB，1s 内只发一次
    if (saveSettingsTimerRef.current) clearTimeout(saveSettingsTimerRef.current)
    saveSettingsTimerRef.current = setTimeout(() => {
      chatApi.saveChatSettings(id, {
        appearance_tags: newVal.appearanceTags || undefined,
        voice_ref: newVal.voiceRef || undefined,
        image_style: newVal.imageStyle || undefined,
      }).catch(console.error)
    }, 1000)
  }
  const [tagsGenerating, setTagsGenerating] = useState(false)
  // 音色预设列表
  type VoicePreset = { id: string; name: string; description: string; reference_id: string; preview_url: string }
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([])
  // 试听状态：当前正在播放的音色 id
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null)
  const previewAudioRef = useRef<HTMLAudioElement | null>(null)
  // 图片 URL 优先读 store（持久化），本地 state 作为当前会话快照
  const [messageImageUrls, setMessageImageUrls] = useState<Record<string, string>>(persistedImageUrls)
  // 本地文生图加载状态（点击后立即显示，不等待API）
  const [localImageLoading, setLocalImageLoading] = useState<Record<string, boolean>>({})
  // 图片灯箱（点击大图预览）
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const [storyMode, setStoryMode] = useState(false)
  const [pendingChoices, setPendingChoices] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 同步 store 中的图片 URL 变化（文生图完成后更新）
  useEffect(() => {
    setMessageImageUrls(persistedImageUrls)
  }, [persistedImageUrls])

  // 当 store 中的文生图任务完成时，清除本地加载状态
  useEffect(() => {
    setLocalImageLoading(prev => {
      const next = { ...prev }
      Object.keys(next).forEach(msgId => {
        if (!imageLoadingIds[msgId]) {
          delete next[msgId]
        }
      })
      return next
    })
  }, [imageLoadingIds])

  // Load character and chat history
  // 组件挂载时重置可能残留的加载状态（防止上次页面关闭时状态未清理）
  useEffect(() => {
    setAiReplyLoading(id, false)
    setIsTyping(false)
  }, [id])

  // 组件卸载时标记，终止所有异步轮询
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      if (saveSettingsTimerRef.current) {
        clearTimeout(saveSettingsTimerRef.current)
      }
      // 卸载时也清理加载状态，避免残留
      setAiReplyLoading(id, false)
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null

        // ── 第一阶段：只请求角色信息，拿到后立即渲染框架 ──
        const characterData = await charactersApi.getById(id)
        if (!characterData) {
          setLoading(false)
          return
        }
        setCharacter(characterData)

        const defaultAppearance = (characterData.appearance || (characterData.appearanceTags as unknown as string) || '')
        const styleMap: Record<string, string> = {
          '动漫': 'anime', '写实': 'photorealistic', '插画': 'oil_painting',
          '水彩': 'oil_painting', '赛博朋克': 'anime', '像素风': 'anime',
        }
        const defaultImageStyle = (() => {
          const raw = characterData.artStyle || 'anime'
          return styleMap[raw] || raw
        })()
        // 先用 localStorage 快速回填设置（避免设置面板空白闪烁）
        const savedOverride = chatSettingsOverrides[id]
        _setChatSettings({
          appearanceTags: savedOverride?.appearanceTags ?? defaultAppearance,
          voiceRef: savedOverride?.voiceRef ?? (characterData.voiceRef || ''),
          appearanceDesc: savedOverride?.appearanceDesc ?? '',
          imageStyle: savedOverride?.imageStyle ?? defaultImageStyle,
        })

        // ✅ 角色信息已就绪，立刻渲染聊天框架，移除全屏 loading
        setLoading(false)

        // ── 第二阶段：并行异步加载历史/状态/DB设置，不阻塞框架渲染 ──
        if (!token) {
          setHistoryLoading(false)
          return
        }

        const [historyResult, statesResult, settingsResult] = await Promise.allSettled([
          chatApi.getHistory(id, 20),
          chatApi.getStates(id),
          chatApi.getChatSettings(id),
        ])

        // 处理历史消息
        const historyMessages = historyResult.status === 'fulfilled' ? historyResult.value : null
        if (Array.isArray(historyMessages) && historyMessages.length > 0) {
          const PAGE_SIZE = 20
          const formattedMessages: Message[] = historyMessages.map((msg: any) => ({
            id: String(msg.id),
            role: msg.role === 'user' || msg.role === 'USER' ? 'user' : 'assistant',
            content: msg.content,
            timestamp: msg.created_at || new Date().toISOString(),
            imageUrl: msg.image_url,
            audioUrl: msg.audio_url || undefined,
          }))
          setMessages(formattedMessages)
          setHasMoreMessages(historyMessages.length >= PAGE_SIZE)
          formattedMessages.forEach(msg => {
            if (msg.audioUrl) useAppStore.getState().setAudioCache(msg.id, msg.audioUrl)
          })
        }
        setHistoryLoading(false)

        // 处理 DB 聊天设置（覆盖 localStorage 快填）
        const settingsRes = settingsResult.status === 'fulfilled' ? settingsResult.value : null
        if (settingsRes?.success && settingsRes.data) {
          const dbSettings = settingsRes.data
          _setChatSettings({
            appearanceTags: dbSettings.appearance_tags || defaultAppearance,
            voiceRef: dbSettings.voice_ref || characterData.voiceRef || '',
            appearanceDesc: '',
            imageStyle: dbSettings.image_style || defaultImageStyle,
          })
          setChatSettingsOverride(id, {
            appearanceTags: dbSettings.appearance_tags || defaultAppearance,
            voiceRef: dbSettings.voice_ref || characterData.voiceRef || '',
            imageStyle: dbSettings.image_style || defaultImageStyle,
          })
        }

        // 处理状态
        const statesRes = statesResult.status === 'fulfilled' ? statesResult.value : null
        if (statesRes?.success && statesRes.states) {
          const statesDict = statesRes.states
          let formattedStates: CharacterState[] = []
          if (Array.isArray(statesDict)) {
            formattedStates = statesDict.map((s: any) => ({
              name: s.state_name || s.name,
              type: isNaN(Number(s.state_value || s.value)) ? 'string' : 'number',
              value: isNaN(Number(s.state_value || s.value)) ? (s.state_value || s.value) : Number(s.state_value || s.value),
              defaultValue: isNaN(Number(s.state_value || s.value)) ? (s.state_value || s.value) : Number(s.state_value || s.value),
              description: s.desc || s.description || '',
            }))
          } else {
            formattedStates = Object.entries(statesDict).map(([name, data]: [string, any]) => ({
              name,
              type: isNaN(Number(data.value)) ? 'string' : 'number',
              value: isNaN(Number(data.value)) ? data.value : Number(data.value),
              defaultValue: isNaN(Number(data.value)) ? data.value : Number(data.value),
              description: data.desc || '',
            }))
          }
          setCurrentStates(formattedStates)
        }

      } catch (error) {
        console.error('Failed to load chat data:', error)
        setLoading(false)
        setHistoryLoading(false)
      }
    }
    loadData()
  }, [id])

  // 加载更多历史消息（上滑分页）
  const handleLoadMore = useCallback(async () => {
    if (isLoadingMore || !hasMoreMessages || messages.length === 0) return
    const oldestId = Number(messages[0].id)
    if (!oldestId) return
    setIsLoadingMore(true)
    try {
      const older = await chatApi.getHistory(id, 20, oldestId)
      if (Array.isArray(older) && older.length > 0) {
        const formattedOlder: Message[] = older.map((msg: any) => ({
          id: String(msg.id),
          role: msg.role === 'user' || msg.role === 'USER' ? 'user' : 'assistant',
          content: msg.content,
          timestamp: msg.created_at || new Date().toISOString(),
          imageUrl: msg.image_url,
          audioUrl: msg.audio_url || undefined,
        }))
        // 记住滚动位置，追加到顶部后恢复
        const container = messagesContainerRef.current
        const prevScrollHeight = container?.scrollHeight ?? 0
        setMessages(prev => [...formattedOlder, ...prev])
        setHasMoreMessages(older.length >= 20)
        formattedOlder.forEach(msg => {
          if (msg.audioUrl) useAppStore.getState().setAudioCache(msg.id, msg.audioUrl)
        })
        // 保持滚动位置不变（加载完毕后撑高了 top，补偿回去）
        requestAnimationFrame(() => {
          if (container) {
            container.scrollTop = container.scrollHeight - prevScrollHeight
          }
        })
      } else {
        setHasMoreMessages(false)
      }
    } catch (e) {
      console.error('加载更多失败:', e)
    } finally {
      setIsLoadingMore(false)
    }
  }, [id, isLoadingMore, hasMoreMessages, messages])

  // 加载音色预设列表
  useEffect(() => {
    chatApi.getVoicePresets().then(res => {
      if (res?.success && res.presets) {
        setVoicePresets(res.presets)
      }
    }).catch(console.error)
  }, [])

  // 试听音色
  const handleVoicePreview = useCallback((voiceId: string, previewUrl: string) => {
    // 如果当前正在播放该音色，则停止
    if (playingVoiceId === voiceId) {
      previewAudioRef.current?.pause()
      previewAudioRef.current = null
      setPlayingVoiceId(null)
      return
    }
    // 停止之前的播放
    if (previewAudioRef.current) {
      previewAudioRef.current.pause()
      previewAudioRef.current = null
    }
    // 获取后端地址（去掉 /api 后缀）
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
    const backendBase = apiBase.replace(/\/api$/, '')
    const audioUrl = `${backendBase}${previewUrl}`
    const audio = new Audio(audioUrl)
    previewAudioRef.current = audio
    setPlayingVoiceId(voiceId)
    audio.play().catch(console.error)
    audio.onended = () => {
      setPlayingVoiceId(null)
      previewAudioRef.current = null
    }
    audio.onerror = () => {
      setPlayingVoiceId(null)
      previewAudioRef.current = null
    }
  }, [playingVoiceId])

  const scrollToBottom = (instant = false) => {
    messagesEndRef.current?.scrollIntoView({
      behavior: instant ? 'instant' : 'smooth',
    })
  }

  // 初次加载完成后立即滚动到底部
  useEffect(() => {
    if (!loading) {
      setTimeout(() => scrollToBottom(true), 50)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading])

  // 发送/接收新消息时平滑滚动到底部
  useEffect(() => {
    if (!loading) {
      scrollToBottom()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, isTyping])

  if (loading) {
    // 角色数据加载中：渲染聊天骨架屏（Header + 消息区占位）
    return (
      <div className="flex flex-col h-screen bg-background">
        {/* 骨架 Header */}
        <div className="flex-shrink-0 border-b border-border/50 bg-background/95 backdrop-blur-lg">
          <div className="max-w-4xl mx-auto px-4 md:px-6 lg:px-8 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-secondary animate-pulse" />
                <div className="w-10 h-10 rounded-xl bg-secondary animate-pulse" />
                <div className="space-y-1.5">
                  <div className="w-24 h-4 rounded bg-secondary animate-pulse" />
                  <div className="w-36 h-3 rounded bg-secondary/70 animate-pulse" />
                </div>
              </div>
              <div className="flex gap-2">
                <div className="w-9 h-9 rounded-xl bg-secondary animate-pulse" />
                <div className="w-9 h-9 rounded-xl bg-secondary animate-pulse" />
              </div>
            </div>
          </div>
        </div>
        {/* 骨架消息区 */}
        <div className="flex-1 overflow-hidden px-4 md:px-6 lg:px-8 py-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className={`flex gap-3 ${i % 2 === 1 ? 'flex-row-reverse' : ''}`}>
                {i % 2 === 0 && <div className="w-9 h-9 rounded-xl bg-secondary animate-pulse flex-shrink-0" />}
                <div
                  className="rounded-2xl bg-secondary animate-pulse"
                  style={{ width: `${45 + (i * 13) % 30}%`, height: `${48 + (i * 17) % 32}px` }}
                />
              </div>
            ))}
          </div>
        </div>
        {/* 骨架输入框 */}
        <div className="flex-shrink-0 border-t border-border/50 px-4 md:px-6 lg:px-8 py-3">
          <div className="max-w-4xl mx-auto">
            <div className="h-12 rounded-2xl bg-secondary animate-pulse" />
          </div>
        </div>
      </div>
    )
  }

  if (!character) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <AuthModal />
        <div className="text-center px-4">
          <h1 className="text-2xl font-semibold mb-4">角色不存在</h1>
          <Button onClick={() => router.push('/')} variant="outline" className="rounded-xl">
            返回首页
          </Button>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <AuthModal />
        <div className="text-center px-4">
          <h1 className="text-2xl font-semibold mb-4">请先登录</h1>
          <Button onClick={() => setAuthModal(true, 'login')} className="rounded-xl">
            立即登录
          </Button>
        </div>
      </div>
    )
  }

  const handleSendMessage = async (overrideContent?: string) => {
    const content = overrideContent ?? inputValue
    if (!content.trim() || isTyping || isSendingRef.current) return
    isSendingRef.current = true

    // Check credits
    if (user.credits < 1) {
      isSendingRef.current = false
      setCreditsAction({
        amount: 1,
        action: '发送消息',
        callback: () => { },
      })
      setShowCreditsDialog(true)
      return
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content,
      timestamp: new Date().toISOString(),
    }

    addMessage(id, userMessage)
    setMessages(prev => [...prev, userMessage])
    if (!overrideContent) setInputValue('')
    setIsTyping(true)
    setAiReplyLoading(id, true)
    setPendingChoices([])

    try {
      const response = await chatApi.sendMessage(id, content, storyMode)
      if (response.success && response.data) {
        deductCredits(1)
        const aiMessage: Message = {
          id: String(response.data.id),
          role: 'assistant',
          content: response.data.content,
          timestamp: response.data.created_at || new Date().toISOString(),
        }
        addMessage(id, aiMessage)
        setMessages(prev => [...prev, aiMessage])
        if (storyMode && response.choices && response.choices.length > 0) {
          setPendingChoices(response.choices)
        }
        // 异步刷新状态
        chatApi.getStates(id).then(res => {
          if (res?.success && res.states) {
            const dict = res.states
            const fmt: CharacterState[] = Object.entries(dict).map(([name, data]: [string, any]) => ({
              name,
              type: isNaN(Number(data.value)) ? 'string' : 'number',
              value: isNaN(Number(data.value)) ? data.value : Number(data.value),
              defaultValue: isNaN(Number(data.value)) ? data.value : Number(data.value),
              description: data.desc || '',
            }))
            setCurrentStates(fmt)
          }
        }).catch(() => { })
      } else {
        throw new Error(response.message || '发送失败')
      }
    } catch (error: any) {
      toast({
        title: '消息发送失败',
        description: error?.message || '请稍后重试',
        variant: 'destructive',
      })
      // 标记最后一条用户消息为失败（加重试按钮）
      const failedMsg: Message = {
        id: `failed-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        failed: true,
      }
      setMessages(prev => [...prev, failedMsg])
    } finally {
      setIsTyping(false)
      setAiReplyLoading(id, false)
      isSendingRef.current = false
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleChoiceSelect = (choice: string) => {
    setPendingChoices([])
    handleSendMessage(choice)
  }

  // 解析消息内容，区分动作、内心想法和对话
  const parseMessageContent = (content: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = []
    let remaining = content
    let key = 0

    while (remaining.length > 0) {
      // 匹配动作 *动作描述*
      const actionMatch = remaining.match(/^\*([^*]+)\*/)
      if (actionMatch) {
        parts.push(
          <span key={key++} className="text-amber-600 italic">
            *{actionMatch[1]}*
          </span>
        )
        remaining = remaining.slice(actionMatch[0].length)
        continue
      }

      // 匹配内心想法 (内心描述)
      const thoughtMatch = remaining.match(/^\(([^)]+)\)/)
      if (thoughtMatch) {
        parts.push(
          <span key={key++} className="text-purple-600 italic text-sm">
            ({thoughtMatch[1]})
          </span>
        )
        remaining = remaining.slice(thoughtMatch[0].length)
        continue
      }

      // 普通对话文本，找到下一个特殊标记的位置
      const nextAction = remaining.indexOf('*')
      const nextThought = remaining.indexOf('(')
      let endIndex = remaining.length

      if (nextAction !== -1 && nextThought !== -1) {
        endIndex = Math.min(nextAction, nextThought)
      } else if (nextAction !== -1) {
        endIndex = nextAction
      } else if (nextThought !== -1) {
        endIndex = nextThought
      }

      const text = remaining.slice(0, endIndex)
      if (text) {
        parts.push(
          <span key={key++} className="text-foreground">
            {text}
          </span>
        )
      }
      remaining = remaining.slice(endIndex)
    }

    return parts
  }

  const handleTTS = (messageId: string, content: string) => {
    // 已有缓存：直接播放/停止切换，无需再次请求 API
    if (audioCache[messageId]) {
      playAudio(messageId, audioCache[messageId])
      return
    }

    // 正在生成中：禁止重复触发
    if (ttsLoadingIds[messageId]) return

    setCreditsAction({
      amount: 5,
      action: '语音合成',
      callback: async () => {
        const ok = deductCredits(5)
        if (!ok) return
        // 交给全局 store 执行，用户离开页面后仍可后台完成
        startTTS(messageId, content, id, chatSettings.voiceRef || undefined)
      },
    })
    setShowCreditsDialog(true)
  }

  // 判断是否为后端真实消息 ID（时间戳 ID > 10^12，视为本地缓存的旧消息）
  const isBackendMessageId = (msgId: string) => {
    const n = parseInt(msgId)
    return !isNaN(n) && n > 0 && n < 1_000_000_000_000
  }

  const handleGenerateImage = (messageId: string) => {
    // 旧版本缓存的消息用 Date.now() 作 ID，后端不存在，拦截请求
    if (!isBackendMessageId(messageId)) return

    setCreditsAction({
      amount: 10,
      action: '生成图片',
      callback: async () => {
        const ok = deductCredits(10)
        if (!ok) return
        // 立即显示本地加载状态
        setLocalImageLoading(prev => ({ ...prev, [messageId]: true }))
        try {
          // 使用聊天设置中的外貌和画风覆盖（若有），否则后端 fallback 到角色默认値
          const imageOverrides: { appearance_tags?: string; image_style?: string } = {}
          if (chatSettings.appearanceTags) imageOverrides.appearance_tags = chatSettings.appearanceTags
          if (chatSettings.imageStyle) imageOverrides.image_style = chatSettings.imageStyle
          const res = await chatApi.generateImage(messageId, Object.keys(imageOverrides).length ? imageOverrides : undefined)
          if (res.success && res.task_id) {
            // 交给全局 store 轮询，用户离开页面后仍可后台完成
            startImagePoll(messageId, res.task_id)
          }
        } catch (error) {
          console.error('Image generation failed:', error)
          // 出错时清除本地加载状态
          setLocalImageLoading(prev => {
            const next = { ...prev }
            delete next[messageId]
            return next
          })
        }
      },
    })
    setShowCreditsDialog(true)
  }

  const handleResetStates = async () => {
    try {
      const response = await chatApi.resetStates(id)
      if (response.success) {
        // Reload states after reset
        const statesRes = await chatApi.getStates(id)
        if (statesRes.success && statesRes.states) {
          const statesDict = statesRes.states
          const formattedStates: CharacterState[] = Object.entries(statesDict).map(([name, data]: [string, any]) => ({
            name,
            type: isNaN(Number(data.value)) ? 'string' : 'number',
            value: isNaN(Number(data.value)) ? data.value : Number(data.value),
            defaultValue: isNaN(Number(data.value)) ? data.value : Number(data.value),
            description: data.desc || '',
          }))
          setCurrentStates(formattedStates)
        }
      }
    } catch (error) {
      console.error('Failed to reset states:', error)
    }
  }

  const handleClearHistory = async () => {
    try {
      await chatApi.clearHistory(id)  // 删除后端 DB 中的聊天记录
    } catch (e) {
      console.error('清空聊天记录失败:', e)
    }
    clearChatHistory(id)        // 清除 zustand store
    setMessages([])              // 清除本地消息 state
    setMessageImageUrls({})      // 清除本地图片 URL缓存
    clearAllMessageImageUrls()   // 清除 localStorage 中持久化的图片 URL
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden" style={{ height: '100dvh' }}>
      <AuthModal />
      <CreditsDialog
        open={showCreditsDialog}
        onOpenChange={setShowCreditsDialog}
        amount={creditsAction.amount}
        action={creditsAction.action}
        onConfirm={creditsAction.callback}
      />

      {/* Chat Settings Sheet */}
      <Sheet open={showChatSettings} onOpenChange={setShowChatSettings}>
        <SheetContent side="right" className="!w-[320px] sm:!w-[380px] p-0 flex flex-col">
          <SheetHeader className="px-5 pt-5 pb-3 border-b border-border">
            <SheetTitle className="text-base flex items-center gap-2">
              <Settings className="h-4 w-4" />
              聊天设置
            </SheetTitle>
            <SheetDescription className="text-xs">
              为与 {character?.name} 的对话配置画风、外貌和声音
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
            {/* 画风设置 */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Palette className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">画风设置</h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'photorealistic', label: '超写实', desc: 'Photorealistic' },
                  { value: 'showa', label: '昭和画风', desc: 'Showa Anime' },
                  { value: 'anime', label: '二次元', desc: 'Anime 2D' },
                  { value: 'oil_painting', label: '艺术油画', desc: 'Oil Painting' },
                ].map((s) => (
                  <button
                    key={s.value}
                    onClick={() => setChatSettings({ ...chatSettings, imageStyle: s.value })}
                    className={cn(
                      'py-2 px-3 rounded-lg text-xs border transition-all text-left',
                      chatSettings.imageStyle === s.value
                        ? 'bg-foreground text-background border-foreground'
                        : 'bg-secondary/50 border-border hover:bg-secondary'
                    )}
                  >
                    <span className="font-medium">{s.label}</span>
                    <span className={cn('block text-[10px] mt-0.5', chatSettings.imageStyle === s.value ? 'text-background/70' : 'text-muted-foreground')}>{s.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 外貌设置 */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Palette className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium flex-1">外貌设置</h3>
                {/* 清除按钮 */}
                {chatSettings.appearanceTags && (
                  <button
                    onClick={() => setChatSettings({ ...chatSettings, appearanceTags: '' })}
                    className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors px-1.5 py-0.5 rounded-md hover:bg-secondary"
                  >
                    <X className="h-3 w-3" />
                    清除
                  </button>
                )}
                {/* AI润色按钮 */}
                <button
                  disabled={isPolishing || !chatSettings.appearanceTags.trim()}
                  onClick={() => {
                    setCreditsAction({
                      amount: 5,
                      action: 'AI润色外貌描述',
                      callback: async () => {
                        setIsPolishing(true)
                        try {
                          const res = await chatApi.polishAppearance(chatSettings.appearanceTags)
                          if (res.success && res.polished) {
                            setChatSettings({ ...chatSettings, appearanceTags: res.polished })
                          }
                        } catch (e: unknown) {
                          console.error('AI润色失败:', e)
                        } finally {
                          setIsPolishing(false)
                        }
                      },
                    })
                    setShowCreditsDialog(true)
                  }}
                  className={cn(
                    'flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md transition-colors',
                    isPolishing || !chatSettings.appearanceTags.trim()
                      ? 'text-muted-foreground/50 cursor-not-allowed'
                      : 'text-purple-500 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950/30'
                  )}
                >
                  {isPolishing ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Sparkles className="h-3 w-3" />
                  )}
                  AI润色 · 5积分
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                描述角色的<strong className="text-foreground">固定外貌特征</strong>，将作为文生图 prompt 的外貌部分参与生成。场景、动作、服装等由 AI 自动从对话内容中分析。
              </p>
              <Textarea
                value={chatSettings.appearanceTags}
                onChange={(e) => setChatSettings({ ...chatSettings, appearanceTags: e.target.value })}
                placeholder="例：A young woman in her mid-20s with long silver hair, striking red eyes, flawless porcelain skin, natural blush on cheeks, slender figure..."
                className="min-h-[100px] rounded-xl bg-secondary/50 border-0 text-sm resize-none"
              />
              <p className="text-[10px] text-muted-foreground mt-1.5">
                仅填写不变的外貌特征：发色、瞳色、肤色、体型、面部特征等。服装与场景由对话自动生成。
              </p>
            </div>

            {/* 声音设置 */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Volume2 className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">声音设置</h3>
              </div>
              <p className="text-xs text-muted-foreground mb-3">
                点击音色卡片即可选择，点击试听按鈕可预览音色效果
              </p>
              {voicePresets.length > 0 ? (
                <div className="space-y-2">
                  {voicePresets.map((preset) => (
                    <div
                      key={preset.id}
                      onClick={() => setChatSettings({ ...chatSettings, voiceRef: preset.reference_id })}
                      className={cn(
                        'flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all',
                        chatSettings.voiceRef === preset.reference_id
                          ? 'border-foreground bg-foreground/5'
                          : 'border-border bg-secondary/30 hover:border-foreground/40 hover:bg-secondary/60'
                      )}
                    >
                      {/* 音色信息 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{preset.name}</span>
                          {chatSettings.voiceRef === preset.reference_id && (
                            <span className="text-[10px] bg-foreground text-background px-1.5 py-0.5 rounded-full">已选</span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5">{preset.description}</p>
                      </div>
                      {/* 试听按鈕 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleVoicePreview(preset.id, preset.preview_url)
                        }}
                        className={cn(
                          'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all',
                          playingVoiceId === preset.id
                            ? 'bg-foreground text-background'
                            : 'bg-secondary hover:bg-secondary/80 text-muted-foreground hover:text-foreground'
                        )}
                        title={playingVoiceId === preset.id ? '停止试听' : '试听音色'}
                      >
                        {playingVoiceId === preset.id ? (
                          <Square className="h-3.5 w-3.5" />
                        ) : (
                          <Play className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground text-center py-4">加载音色列表中...</div>
              )}
            </div>
          </div>

          {/* 剧情模式 */}
          <div
            onClick={() => setStoryMode(!storyMode)}
            className="relative rounded-2xl p-4 cursor-pointer transition-all border-2 border-border bg-secondary/30 hover:border-border/80 hover:bg-secondary/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">📖</span>
                  <span className="text-sm font-semibold">剧情模式</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-muted text-muted-foreground">Beta</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  开启后按剧情选项互动，AI 将按故事逻辑推进
                </p>
              </div>
              <Switch
                checked={storyMode}
                onCheckedChange={setStoryMode}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          </div>

          <div className="px-5 py-4 border-t border-border">
            <Button
              className="w-full rounded-xl h-10"
              onClick={() => setShowChatSettings(false)}
            >
              确认
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Chat Header - Full width, no global header */}
      <div className="flex-shrink-0 border-b border-border/50 bg-background/95 backdrop-blur-lg">
        <div className="max-w-4xl mx-auto px-4 md:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => {
                  if (hasActiveTasks()) {
                    setPendingNavigation(() => () => router.push('/chats'))
                    setShowExitConfirm(true)
                  } else {
                    router.push('/chats')
                  }
                }}
                className="p-2 rounded-xl hover:bg-secondary transition-colors flex-shrink-0"
                title="返回最近聊天"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <Avatar className="h-10 w-10 rounded-xl border-2 border-border flex-shrink-0">
                <AvatarImage src={character.avatar} />
                <AvatarFallback className="rounded-xl bg-secondary text-sm">
                  {character.name.slice(0, 2)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <h2 className="font-semibold truncate">{character.name}</h2>
                <p className="text-xs text-muted-foreground truncate">{character.description}</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              {/* Status Sheet Trigger */}
              <Sheet>
                <SheetTrigger asChild>
                  <button className="p-2 rounded-xl hover:bg-secondary transition-colors flex-shrink-0">
                    <Activity className="h-5 w-5" />
                  </button>
                </SheetTrigger>
                <SheetContent className="!w-[280px] sm:!w-[320px] p-0">
                  <SheetHeader className="px-4 pt-4 pb-2">
                    <SheetTitle className="text-base">角色状态</SheetTitle>
                    <SheetDescription className="text-xs">
                      {character.name} 的当前状态
                    </SheetDescription>
                  </SheetHeader>
                  <div className="flex-1 overflow-y-auto px-4 py-2">
                    <div className="space-y-3">
                      {currentStates.map((state) => (
                        <div key={state.name} className="space-y-1.5">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground text-xs">{state.name}</span>
                            <span className="font-medium text-xs">{String(state.value)}</span>
                          </div>
                          {typeof state.value === 'number' && (
                            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-foreground rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(100, Math.max(0, state.value))}%` }}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                      {currentStates.length === 0 && (
                        <p className="text-xs text-muted-foreground text-center py-6">
                          暂无状态数据
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="px-4 py-3 border-t">
                    <Button
                      onClick={handleResetStates}
                      variant="outline"
                      size="sm"
                      className="w-full rounded-lg text-xs"
                    >
                      <RotateCcw className="mr-2 h-3 w-3" />
                      重置状态
                    </Button>
                  </div>
                </SheetContent>
              </Sheet>

              {/* More Actions */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="p-2 rounded-xl hover:bg-secondary transition-colors flex-shrink-0">
                    <MoreVertical className="h-5 w-5" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48 rounded-xl p-2">
                  <DropdownMenuItem
                    onClick={() => setShowChatSettings(true)}
                    className="rounded-lg cursor-pointer"
                  >
                    <Settings className="mr-3 h-4 w-4" />
                    聊天设置
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleClearHistory}
                    className="rounded-lg cursor-pointer text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-3 h-4 w-4" />
                    清空记录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <main ref={messagesContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden px-4 md:px-6 lg:px-8 py-2 md:py-3">
        <div className="max-w-4xl mx-auto space-y-3 md:space-y-4">
          {/* 加载更多历史 */}
          {hasMoreMessages && (
            <div className="flex justify-center py-2">
              <button
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-lg hover:bg-secondary/60 disabled:opacity-50"
              >
                {isLoadingMore ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin" />加载中...</>
                ) : (
                  <>查看更多历史消息</>
                )}
              </button>
            </div>
          )}

          {/* 历史消息加载中骨架 */}
          {historyLoading && (
            <div className="space-y-4 pb-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className={`flex gap-3 ${i % 2 === 1 ? 'flex-row-reverse' : ''}`}>
                  {i % 2 === 0 && <div className="w-8 h-8 md:w-10 md:h-10 rounded-xl bg-secondary animate-pulse flex-shrink-0" />}
                  <div
                    className="rounded-2xl bg-secondary/80 animate-pulse"
                    style={{ width: `${40 + (i * 17) % 35}%`, height: `${44 + (i * 19) % 36}px` }}
                  />
                </div>
              ))}
            </div>
          )}
          {/* Greeting - show when no messages and history loaded */}
          {!historyLoading && messages.length === 0 && (
            <div className="flex gap-2.5 md:gap-4 animate-fade-in">
              <Avatar className="h-8 w-8 md:h-10 md:w-10 rounded-lg md:rounded-xl border-2 border-border flex-shrink-0">
                <AvatarImage src={character.avatar} />
                <AvatarFallback className="rounded-lg md:rounded-xl bg-secondary text-xs md:text-sm">
                  {character.name.slice(0, 2)}
                </AvatarFallback>
              </Avatar>
              <div className="glass rounded-xl md:rounded-2xl rounded-tl-md p-3 md:p-5 max-w-[85%] md:max-w-[80%]">
                <p className="text-sm md:text-base leading-relaxed whitespace-pre-wrap">{character.greeting}</p>
              </div>
            </div>
          )}

          {/* Messages from history */}
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={cn(
                'flex gap-2.5 md:gap-4 animate-fade-in',
                message.role === 'user' ? 'flex-row-reverse' : ''
              )}
              style={{ animationDelay: `${index * 0.03}s` }}
            >
              {message.role === 'assistant' ? (
                <Avatar className="h-8 w-8 md:h-10 md:w-10 rounded-lg md:rounded-xl border-2 border-border flex-shrink-0">
                  <AvatarImage src={character.avatar} />
                  <AvatarFallback className="rounded-lg md:rounded-xl bg-secondary text-xs md:text-sm">
                    {character.name.slice(0, 2)}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <Avatar className="h-8 w-8 md:h-10 md:w-10 rounded-lg md:rounded-xl border-2 border-border flex-shrink-0">
                  <AvatarImage src={user.avatar} />
                  <AvatarFallback className="rounded-lg md:rounded-xl bg-foreground text-background text-xs md:text-sm">
                    {user.username[0].toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              )}

              <div
                className={cn(
                  'max-w-[85%] md:max-w-[80%]'
                )}
              >
                <div
                  className={cn(
                    'rounded-xl md:rounded-2xl p-3 md:p-5',
                    message.role === 'user'
                      ? 'bg-foreground text-background rounded-tr-md'
                      : 'glass rounded-tl-md'
                  )}
                >
                  <div className={cn(
                    "text-sm md:text-base leading-relaxed whitespace-pre-wrap text-left",
                    message.role === 'user' && "text-background"
                  )}>
                    {message.role === 'user' ? message.content : parseMessageContent(message.content)}
                  </div>
                  {(messageImageUrls[message.id] || message.imageUrl) && (
                    <img
                      src={messageImageUrls[message.id] || message.imageUrl}
                      alt="Generated"
                      className="mt-3 md:mt-4 rounded-lg md:rounded-xl max-w-[280px] md:max-w-[320px] w-full object-contain cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => setLightboxUrl(messageImageUrls[message.id] || message.imageUrl || null)}
                    />
                  )}
                </div>

                {/* Message Actions */}
                {message.role === 'assistant' && !message.failed && (
                  <div className="flex gap-1.5 md:gap-2 mt-1.5 md:mt-2">
                    <button
                      onClick={() => handleTTS(message.id, message.content)}
                      disabled={!!ttsLoadingIds[message.id]}
                      className={cn(
                        'p-1.5 md:p-2 rounded-md md:rounded-lg transition-colors disabled:opacity-50',
                        playingMessageId === message.id
                          ? 'text-foreground bg-secondary hover:bg-secondary/80'
                          : audioCache[message.id]
                            ? 'text-foreground bg-secondary/60 hover:bg-secondary/80'
                            : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                      )}
                      title={
                        ttsLoadingIds[message.id] ? '正在生成语音...' :
                          playingMessageId === message.id ? '点击停止' :
                            audioCache[message.id] ? '重新播放' : '语音播放'
                      }
                    >
                      {ttsLoadingIds[message.id]
                        ? <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 animate-spin" />
                        : playingMessageId === message.id
                          ? <Square className="h-3.5 w-3.5 md:h-4 md:w-4" />
                          : <Volume2 className="h-3.5 w-3.5 md:h-4 md:w-4" />
                      }
                    </button>
                    <button
                      onClick={() => handleGenerateImage(message.id)}
                      disabled={!!imageLoadingIds[message.id] || !!localImageLoading[message.id] || !isBackendMessageId(message.id)}
                      className="p-1.5 md:p-2 rounded-md md:rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-30"
                      title={isBackendMessageId(message.id) ? '生成图片' : '该消息为历史缓存，不支持生成图片'}
                    >
                      {(imageLoadingIds[message.id] || localImageLoading[message.id]) ? <Loader2 className="h-3.5 w-3.5 md:h-4 md:w-4 animate-spin" /> : <ImageIcon className="h-3.5 w-3.5 md:h-4 md:w-4" />}
                    </button>
                  </div>
                )}

                {/* 失败重试按钮 */}
                {message.failed && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-destructive flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      发送失败
                    </span>
                    <button
                      onClick={() => {
                        // 移除失败消息，重新发送最近一条用户消息
                        const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
                        setMessages(prev => prev.filter(m => m.id !== message.id))
                        if (lastUserMsg) handleSendMessage(lastUserMsg.content)
                      }}
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-secondary transition-colors"
                    >
                      <RefreshCcw className="h-3 w-3" />
                      重试
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Story Mode Choices */}
          {storyMode && pendingChoices.length > 0 && !isTyping && (
            <div className="flex flex-col gap-2 pl-12 md:pl-16 mt-1 animate-fade-in">
              {pendingChoices.map((choice, i) => (
                <button
                  key={i}
                  onClick={() => handleChoiceSelect(choice)}
                  className="text-left text-sm md:text-base leading-relaxed px-4 py-2.5 rounded-xl md:rounded-2xl rounded-tl-md border border-border/60 bg-secondary/30 hover:bg-secondary/60 hover:border-foreground/30 transition-all"
                >
                  {choice}
                </button>
              ))}
            </div>
          )}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex gap-2.5 md:gap-4 animate-fade-in">
              <Avatar className="h-8 w-8 md:h-10 md:w-10 rounded-lg md:rounded-xl border-2 border-border flex-shrink-0">
                <AvatarImage src={character.avatar} />
                <AvatarFallback className="rounded-lg md:rounded-xl bg-secondary text-xs md:text-sm">
                  {character.name.slice(0, 2)}
                </AvatarFallback>
              </Avatar>
              <div className="glass rounded-xl md:rounded-2xl rounded-tl-md px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-background px-4 md:px-6 lg:px-8 py-2 md:py-3">
        <div className="max-w-4xl mx-auto glass rounded-xl md:rounded-2xl p-2 md:p-3">
          <div className="flex gap-2 md:gap-4">
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`对 ${character.name} 说点什么...`}
              className="min-h-[36px] md:min-h-[44px] max-h-[80px] md:max-h-[160px] rounded-lg md:rounded-xl bg-secondary/50 border-0 resize-none text-sm md:text-base py-2"
              rows={1}
            />
            <Button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isTyping}
              className="h-9 w-9 md:h-11 md:w-11 rounded-lg md:rounded-xl flex-shrink-0"
            >
              <Send className="h-4 w-4 md:h-5 md:w-5" />
            </Button>
          </div>
          <div className="flex items-center justify-between mt-1.5 md:mt-2">
            <button
              onClick={() => {
                const textarea = document.querySelector('textarea') as HTMLTextAreaElement
                if (textarea) {
                  const start = textarea.selectionStart
                  const end = textarea.selectionEnd
                  const selectedText = inputValue.slice(start, end)
                  const beforeText = inputValue.slice(0, start)
                  const afterText = inputValue.slice(end)

                  // 如果选中了文本，直接包裹；否则插入动作模板
                  let actionText: string
                  if (selectedText) {
                    // 有选中文本，检查是否已经包裹了*
                    const alreadyWrapped = selectedText.startsWith('*') && selectedText.endsWith('*')
                    actionText = alreadyWrapped ? selectedText : `*${selectedText}*`
                  } else {
                    // 无选中文本，检查光标前后是否已经有*
                    const hasStarBefore = beforeText.endsWith('*')
                    const hasStarAfter = afterText.startsWith('*')
                    if (hasStarBefore && hasStarAfter) {
                      // 光标已经在**之间，只插入文字
                      actionText = '动作'
                    } else if (hasStarBefore) {
                      // 光标前面有*，后面加*动作
                      actionText = '动作*'
                    } else if (hasStarAfter) {
                      // 光标后面有*，前面加动作*
                      actionText = '*动作'
                    } else {
                      // 都没有，完整插入*动作*
                      actionText = '*动作*'
                    }
                  }

                  const newValue = beforeText + actionText + afterText
                  setInputValue(newValue)
                  setTimeout(() => {
                    textarea.focus()
                    // 选中"动作"二字方便替换
                    const actionStart = start + (actionText.startsWith('*') ? 1 : 0)
                    const actionEnd = actionStart + (selectedText ? (selectedText.startsWith('*') ? selectedText.length - 2 : selectedText.length) : 2)
                    textarea.setSelectionRange(actionStart, actionEnd)
                  }, 0)
                }
              }}
              className="text-[10px] md:text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-secondary/50 flex items-center gap-1"
            >
              <span className="text-amber-500">*</span>
              动作
            </button>
            <p className="text-[10px] md:text-xs text-muted-foreground text-center flex-1">
              发送消息消耗 1 积分 · 当前余额 {user.credits} 积分
            </p>
            <div className="w-12" />
          </div>
        </div>
      </div>

      {/* 任务进度悬浮提示 */}
      {hasActiveTasks() && (
        <div className="fixed bottom-24 md:bottom-28 left-1/2 -translate-x-1/2 z-40">
          <div className="bg-foreground text-background px-4 py-2 rounded-full shadow-lg flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <div className="flex flex-col">
              {getActiveTaskSummary().map((task, idx) => (
                <span key={idx} className="text-xs font-medium">
                  {task.message}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 退出确认弹窗 */}
      <AlertDialog open={showExitConfirm} onOpenChange={setShowExitConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              正在生成中
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <span className="block">以下任务正在进行中，退出可能会导致生成失败：</span>
              <ul className="space-y-1 ml-4">
                {getActiveTaskSummary().map((task, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm">
                    {task.type === 'ai-reply' && <Sparkles className="h-4 w-4 text-purple-500" />}
                    {task.type === 'image' && <ImageIcon className="h-4 w-4 text-blue-500" />}
                    {task.type === 'tts' && <Mic className="h-4 w-4 text-green-500" />}
                    {task.message}
                  </li>
                ))}
              </ul>
              <span className="block text-amber-600 font-medium">确定要退出吗？</span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingNavigation(null)}>
              继续等待
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pendingNavigation) {
                  pendingNavigation()
                }
                setPendingNavigation(null)
              }}
              className="bg-destructive hover:bg-destructive/90"
            >
              确认退出
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 图片灯箱 */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm"
          onClick={() => setLightboxUrl(null)}
        >
          <button
            className="absolute top-4 right-4 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 rounded-full w-9 h-9 flex items-center justify-center transition-colors"
            onClick={() => setLightboxUrl(null)}
          >
            ✕
          </button>
          <img
            src={lightboxUrl}
            alt="Preview"
            className="max-w-[92vw] max-h-[88vh] object-contain rounded-xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}
