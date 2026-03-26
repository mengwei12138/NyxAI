'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Header } from '@/components/header'
import { AuthModal } from '@/components/auth-modal'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/lib/store'
import { chatApi } from '@/lib/api'
import { MessageSquare, ArrowRight, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatSession {
  characterId: string
  character: {
    id: string
    name: string
    avatar?: string
    greeting: string
  }
  lastMessage: {
    content: string
    timestamp: string
  } | null
  messageCount: number
}

export default function ChatsPage() {
  const { user, setAuthModal } = useAppStore()
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(true)

  // useEffect 必须在所有条件返回之前调用（Rules of Hooks）
  useEffect(() => {
    const loadSessions = async () => {
      if (!user) {
        setLoading(false)
        return
      }
      try {
        const response = await chatApi.getSessions()
        if (response.success && response.data) {
          setChatSessions(response.data.map((item: any) => ({
            characterId: String(item.role_id),
            character: {
              id: String(item.character.id),
              name: item.character.name,
              avatar: item.character.avatar,
              greeting: item.character.greeting,
            },
            lastMessage: item.last_message,
            messageCount: item.message_count,
          })))
        }
      } catch (error) {
        console.error('Failed to load chat sessions:', error)
      } finally {
        setLoading(false)
      }
    }
    loadSessions()
  }, [user])

  if (!user) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <AuthModal />
        <div className="pt-24 md:pt-32 px-4 text-center">
          <div className="max-w-md mx-auto">
            <div className="inline-flex h-14 w-14 md:h-20 md:w-20 items-center justify-center rounded-xl md:rounded-2xl bg-secondary mb-4 md:mb-6">
              <MessageSquare className="h-7 w-7 md:h-10 md:w-10 text-muted-foreground" />
            </div>
            <h1 className="text-lg md:text-2xl font-semibold mb-2 md:mb-4">请先登录</h1>
            <p className="text-xs md:text-sm text-muted-foreground mb-4 md:mb-6">
              登录后即可查看您的聊天记录
            </p>
            <Button onClick={() => setAuthModal(true, 'login')} className="rounded-lg md:rounded-xl h-9 md:h-10 text-sm">
              立即登录
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <AuthModal />

      <main className="pt-24 md:pt-32 pb-12 md:pb-20 px-4 md:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-4 md:mb-10">
            <h1 className="text-lg md:text-3xl font-bold mb-0.5 md:mb-2">最近聊天</h1>
            <p className="text-xs md:text-sm text-muted-foreground">
              您最近与角色的对话
            </p>
          </div>

          {/* Chat List */}
          {loading ? (
            <div className="space-y-2 md:space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="glass rounded-xl md:rounded-2xl p-4 md:p-6 animate-pulse">
                  <div className="flex items-center gap-3 md:gap-5">
                    <div className="h-11 w-11 md:h-14 md:w-14 rounded-lg md:rounded-xl bg-secondary flex-shrink-0" />
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="h-4 w-24 rounded bg-secondary" />
                        <div className="h-3 w-12 rounded bg-secondary/70" />
                      </div>
                      <div className="h-3 w-3/4 rounded bg-secondary/70" />
                      <div className="h-3 w-16 rounded bg-secondary/50" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : chatSessions.length > 0 ? (
            <div className="space-y-2 md:space-y-4">
              {chatSessions.map((chat, index) => {
                const { character, lastMessage, messageCount } = chat

                return (
                  <Link
                    key={character.id}
                    href={`/chat/${character.id}`}
                    className="block animate-slide-up"
                    style={{ animationDelay: `${index * 0.03}s` }}
                  >
                    <div className="glass rounded-xl md:rounded-2xl p-4 md:p-6 transition-all hover:shadow-lg hover:scale-[1.01]">
                      <div className="flex items-center gap-3 md:gap-5">
                        <Avatar className="h-11 w-11 md:h-14 md:w-14 rounded-lg md:rounded-xl border-2 border-border flex-shrink-0">
                          <AvatarImage src={character.avatar} />
                          <AvatarFallback className="rounded-lg md:rounded-xl bg-secondary text-sm md:text-lg">
                            {character.name.slice(0, 2)}
                          </AvatarFallback>
                        </Avatar>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-0.5 md:mb-1">
                            <h3 className="font-semibold text-sm md:text-lg">{character.name}</h3>
                            <span className="text-[10px] md:text-sm text-muted-foreground">
                              {lastMessage &&
                                new Date(lastMessage.timestamp).toLocaleDateString('zh-CN', {
                                  month: 'short',
                                  day: 'numeric',
                                })}
                            </span>
                          </div>
                          <p className="text-muted-foreground text-xs md:text-sm line-clamp-1 mb-1 md:mb-2">
                            {lastMessage?.content || character.greeting}
                          </p>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] md:text-xs text-muted-foreground">
                              {messageCount} 条消息
                            </span>
                            <ArrowRight className="h-3.5 w-3.5 md:h-4 md:w-4 text-muted-foreground" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-12 md:py-20">
              <div className="inline-flex h-16 w-16 md:h-24 md:w-24 items-center justify-center rounded-2xl md:rounded-3xl bg-secondary mb-4 md:mb-6">
                <MessageSquare className="h-8 w-8 md:h-12 md:w-12 text-muted-foreground" />
              </div>
              <h2 className="text-base md:text-2xl font-semibold mb-2 md:mb-3">还没有聊天记录</h2>
              <p className="text-xs md:text-sm text-muted-foreground mb-5 md:mb-8 max-w-md mx-auto">
                浏览角色列表，找到您喜欢的角色开始对话吧！
              </p>
              <Link href="/">
                <Button size="lg" className="h-10 md:h-14 px-5 md:px-8 rounded-xl md:rounded-2xl text-sm md:text-base gap-1.5 md:gap-2">
                  <Sparkles className="h-4 w-4 md:h-5 md:w-5" />
                  探索宇宙
                </Button>
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
