'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { checkinApi } from '@/lib/api'
import { Gift, Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CheckinButtonProps {
    onCheckinSuccess?: (points: number) => void
}

export function CheckinButton({ onCheckinSuccess }: CheckinButtonProps) {
    const [status, setStatus] = useState<{
        has_checked_in_today: boolean
        streak_days: number
        today_points: number
        total_checkins: number
    } | null>(null)
    const [loading, setLoading] = useState(false)
    const [checking, setChecking] = useState(true)
    const [showAnimation, setShowAnimation] = useState(false)
    const [earnedPoints, setEarnedPoints] = useState(0)

    // 获取签到状态
    const fetchStatus = async () => {
        // 未登录时不发请求
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
        if (!token) {
            setChecking(false)
            return
        }
        try {
            const res = await checkinApi.getStatus()
            if (res.success) {
                setStatus(res.data)
            }
        } catch (error) {
            // 网络错误或服务未启动时静默处理，不影响页面渲染
            console.warn('获取签到状态失败:', error)
        } finally {
            setChecking(false)
        }
    }

    useEffect(() => {
        fetchStatus()
    }, [])

    // 执行签到
    const handleCheckin = async () => {
        if (loading || status?.has_checked_in_today) return

        setLoading(true)
        try {
            const res = await checkinApi.checkin()
            if (res.success) {
                const points = res.data.points_earned
                setStatus(prev => prev ? {
                    ...prev,
                    has_checked_in_today: true,
                    streak_days: res.data.streak_days,
                    total_checkins: res.data.total_checkins,
                    today_points: 0
                } : null)

                // 记录本次获得的积分，用于动画显示
                setEarnedPoints(points)
                // 显示动画
                setShowAnimation(true)
                setTimeout(() => setShowAnimation(false), 2000)

                // 回调通知父组件
                if (res.data.is_new && onCheckinSuccess) {
                    onCheckinSuccess(points)
                }
            }
        } catch (error) {
            console.error('签到失败:', error)
        } finally {
            setLoading(false)
        }
    }

    if (checking) {
        return (
            <Button variant="outline" disabled className="gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载中...
            </Button>
        )
    }

    const isCheckedIn = status?.has_checked_in_today
    const currentDay = (status?.streak_days ?? 0) + 1

    return (
        <div className="relative">
            <Button
                onClick={handleCheckin}
                disabled={loading || isCheckedIn}
                variant={isCheckedIn ? "secondary" : "default"}
                className={cn(
                    "gap-2 min-w-[140px] transition-all",
                    isCheckedIn && "bg-green-100 text-green-700 hover:bg-green-100",
                    showAnimation && "scale-105 ring-2 ring-yellow-400"
                )}
            >
                {loading ? (
                    <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        签到中...
                    </>
                ) : isCheckedIn ? (
                    <>
                        <Check className="h-4 w-4" />
                        已签到
                    </>
                ) : (
                    <>
                        <Gift className="h-4 w-4" />
                        签到 +{status?.today_points ?? 1}
                    </>
                )}
            </Button>

            {/* 连续签到指示器 */}
            {status && (
                <div className="mt-2 flex items-center gap-1 justify-center">
                    {[1, 2, 3, 4, 5, 6, 7].map((day) => (
                        <div
                            key={day}
                            className={cn(
                                "w-5 h-5 rounded-full text-[10px] flex items-center justify-center font-medium transition-colors",
                                day < currentDay
                                    ? "bg-green-500 text-white"
                                    : day === currentDay && isCheckedIn
                                        ? "bg-green-500 text-white ring-2 ring-green-300"
                                        : day === currentDay
                                            ? "bg-primary text-primary-foreground animate-pulse"
                                            : "bg-gray-200 text-gray-400"
                            )}
                        >
                            {day}
                        </div>
                    ))}
                </div>
            )}

            {/* 签到成功动画 */}
            {showAnimation && (
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
                    <span className="text-yellow-500 font-bold text-lg animate-bounce">
                        +{earnedPoints} 积分!
                    </span>
                </div>
            )}
        </div>
    )
}
