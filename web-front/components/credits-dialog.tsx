'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useAppStore } from '@/lib/store'
import { Coins, AlertCircle } from 'lucide-react'

interface CreditsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  amount: number
  action: string
  onConfirm: () => void
}

export function CreditsDialog({
  open,
  onOpenChange,
  amount,
  action,
  onConfirm,
}: CreditsDialogProps) {
  const { user } = useAppStore()
  const hasEnoughCredits = user && user.credits >= amount

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="rounded-3xl border-0 shadow-2xl max-w-md">
        <AlertDialogHeader className="text-center">
          <div className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl ${
            hasEnoughCredits ? 'bg-secondary' : 'bg-destructive/10'
          }`}>
            {hasEnoughCredits ? (
              <Coins className="h-8 w-8 text-foreground" />
            ) : (
              <AlertCircle className="h-8 w-8 text-destructive" />
            )}
          </div>
          <AlertDialogTitle className="text-xl">
            {hasEnoughCredits ? '确认消费' : '积分不足'}
          </AlertDialogTitle>
          <AlertDialogDescription className="text-base leading-relaxed">
            {hasEnoughCredits ? (
              <>
                {action}需要消耗 <span className="font-semibold text-foreground">{amount}</span> 积分。
                <br />
                当前余额：<span className="font-semibold text-foreground">{user?.credits}</span> 积分
              </>
            ) : (
              <>
                {action}需要 <span className="font-semibold text-foreground">{amount}</span> 积分，
                但您当前只有 <span className="font-semibold text-foreground">{user?.credits || 0}</span> 积分。
              </>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col gap-2 sm:flex-col">
          {hasEnoughCredits ? (
            <>
              <AlertDialogAction
                onClick={onConfirm}
                className="h-12 rounded-2xl text-base"
              >
                确认消费
              </AlertDialogAction>
              <AlertDialogCancel className="h-12 rounded-2xl text-base border-0 bg-secondary">
                取消
              </AlertDialogCancel>
            </>
          ) : (
            <AlertDialogCancel className="h-12 rounded-2xl text-base">
              知道了
            </AlertDialogCancel>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
