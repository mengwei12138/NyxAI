'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { CharacterCard } from '@/components/character-card'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/lib/store'
import { charactersApi } from '@/lib/api'
import type { Character } from '@/lib/api'
import { PlusCircle, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { Skeleton } from '@/components/ui/skeleton'

export default function MyCharactersPage() {
  const { user, setAuthModal } = useAppStore()
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadCharacters = async () => {
      if (!user) {
        setLoading(false)
        return
      }
      try {
        const response = await charactersApi.getList('my')
        if (response.success && response.data) {
          setCharacters(response.data)
        }
      } catch (error) {
        console.error('Failed to load characters:', error)
      } finally {
        setLoading(false)
      }
    }
    loadCharacters()
  }, [user])

  if (!user) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        <div className="pt-24 md:pt-32 px-4 text-center">
          <div className="max-w-md mx-auto">
            <div className="inline-flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-xl md:rounded-2xl bg-secondary mb-4 md:mb-6">
              <Sparkles className="h-7 w-7 md:h-10 md:w-10 text-muted-foreground" />
            </div>
            <h1 className="text-lg md:text-2xl font-semibold mb-2 md:mb-4">请先登录</h1>
            <p className="text-xs md:text-sm text-muted-foreground mb-4 md:mb-6">
              登录后即可查看和管理您创建的角色
            </p>
            <Button onClick={() => setAuthModal(true, 'login')} className="rounded-lg md:rounded-xl h-9 md:h-10 text-sm">
              立即登录
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const myCharacters = characters

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <AuthModal />

      <main className="pt-24 md:pt-32 pb-12 md:pb-20 px-4 md:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between gap-4 mb-4 md:mb-10">
            <div>
              <h1 className="text-lg md:text-3xl font-bold mb-0.5 md:mb-2">我的羁绊</h1>
              <p className="text-xs md:text-sm text-muted-foreground">
                管理您创建的所有角色
              </p>
            </div>
            <Link href="/create">
              <Button className="rounded-lg md:rounded-xl gap-1.5 md:gap-2 h-9 md:h-10 text-xs md:text-sm px-3 md:px-4">
                <PlusCircle className="h-3.5 w-3.5 md:h-4 md:w-4" />
                创建角色
              </Button>
            </Link>
          </div>

          {/* Characters Grid */}
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <Skeleton className="aspect-[3/4] w-full rounded-xl md:rounded-2xl" />
                  <Skeleton className="h-4 w-3/4 rounded-md" />
                  <Skeleton className="h-3 w-1/2 rounded-md" />
                </div>
              ))}
            </div>
          ) : myCharacters.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 md:gap-4">
              {myCharacters.map((character, index) => (
                <div
                  key={character.id}
                  className="animate-slide-up"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <CharacterCard character={character} showActions />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 md:py-20">
              <div className="inline-flex h-16 w-16 md:h-24 md:w-24 items-center justify-center rounded-2xl md:rounded-3xl bg-secondary mb-4 md:mb-6">
                <Sparkles className="h-8 w-8 md:h-12 md:w-12 text-muted-foreground" />
              </div>
              <h2 className="text-base md:text-2xl font-semibold mb-2 md:mb-3">还没有角色</h2>
              <p className="text-xs md:text-sm text-muted-foreground mb-5 md:mb-8 max-w-md mx-auto">
                创建您的第一个角色，开始与 AI 进行沉浸式对话吧！
              </p>
              <Link href="/create">
                <Button size="lg" className="h-10 md:h-14 px-5 md:px-8 rounded-xl md:rounded-2xl text-sm md:text-base gap-1.5 md:gap-2">
                  <PlusCircle className="h-4 w-4 md:h-5 md:w-5" />
                  创建第一个角色
                </Button>
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
