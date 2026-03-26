'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAppStore } from '@/lib/store'
import { authApi, paymentApi, creditsApi } from '@/lib/api'
import { CheckinButton } from '@/components/checkin-button'
import type { PaymentPackage } from '@/lib/api'
import {
  User,
  Coins,
  TrendingUp,
  TrendingDown,
  Edit2,
  Save,
  X,
  LogOut,
  Sparkles,
  Wallet,
  CreditCard,
  MessageCircle,
  Image,
  UserPlus,
  Plus,
  Zap,
  Lock,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Smartphone,
  QrCode,
  ExternalLink,
  Gift,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ProfilePage() {
  const router = useRouter()
  const { user, setUser, setAuthModal } = useAppStore()
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [editData, setEditData] = useState({
    username: user?.username || '',
  })

  // 修改密码
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [pwdData, setPwdData] = useState({ old_password: '', new_password: '', confirm: '' })
  const [isPwdSaving, setIsPwdSaving] = useState(false)
  const [pwdMsg, setPwdMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // 充值弹窗
  const [showRecharge, setShowRecharge] = useState(false)
  const [packages, setPackages] = useState<PaymentPackage[]>([])
  const [selectedPkg, setSelectedPkg] = useState<string>('')
  const [isCreatingOrder, setIsCreatingOrder] = useState(false)
  // 爱发电：存储 custom_order_id 用于轮询，pay_url 用于重跳
  const [customOrderId, setCustomOrderId] = useState<string>('')
  const [pendingPayUrl, setPendingPayUrl] = useState<string>('')
  const [pendingCredits, setPendingCredits] = useState<number>(0)
  const [pollStatus, setPollStatus] = useState<'waiting' | 'paid' | 'failed' | null>(null)

  // 加载套餐
  useEffect(() => {
    if (showRecharge && packages.length === 0) {
      paymentApi.getPackages().then(res => {
        if (res.success) {
          setPackages(res.data)
          if (res.data.length > 0) setSelectedPkg(res.data[1]?.id || res.data[0].id)
        }
      }).catch(() => { })
    }
  }, [showRecharge])

  // 轮询支付结果（保存 timer ref 以便关闭弹窗时及时清除）
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const userRef = useRef(user)
  useEffect(() => { userRef.current = user }, [user])

  // 页面卸载时清理轮询，防止内存泄漏
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  const startPolling = useCallback((orderId: string) => {
    setPollStatus('waiting')
    let attempts = 0
    const maxAttempts = 60 // 最多轮询 2 分钟
    const timer = setInterval(async () => {
      attempts++
      try {
        const s = await paymentApi.getOrderStatus(orderId)
        if (s.status === 'paid') {
          clearInterval(timer)
          setPollStatus('paid')
          // 从后端重新拉取真实积分余额，避免本地累加出现误差
          try {
            const balanceRes = await creditsApi.getBalance()
            const currentUser = userRef.current
            if (balanceRes.success && currentUser) {
              setUser({
                ...currentUser,
                credits: balanceRes.data.balance,
                totalEarned: balanceRes.data.total_earned,
                totalSpent: balanceRes.data.total_spent,
              })
            }
          } catch { }
        } else if (s.status === 'failed' || attempts >= maxAttempts) {
          clearInterval(timer)
          setPollStatus('failed')
        }
      } catch { }
    }, 3000) // 3秒轮询，给爱发电 Webhook 处理留出时间
    pollTimerRef.current = timer
  }, [setUser])

  const handleCreateOrder = async () => {
    if (!selectedPkg) return
    setIsCreatingOrder(true)
    try {
      const result = await paymentApi.prepareOrder(selectedPkg)
      setCustomOrderId(result.custom_order_id)
      setPendingPayUrl(result.pay_url)
      const pkg = packages.find(p => p.id === selectedPkg)
      setPendingCredits(pkg?.credits ?? 0)
      // 爱发电：直接跳转，移动端同样支持（微信/支付宝网页内打开爱发电）
      window.open(result.pay_url, '_blank')
      startPolling(result.custom_order_id)
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : '创建订单失败，请稍后重试')
    } finally {
      setIsCreatingOrder(false)
    }
  }

  const closeRecharge = () => {
    // 清除后台轮询，防止内存泄漏
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    setShowRecharge(false)
    setCustomOrderId('')
    setPendingPayUrl('')
    setPendingCredits(0)
    setPollStatus(null)
    setIsCreatingOrder(false)
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        <div className="pt-24 md:pt-32 px-4 text-center">
          <div className="max-w-md mx-auto">
            <div className="inline-flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-xl md:rounded-2xl bg-secondary mb-4 md:mb-6">
              <User className="h-7 w-7 md:h-10 md:w-10 text-muted-foreground" />
            </div>
            <h1 className="text-lg md:text-2xl font-semibold mb-2 md:mb-4">请先登录</h1>
            <p className="text-xs md:text-sm text-muted-foreground mb-4 md:mb-6">
              登录后即可查看和编辑您的个人资料
            </p>
            <Button onClick={() => setAuthModal(true, 'login')} className="rounded-lg md:rounded-xl h-9 md:h-10 text-sm">
              立即登录
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const handleSave = async () => {
    setIsSaving(true)
    setSaveMsg(null)
    try {
      const res = await authApi.updateMe({
        username: editData.username,
      })
      if (res.success) {
        setUser({ ...user!, username: res.data.username, email: res.data.email ?? '' })
        setIsEditing(false)
        setSaveMsg({ type: 'success', text: '信息已更新' })
        setTimeout(() => setSaveMsg(null), 3000)
      }
    } catch (e: unknown) {
      setSaveMsg({ type: 'error', text: (e instanceof Error ? e.message : '保存失败') })
    } finally {
      setIsSaving(false)
    }
  }

  const handleChangePassword = async () => {
    if (pwdData.new_password !== pwdData.confirm) {
      setPwdMsg({ type: 'error', text: '两次输入的新密码不一致' })
      return
    }
    if (pwdData.new_password.length < 6) {
      setPwdMsg({ type: 'error', text: '密码至少6个字符' })
      return
    }
    setIsPwdSaving(true)
    setPwdMsg(null)
    try {
      const res = await authApi.changePassword({
        old_password: pwdData.old_password,
        new_password: pwdData.new_password,
      })
      if (res.success) {
        setPwdMsg({ type: 'success', text: '密码已修改，请重新登录' })
        setPwdData({ old_password: '', new_password: '', confirm: '' })
        setTimeout(() => {
          localStorage.removeItem('token')
          setUser(null)
          router.push('/')
        }, 2000)
      }
    } catch (e: unknown) {
      setPwdMsg({ type: 'error', text: (e instanceof Error ? e.message : '修改失败') })
    } finally {
      setIsPwdSaving(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
    router.push('/')
  }

  // TODO: 对接充值接口
  const handleRecharge = () => {
    setShowRecharge(true)
  }

  const stats = [
    {
      icon: Wallet,
      label: '当前积分',
      value: user.credits,
    },
    {
      icon: TrendingUp,
      label: '累计获得',
      value: user.totalEarned,
    },
    {
      icon: TrendingDown,
      label: '累计消费',
      value: user.totalSpent,
    },
  ]

  // 签到成功回调，更新积分显示
  const handleCheckinSuccess = (points: number) => {
    if (user) {
      setUser({
        ...user,
        credits: user.credits + points,
        totalEarned: user.totalEarned + points,
      })
    }
  }

  const costItems = [
    { icon: MessageCircle, label: '发送消息', cost: '1 积分/条' },
    { icon: CreditCard, label: '语音合成', cost: '5 积分/次' },
    { icon: Image, label: '生成图片', cost: '10 积分/张' },
    { icon: UserPlus, label: '创建角色', cost: '50 积分/个' },
  ]

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <AuthModal />

      <main className="pt-16 md:pt-28 pb-16 md:pb-20 px-0 md:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto">

          {/* ── 顶部用户卡片（移动端全出血，无侧边距） ── */}
          <div className="relative bg-card border-b border-border md:rounded-2xl md:border md:mb-6 overflow-hidden">
            {/* 背景装饰条 - 细腻渐变 */}
            <div className="h-20 md:h-24 bg-gradient-to-b from-secondary to-background w-full" />
            {/* 头像 + 信息 */}
            <div className="px-4 md:px-5 pb-4 md:pb-5 -mt-10 md:-mt-12">
              <div className="flex items-end justify-between mb-3">
                <Avatar className="h-20 w-20 md:h-24 md:w-24 rounded-2xl ring-4 ring-background shadow-lg">
                  <AvatarImage src={user.avatar} />
                  <AvatarFallback className="rounded-2xl bg-secondary text-2xl md:text-3xl font-bold">
                    {user.username[0].toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {!isEditing && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => { setEditData({ username: user.username }); setIsEditing(true) }}
                    className="h-8 px-3 rounded-xl text-xs gap-1.5 border-border"
                  >
                    <Edit2 className="h-3 w-3" />
                    编辑
                  </Button>
                )}
              </div>

              {isEditing ? (
                <div className="space-y-2.5">
                  <Input
                    value={editData.username}
                    onChange={(e) => setEditData({ ...editData, username: e.target.value })}
                    className="h-10 rounded-xl bg-secondary/50 border-0 text-sm font-medium"
                    placeholder="用户名"
                  />
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => { setIsEditing(false); setSaveMsg(null) }}
                      className="flex-1 h-9 rounded-xl border-border text-xs" disabled={isSaving}>
                      取消
                    </Button>
                    <Button onClick={handleSave} disabled={isSaving} className="flex-1 h-9 rounded-xl text-xs">
                      {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : '保存'}
                    </Button>
                  </div>
                  {saveMsg && (
                    <div className={cn('flex items-center gap-1.5 text-xs', saveMsg.type === 'success' ? 'text-green-600' : 'text-destructive')}>
                      {saveMsg.type === 'success' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                      {saveMsg.text}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <h1 className="text-xl font-bold leading-tight">{user.username}</h1>
                  <p className="text-xs text-muted-foreground mt-0.5">用户ID：{String(user.id).padStart(6, '0')}</p>
                </div>
              )}
            </div>
          </div>

          {/* ── 积分统计（移动端横向全宽，无外边距） ── */}
          <div className="grid grid-cols-3 border-b border-border md:border-0 md:gap-3 md:mb-6 overflow-hidden">
            {stats.map((stat, index) => (
              <div
                key={stat.label}
                className={cn(
                  "flex flex-col items-center py-5 px-2 md:rounded-2xl md:border md:bg-card transition-all",
                  index !== 2 ? "border-r border-border md:border-r-0" : "",
                  "bg-card"
                )}
              >
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl mb-2 bg-secondary">
                  <stat.icon className="h-4 w-4 text-foreground" />
                </div>
                <div className={cn(
                  "text-2xl font-bold tabular-nums",
                  index === 0 ? "text-foreground" : "text-foreground"
                )}>
                  {stat.value.toLocaleString()}
                </div>
                <div className="text-[11px] text-muted-foreground mt-0.5">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* ── 以下区块统一加 px-4（移动端） ── */}
          <div className="px-4 md:px-0 space-y-3 md:space-y-4 mt-3 md:mt-0">

            {/* 每日签到 */}
            <div className="rounded-2xl border border-border bg-card p-4 md:p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary shrink-0">
                    <Gift className="h-5 w-5 text-foreground" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold">每日签到</h2>
                    <p className="text-[11px] text-muted-foreground mt-0.5">连续签到，积分递增 1-7</p>
                  </div>
                </div>
                <CheckinButton onCheckinSuccess={handleCheckinSuccess} />
              </div>
            </div>

            {/* 积分充值 */}
            <div className="rounded-2xl border border-border bg-card p-4 md:p-5">
              <div className="flex items-center justify-between mb-3.5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-foreground shrink-0">
                    <Zap className="h-5 w-5 text-background" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold">积分充值</h2>
                    <p className="text-[11px] text-muted-foreground mt-0.5">快速补充积分，畅享AI对话</p>
                  </div>
                </div>
                <Button onClick={handleRecharge} size="sm"
                  className="h-9 px-4 rounded-xl gap-1.5 text-xs bg-foreground text-background hover:bg-foreground/90 shrink-0">
                  <Plus className="h-3.5 w-3.5" />充值
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { credits: 100, price: '¥9.9', id: 'starter' },
                  { credits: 350, price: '¥30', id: 'standard', popular: true },
                  { credits: 1150, price: '¥88', id: 'pro' },
                ].map((plan) => (
                  <button key={plan.id} onClick={handleRecharge}
                    className={cn(
                      'relative flex flex-col items-center py-3 px-2 rounded-xl border transition-all',
                      plan.popular ? 'border-foreground bg-foreground/5' : 'border-border bg-background hover:border-foreground/50'
                    )}
                  >
                    {plan.popular && (
                      <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[10px] bg-foreground text-background px-2 py-0.5 rounded-full whitespace-nowrap">热门</span>
                    )}
                    <Coins className="h-4 w-4 mb-1.5 text-muted-foreground" />
                    <span className="text-sm font-bold">{plan.credits}</span>
                    <span className="text-[11px] text-muted-foreground">{plan.price}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 积分说明 */}
            <div className="rounded-2xl border border-border bg-card p-4 md:p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">积分使用说明</h2>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {costItems.map((item) => (
                  <div key={item.label} className="flex items-center gap-2.5 p-3 rounded-xl bg-secondary/50">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background shrink-0">
                      <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-xs font-medium leading-tight">{item.label}</p>
                      <p className="text-[11px] text-muted-foreground">{item.cost}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 修改密码 */}
            <div className="rounded-2xl border border-border bg-card overflow-hidden">
              <button
                onClick={() => { setShowPasswordForm(!showPasswordForm); setPwdMsg(null) }}
                className="w-full flex items-center justify-between p-4 md:p-5"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary shrink-0">
                    <Lock className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="text-left">
                    <h2 className="text-sm font-semibold">修改密码</h2>
                    <p className="text-[11px] text-muted-foreground mt-0.5">定期更新密码保障账户安全</p>
                  </div>
                </div>
                {showPasswordForm ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
              </button>

              {showPasswordForm && (
                <div className="px-4 pb-4 md:px-5 md:pb-5 space-y-2.5 border-t border-border pt-4">
                  <Input type="password" value={pwdData.old_password}
                    onChange={(e) => setPwdData({ ...pwdData, old_password: e.target.value })}
                    placeholder="当前密码" className="h-10 rounded-xl bg-secondary/50 border-0 text-sm" />
                  <Input type="password" value={pwdData.new_password}
                    onChange={(e) => setPwdData({ ...pwdData, new_password: e.target.value })}
                    placeholder="新密码（至少6个字符）" className="h-10 rounded-xl bg-secondary/50 border-0 text-sm" />
                  <Input type="password" value={pwdData.confirm}
                    onChange={(e) => setPwdData({ ...pwdData, confirm: e.target.value })}
                    placeholder="确认新密码" className="h-10 rounded-xl bg-secondary/50 border-0 text-sm" />
                  {pwdMsg && (
                    <div className={cn('flex items-center gap-1.5 text-xs', pwdMsg.type === 'success' ? 'text-green-600' : 'text-destructive')}>
                      {pwdMsg.type === 'success' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                      {pwdMsg.text}
                    </div>
                  )}
                  <Button onClick={handleChangePassword}
                    disabled={isPwdSaving || !pwdData.old_password || !pwdData.new_password || !pwdData.confirm}
                    className="w-full h-10 rounded-xl text-sm">
                    {isPwdSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : '确认修改'}
                  </Button>
                </div>
              )}
            </div>

            {/* 退出登录 */}
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 rounded-2xl p-4 text-destructive bg-destructive/5 hover:bg-destructive/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="text-sm font-medium">退出登录</span>
            </button>

          </div>{/* end px-4 wrapper */}
        </div>
      </main>

      {/* ===== 充值弹窗 ===== */}
      {showRecharge && (
        <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
          {/* 蒙层 */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={pollStatus !== 'waiting' ? closeRecharge : undefined} />

          <div className="relative w-full md:max-w-md bg-background rounded-t-3xl md:rounded-2xl border border-border p-6 z-10 max-h-[90vh] overflow-y-auto">
            {/* 头部 */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold">积分充值</h2>
              {pollStatus !== 'waiting' && (
                <button onClick={closeRecharge} className="h-8 w-8 flex items-center justify-center rounded-full bg-secondary hover:bg-secondary/80">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* 支付成功 */}
            {pollStatus === 'paid' ? (
              <div className="flex flex-col items-center py-8 gap-4">
                <div className="h-16 w-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <CheckCircle2 className="h-8 w-8 text-green-600" />
                </div>
                <div className="text-center">
                  <p className="text-xl font-bold mb-1">支付成功！</p>
                  <p className="text-sm text-muted-foreground">{pendingCredits} 积分已入账</p>
                </div>
                <Button onClick={closeRecharge} className="w-full rounded-xl h-11">完成</Button>
              </div>
            ) : pollStatus === 'waiting' && customOrderId ? (
              /* 等待支付 */
              <div className="flex flex-col items-center py-6 gap-4">
                <div className="h-16 w-16 rounded-full bg-secondary flex items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
                <div className="text-center">
                  <p className="font-semibold mb-1">等待支付完成...</p>
                  <p className="text-xs text-muted-foreground">支付完成后自动充入 {pendingCredits} 积分</p>
                </div>
                <button
                  onClick={() => window.open(pendingPayUrl, '_blank')}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  重新打开爱发电付款页
                </button>
              </div>
            ) : (
              /* 选择套餐 */
              <>
                {/* 套餐列表 */}
                <div className="space-y-3 mb-6">
                  {packages.length === 0 ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : packages.map((pkg) => (
                    <button
                      key={pkg.id}
                      onClick={() => setSelectedPkg(pkg.id)}
                      className={cn(
                        'relative w-full flex items-center justify-between p-4 rounded-xl border transition-all text-left',
                        selectedPkg === pkg.id
                          ? 'border-foreground bg-foreground/5'
                          : 'border-border hover:border-foreground/50'
                      )}
                    >
                      {pkg.popular && (
                        <span className="absolute -top-2 right-3 text-[10px] bg-foreground text-background px-2 py-0.5 rounded-full">热门</span>
                      )}
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'h-10 w-10 rounded-xl flex items-center justify-center',
                          selectedPkg === pkg.id ? 'bg-foreground' : 'bg-secondary'
                        )}>
                          <Coins className={cn('h-5 w-5', selectedPkg === pkg.id ? 'text-background' : 'text-muted-foreground')} />
                        </div>
                        <div>
                          <p className="font-semibold text-sm">{pkg.name}</p>
                          <p className="text-xs text-muted-foreground">{pkg.desc} · {pkg.credits} 积分</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold">¥{pkg.amount}</p>
                        <p className="text-xs text-muted-foreground">{(pkg.amount / pkg.credits * 100).toFixed(0)}分/百积分</p>
                      </div>
                    </button>
                  ))}
                </div>

                <Button
                  onClick={handleCreateOrder}
                  disabled={isCreatingOrder || !selectedPkg}
                  className="w-full h-12 rounded-xl text-base gap-2"
                >
                  {isCreatingOrder
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> 创建订单...</>
                    : <>立即支付 · ¥{packages.find(p => p.id === selectedPkg)?.amount || ''}</>
                  }
                </Button>
                <p className="text-center text-xs text-muted-foreground mt-3">充入的积分仅用于平台购买，不支持提现或转让</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
