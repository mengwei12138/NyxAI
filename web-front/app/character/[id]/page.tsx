'use client'

import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/lib/store'
import { charactersApi } from '@/lib/api'
import type { Character } from '@/lib/api'
import {
  ArrowLeft,
  MessageSquare,
  Sparkles,
  Edit,
  Users,
  BookOpen,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export default function CharacterDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const router = useRouter()
  const { user, setAuthModal } = useAppStore()
  const [character, setCharacter] = useState<Character | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadCharacter = async () => {
      try {
        const c = await charactersApi.getById(id)
        if (c) setCharacter(c)
      } catch (error) {
        console.error('Failed to load character:', error)
      } finally {
        setLoading(false)
      }
    }
    loadCharacter()
  }, [id])

  /* ───── Loading ───── */
  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        {/* Mobile skeleton */}
        <div className="md:hidden">
          <Skeleton className="h-56 w-full" />
          <div className="px-5 pt-16 pb-4 space-y-3">
            <Skeleton className="h-7 w-40 mx-auto rounded-lg" />
            <Skeleton className="h-4 w-24 mx-auto rounded-md" />
            <div className="flex justify-center gap-2 pt-1">
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="h-5 w-14 rounded-full" />
            </div>
          </div>
          <div className="px-5 pt-2 space-y-2">
            <Skeleton className="h-4 w-full rounded" />
            <Skeleton className="h-4 w-5/6 rounded" />
            <Skeleton className="h-4 w-4/6 rounded" />
          </div>
        </div>
        {/* Desktop skeleton */}
        <div className="hidden md:block max-w-3xl mx-auto px-6 pt-32">
          <div className="glass rounded-3xl p-8 flex gap-8">
            <Skeleton className="h-40 w-40 rounded-2xl flex-shrink-0" />
            <div className="flex-1 space-y-3 pt-2">
              <Skeleton className="h-8 w-48 rounded-lg" />
              <Skeleton className="h-4 w-32 rounded" />
              <div className="flex gap-2 pt-1">
                <Skeleton className="h-5 w-16 rounded-md" />
                <Skeleton className="h-5 w-16 rounded-md" />
              </div>
              <Skeleton className="h-4 w-full rounded mt-4" />
              <Skeleton className="h-4 w-3/4 rounded" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  /* ───── Not Found ───── */
  if (!character) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        <div className="pt-32 px-4 text-center">
          <h1 className="text-2xl font-semibold mb-4">角色不存在</h1>
          <Button onClick={() => router.push('/')} variant="outline" className="rounded-xl">
            返回首页
          </Button>
        </div>
      </div>
    )
  }

  const isOwner = user && character.creatorId === user.id

  const handleStartChat = () => {
    if (!user) {
      setAuthModal(true, 'login')
      return
    }
    router.push(`/chat/${character.id}`)
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
  const backendBase = apiBase.replace(/\/api$/, '')
  const avatarSrc = character.avatar
    ? (character.avatar.startsWith('http') ? character.avatar : `${backendBase}${character.avatar}`)
    : null

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <AuthModal />

      {/* ═══════════════ MOBILE ═══════════════ */}
      <div className="md:hidden">
        {/* Hero 封面区 */}
        <div className="relative h-60 w-full overflow-hidden">
          {avatarSrc ? (
            <Image
              src={avatarSrc}
              alt={character.name}
              fill
              className="object-cover object-top scale-110"
              priority
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-secondary to-background" />
          )}
          {/* 渐变遮罩 */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-background" />
          {/* 返回按钮 */}
          <button
            onClick={() => router.back()}
            className="absolute top-20 left-4 z-10 flex items-center justify-center h-9 w-9 rounded-full bg-black/40 backdrop-blur-md text-white"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
        </div>

        {/* 头像浮在封面下方 */}
        <div className="relative -mt-14 px-5 flex flex-col items-center">
          <div className={cn(
            "h-24 w-24 rounded-2xl border-4 border-background shadow-xl overflow-hidden flex-shrink-0",
            "bg-gradient-to-br from-primary/20 to-secondary"
          )}>
            {avatarSrc ? (
              <Image src={avatarSrc} alt={character.name} width={96} height={96} className="object-cover w-full h-full" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-foreground/60">
                {character.name.slice(0, 2)}
              </div>
            )}
          </div>

          {/* 名称 + 标题 */}
          <div className="mt-3 text-center">
            {character.title && (
              <p className="text-[11px] font-medium tracking-widest text-primary/60 uppercase mb-0.5">
                {character.title}
              </p>
            )}
            <div className="flex items-center justify-center gap-1.5">
              <h1 className="text-xl font-bold tracking-tight">{character.name}</h1>
              {character.isSystem && <Sparkles className="h-4 w-4 text-primary" />}
            </div>
            {character.dialogueCount > 0 && (
              <div className="flex items-center justify-center gap-1 mt-1 text-[11px] text-muted-foreground">
                <Users className="h-3 w-3" />
                <span>{character.dialogueCount.toLocaleString()} 次对话</span>
              </div>
            )}
          </div>

          {/* 标签 */}
          {(character.tags || []).length > 0 && (
            <div className="flex flex-wrap justify-center gap-1.5 mt-3">
              {character.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="rounded-full px-2.5 py-0.5 text-[11px]">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* 简介 */}
        {character.description && (
          <div className="mx-5 mt-5 mb-28">
            <div className="flex items-center gap-2 mb-2.5">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">简介</span>
            </div>
            <p className="text-sm text-foreground/75 leading-relaxed whitespace-pre-wrap">
              {character.description}
            </p>
          </div>
        )}

        {/* 底部固定操作栏 */}
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/90 backdrop-blur-xl border-t border-border/50">
          <div className="flex gap-2.5">
            <Button className="flex-1 h-12 rounded-xl gap-2 text-sm font-semibold" onClick={handleStartChat}>
              <MessageSquare className="h-4 w-4" />
              开始聊天
            </Button>
            {isOwner && !character.isSystem && (
              <Link href={`/character/${character.id}/edit`}>
                <Button variant="outline" className="h-12 w-12 rounded-xl border-border p-0">
                  <Edit className="h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════════ DESKTOP ═══════════════ */}
      <main className="hidden md:block pt-24 pb-16">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>

          {/* 主卡片 */}
          <div className="relative rounded-3xl overflow-hidden border border-border/50 shadow-xl animate-fade-in">
            {/* 顶部封面背景条 */}
            <div className="relative h-36 w-full overflow-hidden">
              {avatarSrc ? (
                <Image src={avatarSrc} alt={character.name} fill className="object-cover object-top blur-sm scale-110 brightness-75" />
              ) : (
                <div className="absolute inset-0 bg-gradient-to-br from-primary/30 to-secondary" />
              )}
              <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background/95" />
            </div>

            {/* 内容区 */}
            <div className="bg-background/95 backdrop-blur-sm px-8 pb-8 -mt-6">
              <div className="flex gap-6 items-end">
                {/* 大头像 */}
                <div className="relative -mt-16 flex-shrink-0 h-32 w-32 rounded-2xl border-4 border-background shadow-2xl overflow-hidden bg-gradient-to-br from-primary/20 to-secondary">
                  {avatarSrc ? (
                    <Image src={avatarSrc} alt={character.name} fill className="object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl font-bold text-foreground/60">
                      {character.name.slice(0, 2)}
                    </div>
                  )}
                </div>

                {/* 名称信息 */}
                <div className="flex-1 min-w-0 pb-1 pt-4">
                  {character.title && (
                    <p className="text-[11px] font-semibold tracking-widest text-primary/60 uppercase mb-1">
                      {character.title}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mb-1">
                    <h1 className="text-2xl font-bold tracking-tight">{character.name}</h1>
                    {character.isSystem && (
                      <span className="flex items-center gap-1 text-[11px] text-muted-foreground bg-secondary rounded-full px-2 py-0.5">
                        <Sparkles className="h-3 w-3" />
                        官方
                      </span>
                    )}
                  </div>
                  {character.dialogueCount > 0 && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                      <Users className="h-3 w-3" />
                      <span>{character.dialogueCount.toLocaleString()} 次对话</span>
                    </div>
                  )}
                  {(character.tags || []).length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {character.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="rounded-md px-2 py-0.5 text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                {/* 操作按钮 */}
                <div className="flex flex-col gap-2 flex-shrink-0 pb-1">
                  <Button className="h-11 px-7 rounded-xl text-sm gap-2 font-semibold" onClick={handleStartChat}>
                    <MessageSquare className="h-4 w-4" />
                    开始聊天
                  </Button>
                  {isOwner && !character.isSystem && (
                    <Link href={`/character/${character.id}/edit`}>
                      <Button variant="outline" className="h-9 w-full px-5 rounded-xl text-sm gap-1.5 border-border">
                        <Edit className="h-3.5 w-3.5" />
                        编辑角色
                      </Button>
                    </Link>
                  )}
                </div>
              </div>

              {/* 简介 */}
              {character.description && (
                <div className="mt-6 pt-6 border-t border-border/50">
                  <div className="flex items-center gap-2 mb-3">
                    <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">角色简介</span>
                  </div>
                  <p className="text-sm text-foreground/75 leading-loose whitespace-pre-wrap">
                    {character.description}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
