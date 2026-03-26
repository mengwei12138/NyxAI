import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 根据名字哈希生成一致的背景色（HSL）
 */
export function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
    hash |= 0
  }
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 60%, 50%)`
}

/**
 * 取名字第一个有效字符（支持中英文）
 */
export function getAvatarInitial(name: string): string {
  if (!name) return '?'
  // 取第一个非空字符
  const match = name.trim().match(/[\u4e00-\u9fa5a-zA-Z0-9]/)
  return match ? match[0].toUpperCase() : name[0].toUpperCase()
}
