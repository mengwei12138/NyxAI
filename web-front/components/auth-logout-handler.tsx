'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/lib/store'

// 监听 API 层发出的 auth:logout 事件，使用 router.push 跳转首页
// 避免 window.location.href 强制刷新打断其他页面渲染
export function AuthLogoutHandler() {
    const router = useRouter()
    const { setUser } = useAppStore()

    useEffect(() => {
        const handleLogout = () => {
            setUser(null)
            router.push('/')
        }

        window.addEventListener('auth:logout', handleLogout)
        return () => window.removeEventListener('auth:logout', handleLogout)
    }, [router, setUser])

    return null
}
