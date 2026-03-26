'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { CreditsDialog } from '@/components/credits-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { useAppStore } from '@/lib/store'
import { charactersApi, chatApi } from '@/lib/api'
import type { CharacterState } from '@/lib/api'
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  User,
  Brain,
  Sliders,
  Book,
  Palette,
  Volume2,
  Check,
  X,
  Plus,
  Play,
  Square,
  Wand2,
  Loader2,
  Upload,
  ImageIcon,
  ChevronUp,
  ChevronDown,
  Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

const steps = [
  { icon: User, title: '公开信息', description: '设置角色的基本信息' },
  { icon: Brain, title: '人设设置', description: '定义角色的性格和场景' },
  { icon: Sliders, title: '状态设计', description: '配置动态状态变量' },
  { icon: Book, title: '世界观', description: '构建故事背景' },
  { icon: Palette, title: '文生图', description: '设置外貌和画风' },
  { icon: Volume2, title: '语音设置', description: '选择声音特征' },
]

const artStyles = [
  { value: 'photorealistic', label: '超写实', desc: 'Photorealistic' },
  { value: 'showa', label: '昭和画风', desc: 'Showa Anime' },
  { value: 'anime', label: '二次元', desc: 'Anime 2D' },
  { value: 'oil_painting', label: '艺术油画', desc: 'Oil Painting' },
]

export default function CreateCharacterPage() {
  const router = useRouter()
  const { user, deductCredits, setAuthModal } = useAppStore()
  const { toast } = useToast()
  const [currentStep, setCurrentStep] = useState(0)
  const [showCreditsDialog, setShowCreditsDialog] = useState(false)
  const [isAiGenerating, setIsAiGenerating] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')
  const [showAiMode, setShowAiMode] = useState(false)

  // 头像状态
  const [avatarUrl, setAvatarUrl] = useState<string>('')
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const avatarInputRef = useRef<HTMLInputElement>(null)

  // 头像生成轮询状态（已废弃，后台异步不阻塞）
  // 音色预设列表
  type VoicePreset = { id: string; name: string; description: string; reference_id: string; preview_url: string }
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([])
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null)
  const previewAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    chatApi.getVoicePresets().then(res => {
      if (res?.success && res.presets) setVoicePresets(res.presets)
    }).catch(console.error)
  }, [])

  const handleVoicePreview = useCallback((voiceId: string, previewUrl: string) => {
    if (playingVoiceId === voiceId) {
      previewAudioRef.current?.pause()
      previewAudioRef.current = null
      setPlayingVoiceId(null)
      return
    }
    previewAudioRef.current?.pause()
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
    const backendBase = apiBase.replace(/\/api$/, '')
    const audio = new Audio(`${backendBase}${previewUrl}`)
    previewAudioRef.current = audio
    setPlayingVoiceId(voiceId)
    audio.play().catch(console.error)
    audio.onended = () => { setPlayingVoiceId(null); previewAudioRef.current = null }
    audio.onerror = () => { setPlayingVoiceId(null); previewAudioRef.current = null }
  }, [playingVoiceId])

  const [formData, setFormData] = useState({
    name: '',
    title: '',
    description: '',
    tags: [] as string[],
    visibility: 'public' as 'public' | 'private',
    personality: '',
    userRole: '',
    scene: '',
    greeting: '',
    states: [] as CharacterState[],
    storyline: '',
    worldSetting: '',
    appearance: '',
    artStyle: 'anime',
    initialClothing: '',
    voiceRef: '',
    plot_milestones: [] as { title: string; description: string }[],
  })

  const [newTag, setNewTag] = useState('')
  const [newState, setNewState] = useState({
    name: '',
    type: 'string' as 'string' | 'number',
    defaultValue: '',
    description: '',
  })

  if (!user) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        <div className="pt-24 md:pt-32 px-4 text-center">
          <h1 className="text-lg md:text-2xl font-semibold mb-3 md:mb-4">请先登录</h1>
          <Button
            onClick={() => setAuthModal(true, 'login')}
            className="rounded-lg md:rounded-xl h-9 md:h-10 text-sm"
          >
            立即登录
          </Button>
        </div>
      </div>
    )
  }

  const handleAddTag = () => {
    if (newTag && !formData.tags.includes(newTag)) {
      setFormData({ ...formData, tags: [...formData.tags, newTag] })
      setNewTag('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) })
  }

  const handleAddState = () => {
    if (newState.name && newState.defaultValue) {
      setFormData({
        ...formData,
        states: [
          ...formData.states,
          {
            name: newState.name,
            type: newState.type,
            value: newState.type === 'number' ? Number(newState.defaultValue) : newState.defaultValue,
            defaultValue: newState.type === 'number' ? Number(newState.defaultValue) : newState.defaultValue,
            description: newState.description,
          },
        ],
      })
      setNewState({ name: '', type: 'string', defaultValue: '', description: '' })
    }
  }

  const handleRemoveState = (name: string) => {
    setFormData({
      ...formData,
      states: formData.states.filter((s) => s.name !== name),
    })
  }

  // 上传头像
  const handleAvatarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIsUploadingAvatar(true)
    try {
      const res = await charactersApi.uploadAvatar(file)
      if (res.success) {
        setAvatarUrl(res.url)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '上传失败'
      toast({ title: '上传失败', description: msg, variant: 'destructive' })
    } finally {
      setIsUploadingAvatar(false)
      if (avatarInputRef.current) avatarInputRef.current.value = ''
    }
  }

  // AI 智能创建 - 调用真实 API
  const handleAiGenerate = async () => {
    if (!aiPrompt) return
    setIsAiGenerating(true)
    try {
      const res = await charactersApi.generate(aiPrompt)
      if (res.success && res.data) {
        const d = res.data as Record<string, unknown>
        setFormData(prev => ({
          ...prev,
          name: (d.name as string) || prev.name,
          description: (d.public_summary as string) || (d.description as string) || prev.description,
          tags: Array.isArray(d.tags) ? d.tags as string[] : (typeof d.tags === 'string' ? (d.tags as string).split(',').map((t: string) => t.trim()).filter(Boolean) : prev.tags),
          personality: (d.persona as string) || (d.personality as string) || prev.personality,
          userRole: (d.user_persona as string) || (d.userRole as string) || prev.userRole,
          scene: (d.scenario as string) || (d.scene as string) || prev.scene,
          greeting: (d.greeting as string) || prev.greeting,
          storyline: (d.storyline as string) || prev.storyline,
          worldSetting: (d.world_setting as string) || (d.worldSetting as string) || prev.worldSetting,
          appearance: (d.appearance as string) || (typeof d.appearance_tags === 'string' ? d.appearance_tags as string : '') || prev.appearance,
          artStyle: (d.image_style as string) || (d.artStyle as string) || prev.artStyle,
          initialClothing: (d.clothing_state as string) || (d.initialClothing as string) || prev.initialClothing,
          states: Array.isArray(d.states)
            ? (d.states as Array<Record<string, unknown>>).map(s => {
              // 兼容后端格式 {state_name, display_name, state_value, default_value} 和前端格式 {name, value, defaultValue}
              const name = (s.display_name as string) || (s.name as string) || (s.state_name as string) || ''
              const rawVal = s.state_value ?? s.value ?? s.default_value ?? s.defaultValue ?? '0'
              const rawDefault = s.default_value ?? s.defaultValue ?? rawVal ?? '0'
              const numericVal = Number(rawVal)
              const isNumber = !isNaN(numericVal) && rawVal !== ''
              return {
                name,
                type: isNumber ? 'number' as const : 'string' as const,
                value: isNumber ? numericVal : String(rawVal),
                defaultValue: isNumber ? Number(rawDefault) : String(rawDefault),
                description: (s.description as string) || '',
              }
            })
            : prev.states,
          voiceRef: (d.voice_reference_id as string) || (d.voiceRef as string) || prev.voiceRef,
        }))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'AI 生成失败'
      toast({ title: 'AI 生成失败', description: msg, variant: 'destructive' })
    } finally {
      setIsAiGenerating(false)
      setShowAiMode(false)
      setCurrentStep(0)
    }
  }

  // 后台轮询头像生成状态（对齐 store.startImagePoll 逻辑，递归 setTimeout，不阻塞页面跳转）
  const startAvatarPollBackground = (roleId: string, taskId: string) => {
    const deadline = Date.now() + 5 * 60 * 1000 // 最多等 5 分钟

    const poll = async () => {
      if (Date.now() > deadline) {
        console.warn('[Avatar] 头像生成超时放弃')
        return
      }
      try {
        const statusRes = await chatApi.checkImageStatus(taskId)
        const s = (statusRes.status || '').toUpperCase()

        if (s === 'COMPLETED' || s === 'SUCCESS') {
          if (statusRes.image_url) {
            try {
              console.log('[Avatar] 保存头像到角色:', roleId, statusRes.image_url)
              await charactersApi.saveAvatar(roleId, statusRes.image_url)
              console.log('[Avatar] 头像保存成功')
            } catch (err) {
              console.error('[Avatar] 保存头像失败:', err)
            }
          }
        } else if (s === 'ERROR' || s === 'FAILED') {
          console.warn('[Avatar] 头像生成失败')
        } else {
          // PENDING / PROCESSING：继续等待
          setTimeout(poll, 2500)
        }
      } catch {
        // 网络抖动不中断，继续重试
        if (Date.now() < deadline) {
          setTimeout(poll, 3000)
        }
      }
    }

    // 首次延迟 3 秒再开始（留时间给生图服务处理）
    setTimeout(poll, 3000)
  }

  const handleSubmit = () => {
    setShowCreditsDialog(true)
  }

  const handleConfirmCreate = async () => {
    if (!user) return

    console.log('[Create] 开始创建角色，avatarUrl:', avatarUrl, '是否生成头像:', !avatarUrl)

    const ok = deductCredits(50)
    if (!ok) {
      toast({ title: '积分不足', description: '积分不足，无法创建角色', variant: 'destructive' })
      return
    }

    setIsCreating(true)
    try {
      console.log('[Create] 调用 charactersApi.create...')
      const { plot_milestones, ...restFormData } = formData
      const response = await charactersApi.create({
        ...restFormData,
        plot_milestones: plot_milestones.length > 0 ? JSON.stringify(plot_milestones) : undefined,
        avatar: avatarUrl || '',
        isSystem: false,
        creatorId: user.id,
        dialogueCount: 0,
        createdAt: new Date().toISOString(),
      })
      console.log('[Create] 创建角色响应:', response)

      if (response.success) {
        const roleId = String(response.data.id)
        console.log('[Create] 角色创建成功，ID:', roleId)

        // 若用户没有手动上传头像，后台异步生成头像（不阻塞页面跳转）
        if (!avatarUrl) {
          console.log('[Create] 未上传头像，开始调用 generateAvatar...')
          try {
            const genRes = await charactersApi.generateAvatar(roleId)
            console.log('[Create] generateAvatar 响应:', genRes)
            if (genRes.success && genRes.task_id) {
              console.log('[Create] 启动后台头像轮询，task_id:', genRes.task_id)
              startAvatarPollBackground(roleId, genRes.task_id)
            } else {
              console.error('[Create] generateAvatar 返回失败:', genRes)
            }
          } catch (err) {
            console.error('[Create] 生成头像异常:', err)
          }
        } else {
          console.log('[Create] 已上传头像，跳过 AI 生成')
        }

        console.log('[Create] 准备跳转到角色页:', roleId)
        router.push(`/character/${roleId}`)
      }
    } catch (err: unknown) {
      console.error('[Create] 创建角色异常:', err)
      const msg = err instanceof Error ? err.message : '创建失败'
      toast({ title: '创建失败', description: msg, variant: 'destructive' })
    } finally {
      setIsCreating(false)
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return formData.name && formData.description
      case 1:
        return formData.personality && formData.greeting
      default:
        return true
    }
  }

  // Step 0 头像上传区域
  const renderAvatarUpload = () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
    const backendBase = apiBase.replace(/\/api$/, '')
    const previewSrc = avatarUrl
      ? (avatarUrl.startsWith('http') ? avatarUrl : `${backendBase}${avatarUrl}`)
      : null

    return (
      <div className="flex items-center gap-4 mb-5 md:mb-6">
        {/* 头像预览圆形区域 */}
        <div className="relative flex-shrink-0">
          <div
            className="relative h-20 w-20 md:h-24 md:w-24 rounded-full overflow-hidden border-2 border-border flex items-center justify-center text-2xl font-bold text-white select-none"
            style={{
              background: previewSrc ? 'transparent' : 'hsl(var(--muted))',
            }}
          >
            {previewSrc ? (
              <Image src={previewSrc} alt="头像预览" fill className="object-cover" />
            ) : (
              <ImageIcon className="h-8 w-8 text-muted-foreground opacity-60" />
            )}
            {isUploadingAvatar && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center rounded-full">
                <Loader2 className="h-5 w-5 text-white animate-spin" />
              </div>
            )}
          </div>
          {/* 未上传时的小提示标记 */}
          {!previewSrc && !isUploadingAvatar && formData.appearance && (
            <div className="absolute -bottom-1 -right-1 bg-foreground text-background text-[9px] px-1.5 py-0.5 rounded-full">
              AI
            </div>
          )}
        </div>

        {/* 操作文字 */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium mb-1">角色头像</p>
          <p className="text-xs text-muted-foreground mb-2.5">
            {previewSrc
              ? '已上传头像'
              : formData.appearance
                ? '未上传时将根据外貌描述自动生成（消耗 10 积分）'
                : '支持 JPEG/PNG/WebP，最大 5MB'}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => avatarInputRef.current?.click()}
              disabled={isUploadingAvatar}
              className="h-8 text-xs rounded-lg border-border"
            >
              <Upload className="h-3.5 w-3.5 mr-1.5" />
              {previewSrc ? '重新上传' : '上传图片'}
            </Button>
            {previewSrc && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setAvatarUrl('')}
                className="h-8 text-xs rounded-lg text-muted-foreground hover:text-destructive"
              >
                <X className="h-3.5 w-3.5 mr-1" />
                移除
              </Button>
            )}
          </div>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleAvatarFileChange}
          />
        </div>
      </div>
    )
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4 md:space-y-6">
            {/* 头像上传 */}
            {renderAvatarUpload()}

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">角色名称 *</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="给你的角色起个名字"
                className="h-11 md:h-14 rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">标题</label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="例：月光下的秘密（作为首页卡片展示标题，不填则显示角色名称）"
                className="h-11 md:h-14 rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">公开简介 *</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="简单描述你的角色（会显示在卡片上）"
                className="min-h-[100px] md:min-h-[120px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">标签</label>
              <div className="flex gap-2 mb-2 md:mb-3">
                <Input
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  placeholder="添加标签"
                  className="h-10 md:h-12 rounded-lg md:rounded-xl bg-secondary/50 border-0 text-sm"
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleAddTag}
                  className="h-10 md:h-12 px-3 md:px-4 rounded-lg md:rounded-xl"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 md:gap-2">
                {formData.tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="rounded-md md:rounded-lg px-2 md:px-3 py-1 md:py-1.5 text-xs md:text-sm cursor-pointer hover:bg-destructive hover:text-destructive-foreground transition-colors"
                    onClick={() => handleRemoveTag(tag)}
                  >
                    {tag}
                    <X className="ml-1 md:ml-1.5 h-3 w-3" />
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between rounded-xl md:rounded-2xl bg-secondary/50 p-3 md:p-4">
              <div>
                <p className="text-sm md:text-base font-medium">公开角色</p>
                <p className="text-xs md:text-sm text-muted-foreground">其他用户可以看到并与之对话</p>
              </div>
              <Switch
                checked={formData.visibility === 'public'}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, visibility: checked ? 'public' : 'private' })
                }
              />
            </div>
          </div>
        )

      case 1:
        return (
          <div className="space-y-4 md:space-y-6">
            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">角色人设 *</label>
              <Textarea
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                placeholder="详细描述角色的性格特征、行为模式、说话方式等"
                className="min-h-[120px] md:min-h-[150px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">用户人设</label>
              <Textarea
                value={formData.userRole}
                onChange={(e) => setFormData({ ...formData, userRole: e.target.value })}
                placeholder="定义用户在对话中的身份角色"
                className="min-h-[80px] md:min-h-[100px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">场景设定</label>
              <Textarea
                value={formData.scene}
                onChange={(e) => setFormData({ ...formData, scene: e.target.value })}
                placeholder="描述对话发生的环境和背景"
                className="min-h-[80px] md:min-h-[100px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">开场白 *</label>
              <Textarea
                value={formData.greeting}
                onChange={(e) => setFormData({ ...formData, greeting: e.target.value })}
                placeholder="角色首次见面时会说的话"
                className="min-h-[100px] md:min-h-[120px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4 md:space-y-6">
            <p className="text-xs md:text-sm text-muted-foreground">
              状态变量可以追踪角色的动态变化，如情绪、好感度等。
            </p>

            <div className="glass-subtle rounded-xl md:rounded-2xl p-4 md:p-6 space-y-3 md:space-y-4">
              <div className="grid grid-cols-2 gap-3 md:gap-4">
                <div>
                  <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">状态名称</label>
                  <Input
                    value={newState.name}
                    onChange={(e) => setNewState({ ...newState, name: e.target.value })}
                    placeholder="如：情绪"
                    className="h-10 md:h-12 rounded-lg md:rounded-xl bg-background border-border text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">类型</label>
                  <select
                    value={newState.type}
                    onChange={(e) =>
                      setNewState({ ...newState, type: e.target.value as 'string' | 'number' })
                    }
                    className="h-10 md:h-12 w-full rounded-lg md:rounded-xl bg-background border border-border px-3 md:px-4 text-sm"
                  >
                    <option value="string">文本</option>
                    <option value="number">数值</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">默认值</label>
                <Input
                  value={newState.defaultValue}
                  onChange={(e) => setNewState({ ...newState, defaultValue: e.target.value })}
                  placeholder={newState.type === 'number' ? '如：50' : '如：平静'}
                  type={newState.type === 'number' ? 'number' : 'text'}
                  className="h-10 md:h-12 rounded-lg md:rounded-xl bg-background border-border text-sm"
                />
              </div>
              <div>
                <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">描述</label>
                <Input
                  value={newState.description}
                  onChange={(e) => setNewState({ ...newState, description: e.target.value })}
                  placeholder="这个状态代表什么"
                  className="h-10 md:h-12 rounded-lg md:rounded-xl bg-background border-border text-sm"
                />
              </div>
              <Button
                type="button"
                onClick={handleAddState}
                className="w-full h-10 md:h-12 rounded-lg md:rounded-xl text-sm"
                disabled={!newState.name || !newState.defaultValue}
              >
                <Plus className="mr-1.5 md:mr-2 h-4 w-4" />
                添加状态
              </Button>
            </div>

            {formData.states.length > 0 && (
              <div className="space-y-2 md:space-y-3">
                <h3 className="text-sm md:text-base font-medium">已添加的状态</h3>
                {formData.states.map((state, idx) => (
                  <div
                    key={state.name || idx}
                    className="flex items-center justify-between rounded-lg md:rounded-xl bg-secondary/50 p-3 md:p-4"
                  >
                    <div>
                      <p className="text-sm md:text-base font-medium">{state.name}</p>
                      <p className="text-xs md:text-sm text-muted-foreground">
                        {state.type === 'number' ? '数值' : '文本'} · 默认值: {String(state.defaultValue)}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveState(state.name)}
                      className="text-destructive hover:text-destructive h-8 w-8 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )

      case 3:
        return (
          <div className="space-y-4 md:space-y-6">
            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">世界设定</label>
              <Textarea
                value={formData.worldSetting}
                onChange={(e) => setFormData({ ...formData, worldSetting: e.target.value })}
                placeholder="故事发生的世界观描述"
                className="min-h-[120px] md:min-h-[150px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            {/* 剧情大纲 */}
            <div>
              <div className="flex items-center justify-between mb-1.5 md:mb-2">
                <div>
                  <label className="block text-xs md:text-sm font-medium">剧情大纲</label>
                  <p className="text-[10px] text-muted-foreground mt-0.5">开启剧情模式时，AI 会按此大纲推进故事走向</p>
                </div>
              </div>
              <Textarea
                value={formData.storyline}
                onChange={(e) => setFormData({ ...formData, storyline: e.target.value })}
                placeholder="例：第一阶段 - 初次相遇，两人因误会产生矛盾；第二阶段 - 共同经历危机，建立信任；第三阶段 - 情感升华，表白和解"
                className="min-h-[100px] md:min-h-[120px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
            </div>

            {/* 关键节点 */}
            <div>
              <div className="flex items-center justify-between mb-1.5 md:mb-2">
                <div>
                  <label className="block text-xs md:text-sm font-medium">关键节点</label>
                  <p className="text-[10px] text-muted-foreground mt-0.5">AI 会引导剧情按顺序触达每个节点</p>
                </div>
                <button
                  type="button"
                  onClick={() => setFormData({
                    ...formData,
                    plot_milestones: [...formData.plot_milestones, { title: '', description: '' }]
                  })}
                  className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" />
                  添加节点
                </button>
              </div>

              {formData.plot_milestones.length === 0 ? (
                <div className="text-center py-6 rounded-xl border-2 border-dashed border-border text-xs text-muted-foreground">
                  暂无关键节点，点击「添加节点」开始规划
                </div>
              ) : (
                <div className="space-y-3">
                  {formData.plot_milestones.map((m, i) => (
                    <div key={i} className="rounded-xl border border-border bg-secondary/20 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-muted-foreground font-medium">节点 {i + 1}</span>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            disabled={i === 0}
                            onClick={() => {
                              const arr = [...formData.plot_milestones]
                                ;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
                              setFormData({ ...formData, plot_milestones: arr })
                            }}
                            className="p-1 rounded-md hover:bg-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            disabled={i === formData.plot_milestones.length - 1}
                            onClick={() => {
                              const arr = [...formData.plot_milestones]
                                ;[arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]
                              setFormData({ ...formData, plot_milestones: arr })
                            }}
                            className="p-1 rounded-md hover:bg-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronDown className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const arr = formData.plot_milestones.filter((_, idx) => idx !== i)
                              setFormData({ ...formData, plot_milestones: arr })
                            }}
                            className="p-1 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                      <Input
                        value={m.title}
                        onChange={(e) => {
                          const arr = formData.plot_milestones.map((item, idx) =>
                            idx === i ? { ...item, title: e.target.value } : item
                          )
                          setFormData({ ...formData, plot_milestones: arr })
                        }}
                        placeholder="节点标题（如：初次见面、产生信任、表白）"
                        className="h-8 rounded-lg bg-background border-border text-sm"
                      />
                      <Textarea
                        value={m.description}
                        onChange={(e) => {
                          const arr = formData.plot_milestones.map((item, idx) =>
                            idx === i ? { ...item, description: e.target.value } : item
                          )
                          setFormData({ ...formData, plot_milestones: arr })
                        }}
                        placeholder="触发条件或剧情描述（如：当用户主动示好并提到喜欢角色时触发）"
                        className="min-h-[72px] rounded-lg bg-background border-border text-sm resize-none"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )

      case 4:
        return (
          <div className="space-y-4 md:space-y-6">
            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">外貌描述</label>
              <Textarea
                value={formData.appearance}
                onChange={(e) => setFormData({ ...formData, appearance: e.target.value })}
                placeholder="例：A young woman in her mid-20s with long silver hair, striking red eyes, flawless porcelain skin, slender figure..."
                className="min-h-[100px] md:min-h-[120px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none"
              />
              <p className="text-[10px] md:text-sm text-muted-foreground mt-1.5 md:mt-2">
                仅描述固定外貌特征（发色、瞳色、肤色、体型等），将直接用于图像生成 prompt
              </p>
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">画风选择</label>
              <div className="grid grid-cols-2 gap-2 md:gap-3">
                {artStyles.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, artStyle: s.value })}
                    className={cn(
                      'rounded-lg md:rounded-xl p-2.5 md:p-4 text-xs md:text-sm text-left transition-all border-2',
                      formData.artStyle === s.value
                        ? 'border-foreground bg-foreground text-background'
                        : 'border-border bg-secondary/50 hover:border-foreground/50'
                    )}
                  >
                    <span className="font-medium block">{s.label}</span>
                    <span className={cn('text-[10px] mt-0.5 block', formData.artStyle === s.value ? 'text-background/70' : 'text-muted-foreground')}>{s.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">初始衣物状态</label>
              <Input
                value={formData.initialClothing}
                onChange={(e) => setFormData({ ...formData, initialClothing: e.target.value })}
                placeholder="角色初始穿着描述"
                className="h-11 md:h-14 rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base"
              />
            </div>
          </div>
        )

      case 5:
        return (
          <div className="space-y-4 md:space-y-6">
            <div>
              <label className="block text-xs md:text-sm font-medium mb-1.5 md:mb-2">声音参考</label>
              <p className="text-xs text-muted-foreground mb-3">
                点击音色卡片即可选择，点击▶ 可预览音色效果
              </p>
              {voicePresets.length > 0 ? (
                <div className="space-y-2">
                  {voicePresets.map((preset) => (
                    <div
                      key={preset.id}
                      onClick={() => setFormData({ ...formData, voiceRef: preset.reference_id })}
                      className={cn(
                        'flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all',
                        formData.voiceRef === preset.reference_id
                          ? 'border-foreground bg-foreground/5'
                          : 'border-border bg-secondary/30 hover:border-foreground/40'
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{preset.name}</span>
                          {formData.voiceRef === preset.reference_id && (
                            <span className="text-[10px] bg-foreground text-background px-1.5 py-0.5 rounded-full">已选</span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5">{preset.description}</p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleVoicePreview(preset.id, preset.preview_url) }}
                        className={cn(
                          'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all',
                          playingVoiceId === preset.id
                            ? 'bg-foreground text-background'
                            : 'bg-secondary hover:bg-secondary/80 text-muted-foreground hover:text-foreground'
                        )}
                      >
                        {playingVoiceId === preset.id
                          ? <Square className="h-3.5 w-3.5" />
                          : <Play className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground text-center py-6">加载音色列表中...</div>
              )}
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <AuthModal />
      <CreditsDialog
        open={showCreditsDialog}
        onOpenChange={(open) => { if (!isCreating) setShowCreditsDialog(open) }}
        amount={50}
        action="创建角色"
        onConfirm={handleConfirmCreate}
      />

      <main className="pt-24 md:pt-32 pb-12 md:pb-20 px-4 md:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-4 md:mb-8">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>

            <button
              onClick={() => setShowAiMode(!showAiMode)}
              className="flex items-center gap-1.5 text-xs md:text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <Wand2 className="h-3.5 w-3.5 md:h-4 md:w-4" />
              {showAiMode ? '手动创建' : 'AI 智能创建'}
            </button>
          </div>

          {showAiMode ? (
            /* AI Mode */
            <div className="glass rounded-2xl md:rounded-3xl p-5 md:p-8 animate-fade-in">
              <div className="text-center mb-5 md:mb-8">
                <div className="inline-flex h-12 w-12 md:h-16 md:w-16 items-center justify-center rounded-xl md:rounded-2xl bg-foreground mb-3 md:mb-4">
                  <Wand2 className="h-6 w-6 md:h-8 md:w-8 text-background" />
                </div>
                <h1 className="text-lg md:text-2xl font-bold mb-1.5 md:mb-2">AI 智能创建</h1>
                <p className="text-xs md:text-sm text-muted-foreground">
                  用自然语言描述你想要的角色，AI 会自动生成完整配置
                </p>
              </div>

              <Textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="例如：创建一个银发少女，性格高冷但内心温柔，是魔法学院的学生，场景设定在图书馆初次相遇"
                className="min-h-[140px] md:min-h-[200px] rounded-xl md:rounded-2xl bg-secondary/50 border-0 text-sm md:text-base resize-none mb-4 md:mb-6"
              />

              <Button
                onClick={handleAiGenerate}
                disabled={!aiPrompt || isAiGenerating}
                className="w-full h-11 md:h-14 rounded-xl md:rounded-2xl text-sm md:text-base"
              >
                {isAiGenerating ? (
                  <>
                    <Loader2 className="mr-1.5 md:mr-2 h-4 w-4 md:h-5 md:w-5 animate-spin" />
                    AI 正在创作中...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-1.5 md:mr-2 h-4 w-4 md:h-5 md:w-5" />
                    开始生成
                  </>
                )}
              </Button>
            </div>
          ) : (
            /* Manual Mode */
            <>
              {/* Progress Steps */}
              <div className="mb-4 md:mb-8">
                <div className="flex items-center justify-between mb-3 md:mb-4">
                  {steps.map((step, index) => (
                    <button
                      key={step.title}
                      onClick={() => setCurrentStep(index)}
                      className={cn(
                        'flex flex-col items-center gap-1 md:gap-2 transition-all',
                        index === currentStep
                          ? 'text-foreground'
                          : index < currentStep
                            ? 'text-foreground/70'
                            : 'text-muted-foreground'
                      )}
                    >
                      <div
                        className={cn(
                          'flex h-9 w-9 md:h-12 md:w-12 items-center justify-center rounded-lg md:rounded-xl transition-all',
                          index === currentStep
                            ? 'bg-foreground text-background'
                            : index < currentStep
                              ? 'bg-foreground/20 text-foreground'
                              : 'bg-secondary'
                        )}
                      >
                        {index < currentStep ? (
                          <Check className="h-4 w-4 md:h-5 md:w-5" />
                        ) : (
                          <step.icon className="h-4 w-4 md:h-5 md:w-5" />
                        )}
                      </div>
                      <span className="text-[10px] md:text-xs font-medium hidden sm:block">
                        {step.title}
                      </span>
                    </button>
                  ))}
                </div>
                <div className="h-1 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-foreground transition-all duration-300"
                    style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                  />
                </div>
              </div>

              {/* Form */}
              <div className="glass rounded-2xl md:rounded-3xl p-5 md:p-8 mb-4 md:mb-8 animate-fade-in">
                <div className="mb-4 md:mb-6">
                  <h2 className="text-base md:text-2xl font-bold mb-0.5 md:mb-1">{steps[currentStep].title}</h2>
                  <p className="text-xs md:text-sm text-muted-foreground">{steps[currentStep].description}</p>
                </div>

                {renderStepContent()}
              </div>

              {/* 创建中提示 */}
              {isCreating && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 px-1 bg-secondary/50 rounded-lg p-3">
                  <Loader2 className="h-3.5 w-3.5 animate-spin flex-shrink-0" />
                  <span>正在创建角色...</span>
                </div>
              )}

              {/* Navigation */}
              <div className="flex gap-2 md:gap-4">
                <Button
                  variant="outline"
                  onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
                  disabled={currentStep === 0}
                  className="flex-1 h-11 md:h-14 rounded-xl md:rounded-2xl text-sm md:text-base border-border"
                >
                  <ArrowLeft className="mr-1.5 md:mr-2 h-4 w-4 md:h-5 md:w-5" />
                  上一步
                </Button>

                {currentStep === steps.length - 1 ? (
                  <Button
                    onClick={handleSubmit}
                    disabled={!canProceed()}
                    className="flex-1 h-11 md:h-14 rounded-xl md:rounded-2xl text-sm md:text-base"
                  >
                    <Check className="mr-1.5 md:mr-2 h-4 w-4 md:h-5 md:w-5" />
                    <span className="hidden sm:inline">创建角色（50 积分）</span>
                    <span className="sm:hidden">创建（50积分）</span>
                  </Button>
                ) : (
                  <Button
                    onClick={() => setCurrentStep((s) => Math.min(steps.length - 1, s + 1))}
                    disabled={!canProceed()}
                    className="flex-1 h-11 md:h-14 rounded-xl md:rounded-2xl text-sm md:text-base"
                  >
                    下一步
                    <ArrowRight className="ml-1.5 md:ml-2 h-4 w-4 md:h-5 md:w-5" />
                  </Button>
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
