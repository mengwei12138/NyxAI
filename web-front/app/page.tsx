'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { CharacterCard } from '@/components/character-card'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Flame, Clock, ArrowRight, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { charactersApi } from '@/lib/api'
import type { Character } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

type SortMode = 'hot' | 'new'

const PAGE_SIZE = 12
const INITIAL_SIZE = 6

export default function HomePage() {
  const { user, setAuthModal, setCharacters } = useAppStore()
  const [sortMode, setSortMode] = useState<SortMode>('hot')
  const [searchQuery, setSearchQuery] = useState('')
  const [characters, setLocalCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [visibleCount, setVisibleCount] = useState(INITIAL_SIZE)
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Load characters from API
  useEffect(() => {
    const loadCharacters = async () => {
      try {
        const response = await charactersApi.getList('public')
        if (response.success && response.data) {
          setLocalCharacters(response.data)
          setCharacters(response.data)
        }
      } catch (error) {
        console.error('Failed to load characters:', error)
      } finally {
        setLoading(false)
      }
    }
    loadCharacters()
  }, [setCharacters])

  const publicCharacters = characters.filter((c) => c.visibility === 'public')

  const sortedCharacters = [...publicCharacters].sort((a, b) => {
    if (sortMode === 'hot') {
      return b.dialogueCount - a.dialogueCount
    }
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })

  const filteredCharacters = sortedCharacters.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.tags.some((t: string) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const visibleCharacters = filteredCharacters.slice(0, visibleCount)
  const hasMore = visibleCount < filteredCharacters.length

  // 搜索/排序变化时重置可见数量
  useEffect(() => {
    setVisibleCount(INITIAL_SIZE)
  }, [searchQuery, sortMode])

  // 加载更多
  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    setTimeout(() => {
      setVisibleCount((prev) => prev + PAGE_SIZE)
      setLoadingMore(false)
    }, 300)
  }, [loadingMore, hasMore])

  // IntersectionObserver 监听哨兵元素
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore()
      },
      { rootMargin: '200px' }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [loadMore])

  return (
    <div className="min-h-screen bg-background pb-10">
      <Header />
      <AuthModal />

      {/* Hero Section */}
      <section className="hidden md:flex flex-col items-center justify-center pt-28 pb-8 px-6 lg:px-8" suppressHydrationWarning>
        <div className="text-center max-w-2xl mx-auto">
          {/* <p className="text-sm text-muted-foreground mb-4 tracking-wide" suppressHydrationWarning>
            AI 角色扮演平台
          </p> */}
          <h1 className="text-3xl lg:text-4xl font-bold tracking-tight mb-4" suppressHydrationWarning>
            不止于对话，遇见懂你的灵魂伴侣
          </h1>
          <p className="text-muted-foreground mb-8 max-w-lg mx-auto" suppressHydrationWarning>
            跨越次元的界限。在这里，没有冰冷的代码，只有随时待命的倾听以及只属于你的专属羁绊。
          </p>
          <div className="flex items-center justify-center gap-3">
            {user ? (
              <Link href="/create">
                <Button size="lg" className="h-11 px-6 rounded-full text-sm gap-2">
                  开始创作
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            ) : (
              <Button
                size="lg"
                className="h-11 px-6 rounded-full text-sm gap-2"
                onClick={() => setAuthModal(true, 'register')}
              >
                开启你的剧本
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="outline"
              size="lg"
              className="h-11 px-6 rounded-full text-sm"
              onClick={() => document.getElementById('characters')?.scrollIntoView({ behavior: 'smooth' })}
            >
              浏览角色
            </Button>
          </div>
        </div>
      </section>

      {/* Characters Section */}
      <section id="characters" className="pt-20 md:pt-6 pb-8 md:pb-12 px-4 md:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <h2 className="text-lg md:text-xl font-semibold">探索宇宙</h2>
              <span className="hidden md:inline-block h-4 w-px bg-border" />
              <p className="hidden md:block text-sm text-muted-foreground">探索社区创建的精彩角色</p>
            </div>

            {/* Search & Filter */}
            <div className="flex items-center gap-2 md:gap-3">
              <div className="relative flex-1 md:flex-none">
                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 md:h-4 md:w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索角色..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-9 md:h-11 w-full md:w-56 rounded-lg md:rounded-xl pl-9 md:pl-10 text-sm bg-secondary/50 border-0"
                />
              </div>

              <div className="flex rounded-lg md:rounded-xl bg-secondary/50 p-0.5 md:p-1">
                <button
                  onClick={() => setSortMode('hot')}
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 md:px-4 py-1.5 md:py-2 rounded-md md:rounded-lg text-xs md:text-sm font-medium transition-all',
                    sortMode === 'hot'
                      ? 'bg-background shadow-sm text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Flame className="h-3 w-3 md:h-4 md:w-4" />
                  热门
                </button>
                <button
                  onClick={() => setSortMode('new')}
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 md:px-4 py-1.5 md:py-2 rounded-md md:rounded-lg text-xs md:text-sm font-medium transition-all',
                    sortMode === 'new'
                      ? 'bg-background shadow-sm text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Clock className="h-3 w-3 md:h-4 md:w-4" />
                  最新
                </button>
              </div>
            </div>
          </div>

          {/* Characters Grid */}
          {loading ? (
            /* 骨架屏 */
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <Skeleton className="aspect-[3/4] w-full rounded-xl" />
                  <Skeleton className="h-4 w-3/4 rounded-md" />
                  <Skeleton className="h-3 w-1/2 rounded-md" />
                </div>
              ))}
            </div>
          ) : filteredCharacters.length > 0 ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
                {visibleCharacters.map((character, index) => (
                  <div
                    key={character.id}
                    className="animate-slide-up"
                    style={{ animationDelay: `${(index % PAGE_SIZE) * 0.05}s` }}
                  >
                    <CharacterCard character={character} />
                  </div>
                ))}
              </div>

              {/* 哨兵 + 加载状态 */}
              <div ref={sentinelRef} className="mt-8 flex justify-center min-h-[2rem]">
                {loadingMore && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                )}
                {!hasMore && visibleCount > INITIAL_SIZE && (
                  <p className="text-xs text-muted-foreground">
                    已显示全部 {filteredCharacters.length} 个角色
                  </p>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-12 md:py-20">
              <div className="inline-flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-xl md:rounded-2xl bg-secondary mb-4 md:mb-6">
                <Search className="h-7 w-7 md:h-10 md:w-10 text-muted-foreground" />
              </div>
              <h3 className="text-base md:text-xl font-semibold mb-1.5 md:mb-2">未找到角色</h3>
              <p className="text-xs md:text-sm text-muted-foreground mb-4 md:mb-6">
                尝试调整搜索条件或创建一个新角色
              </p>
              {user && (
                <Link href="/create">
                  <Button className="rounded-lg md:rounded-xl text-sm h-9 md:h-10">创建角色</Button>
                </Link>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 py-3 px-4 md:px-6 text-center text-xs text-muted-foreground bg-background/80 backdrop-blur-sm border-t border-border/50">
        <span>&copy; 2026 Nyx AI</span>
        <span className="mx-2">·</span>
        <Link href="/terms" className="hover:text-foreground transition-colors">用户协议</Link>
        <span className="mx-2">·</span>
        <Link href="/privacy" className="hover:text-foreground transition-colors">隐私政策</Link>
      </footer>
    </div>
  )
}
