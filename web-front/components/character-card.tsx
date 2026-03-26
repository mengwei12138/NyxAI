'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Character } from '@/lib/api'
import { cn, getAvatarColor, getAvatarInitial } from '@/lib/utils'

interface CharacterCardProps {
  character: Character
  className?: string
  showActions?: boolean
  aspectRatio?: '3/4' | '4/3' | '1/1'
}

export function CharacterCard({ character, className, showActions = false, aspectRatio = '3/4' }: CharacterCardProps) {
  const router = useRouter()
  const [showOverlay, setShowOverlay] = useState(false)
  const initial = getAvatarInitial(character.name)
  const avatarBg = getAvatarColor(character.name)

  const handleCardClick = () => {
    if (showActions && showOverlay) {
      return
    }
    router.push(`/character/${character.id}`)
  }

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    router.push(`/character/${character.id}/edit`)
  }

  const handleChatClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    router.push(`/chat/${character.id}`)
  }

  return (
    <article
      onClick={handleCardClick}
      onMouseEnter={() => showActions && setShowOverlay(true)}
      onMouseLeave={() => showActions && setShowOverlay(false)}
      className={cn(
        'group relative transition-all duration-300',
        'hover:-translate-y-1',
        'cursor-pointer',
        className
      )}
    >
      {/* Cover Area */}
      <div className={cn("relative overflow-hidden rounded-xl bg-secondary", {
        'aspect-[3/4]': aspectRatio === '3/4',
        'aspect-[4/3]': aspectRatio === '4/3',
        'aspect-square': aspectRatio === '1/1',
      })}>
        {/* Character Image or Fallback */}
        {character.avatar ? (
          <Image
            src={character.avatar}
            alt={character.name}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center text-4xl font-bold text-white select-none"
            style={{ background: avatarBg }}
          >
            <span>{initial}</span>
          </div>
        )}

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* 名字覆盖层：图片内底部（移动端 showActions 时隐藏，避免与按钮重叠） */}
        <div className={cn(
          "absolute bottom-0 left-0 right-0 p-3 z-10 transition-opacity duration-300",
          showActions ? "hidden md:block" : "block",
          showActions && showOverlay ? "md:opacity-0" : "md:opacity-100"
        )}>
          <h3 className="font-bold text-white text-sm mb-1 truncate drop-shadow-lg">
            {character.title || character.name}
          </h3>
        </div>

        {/* Hover action overlay - 普通卡片 */}
        {!showActions && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-20">
            <span className="px-4 py-2 bg-white text-black text-xs font-medium rounded-full">
              开始对话
            </span>
          </div>
        )}

        {/* 编辑/聊天按钮 */}
        {showActions && (
          <>
            {/* Desktop: hover 显示 */}
            <div className={cn(
              "hidden md:flex absolute inset-0 flex-col items-center justify-end pb-3 bg-black/50 z-20 transition-opacity duration-300",
              showOverlay ? "opacity-100" : "opacity-0"
            )}>
              <div className="flex gap-2 w-full px-3">
                <button
                  onClick={handleEditClick}
                  className="flex-1 text-center py-1.5 rounded-lg text-[10px] font-medium bg-white/20 text-white hover:bg-white/30 transition-colors backdrop-blur-sm"
                >
                  编辑
                </button>
                <button
                  onClick={handleChatClick}
                  className="flex-1 text-center py-1.5 rounded-lg text-[10px] font-medium bg-white text-black hover:bg-white/90 transition-colors"
                >
                  聊天
                </button>
              </div>
            </div>
            {/* Mobile: 始终显示在图片底部 */}
            <div className="flex md:hidden absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/90 to-transparent z-20">
              <div className="flex gap-2 w-full">
                <button
                  onClick={handleEditClick}
                  className="flex-1 text-center py-1.5 rounded-lg text-[10px] font-medium bg-white/20 text-white"
                >
                  编辑
                </button>
                <button
                  onClick={handleChatClick}
                  className="flex-1 text-center py-1.5 rounded-lg text-[10px] font-medium bg-white text-black"
                >
                  聊天
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 移动端 showActions 时，名字在卡片下方居中显示 */}
      {showActions && (
        <p className="md:hidden mt-1.5 text-xs font-medium truncate text-center text-foreground">
          {character.title || character.name}
        </p>
      )}
    </article>
  )
}
