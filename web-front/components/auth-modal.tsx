'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAppStore } from '@/lib/store'
import { authApi } from '@/lib/api'
import { Sparkles, Eye, EyeOff, User, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import Link from 'next/link'

export function AuthModal() {
  const { isAuthModalOpen, authModalMode, setAuthModal, setUser } = useAppStore()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [ageConfirmed, setAgeConfirmed] = useState(false)
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      if (authModalMode === 'register') {
        if (!ageConfirmed) {
          alert('请确认您已年满 18 周岁')
          setIsLoading(false)
          return
        }
        if (!termsAccepted) {
          alert('请阅读并同意用户协议和隐私政策')
          setIsLoading(false)
          return
        }
        const result = await authApi.register({
          username: formData.username,
          password: formData.password,
          confirm_password: formData.confirmPassword,
        })
        alert(result.message || '注册成功！请使用用户名和密码登录')
        setFormData({ username: formData.username, password: '', confirmPassword: '' })
        setAgeConfirmed(false)
        setTermsAccepted(false)
        setAuthModal(true, 'login')
      } else {
        const response = await authApi.login({
          username: formData.username,
          password: formData.password,
        })

        if (response.access_token) {
          localStorage.setItem('token', response.access_token)
          setUser({
            id: response.user_id.toString(),
            username: response.username,
            email: response.email || '',
            credits: response.credits || 0,
            totalEarned: response.total_earned || 0,
            totalSpent: response.total_spent || 0,
          })
          setAuthModal(false)
          setFormData({ username: '', password: '', confirmPassword: '' })
        }
      }
    } catch (error: any) {
      alert(error.message || '操作失败')
    } finally {
      setIsLoading(false)
    }
  }

  const isLogin = authModalMode === 'login'

  const switchMode = () => {
    setAgeConfirmed(false)
    setTermsAccepted(false)
    setAuthModal(true, isLogin ? 'register' : 'login')
  }

  return (
    <Dialog open={isAuthModalOpen} onOpenChange={(open) => setAuthModal(open)}>
      <DialogContent className="sm:max-w-md rounded-3xl p-0 overflow-hidden border-0 shadow-2xl">
        <div className="p-8">
          <DialogHeader className="mb-8">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-foreground">
              <Sparkles className="h-8 w-8 text-background" />
            </div>
            <DialogTitle className="text-center text-2xl font-semibold">
              {isLogin ? '欢迎回来' : '创建账户'}
            </DialogTitle>
            <DialogDescription className="text-center text-muted-foreground mt-2">
              {isLogin ? '登录以继续您的角色扮演之旅' : '注册即送 100 积分'}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="relative">
              <User className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                placeholder="用户名"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="h-14 rounded-2xl border-border bg-secondary/50 pl-12 text-base placeholder:text-muted-foreground focus:bg-background"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="密码"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="h-14 rounded-2xl border-border bg-secondary/50 pl-12 pr-12 text-base placeholder:text-muted-foreground focus:bg-background"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>

            {!isLogin && (
              <>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="确认密码"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="h-14 rounded-2xl border-border bg-secondary/50 pl-12 pr-12 text-base placeholder:text-muted-foreground focus:bg-background"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>

                {/* 18+ 年龄确认 */}
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className="relative mt-0.5 flex-shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={ageConfirmed}
                      onChange={(e) => setAgeConfirmed(e.target.checked)}
                    />
                    <div
                      className={cn(
                        'h-5 w-5 rounded-md border-2 transition-all flex items-center justify-center',
                        ageConfirmed
                          ? 'bg-foreground border-foreground'
                          : 'border-border bg-secondary/50 group-hover:border-foreground/50'
                      )}
                    >
                      {ageConfirmed && (
                        <svg className="h-3 w-3 text-background" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  </div>
                  <span className="text-sm text-muted-foreground leading-snug">
                    我已年满{' '}
                    <span className="font-semibold text-foreground">18 周岁</span>
                  </span>
                </label>

                {/* 用户协议 + 隐私政策 */}
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className="relative mt-0.5 flex-shrink-0">
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={termsAccepted}
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <div
                      className={cn(
                        'h-5 w-5 rounded-md border-2 transition-all flex items-center justify-center',
                        termsAccepted
                          ? 'bg-foreground border-foreground'
                          : 'border-border bg-secondary/50 group-hover:border-foreground/50'
                      )}
                    >
                      {termsAccepted && (
                        <svg className="h-3 w-3 text-background" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  </div>
                  <span className="text-sm text-muted-foreground leading-snug">
                    我已阅读并同意{' '}
                    <Link
                      href="/terms"
                      target="_blank"
                      className="font-medium text-foreground hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      用户协议
                    </Link>
                    {' '}和{' '}
                    <Link
                      href="/privacy"
                      target="_blank"
                      className="font-medium text-foreground hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      隐私政策
                    </Link>
                  </span>
                </label>
              </>
            )}

            <Button
              type="submit"
              disabled={isLoading || (!isLogin && (!ageConfirmed || !termsAccepted))}
              className={cn(
                'h-14 w-full rounded-2xl text-base font-medium transition-all',
                (isLoading || (!isLogin && (!ageConfirmed || !termsAccepted))) && 'opacity-50'
              )}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  处理中...
                </span>
              ) : isLogin ? (
                '登录'
              ) : (
                '创建账户'
              )}
            </Button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-muted-foreground">
              {isLogin ? '还没有账户？' : '已有账户？'}
              <button
                type="button"
                onClick={switchMode}
                className="ml-1 font-medium text-foreground hover:underline"
              >
                {isLogin ? '立即注册' : '立即登录'}
              </button>
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
