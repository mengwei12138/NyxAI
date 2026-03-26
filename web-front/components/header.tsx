'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useAppStore } from '@/lib/store'
import {
  Sparkles,
  Menu,
  X,
  User,
  LogOut,
  MessageSquare,
  PlusCircle,
  Coins
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

const navLinks = [
  { href: '/', label: '探索宇宙', requireAuth: false },
  { href: '/my-characters', label: '我的羁绊', requireAuth: true },
  { href: '/chats', label: '最近聊天', requireAuth: true },
]

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, setAuthModal, setUser } = useAppStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
    }
    setUser(null)
    setMobileMenuOpen(false)
    // 退出登录后返回首页
    router.push('/')
  }

  const handleNavClick = (e: React.MouseEvent, link: typeof navLinks[0]) => {
    if (link.requireAuth && !user) {
      e.preventDefault()
      setAuthModal(true, 'login')
    }
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50">
      <div className="mx-3 mt-3 md:mx-6 md:mt-4 lg:mx-8">
        <nav className="glass rounded-xl md:rounded-2xl px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between">
            {/* Mobile Menu Button - 移动端显示在左侧 */}
            <button
              className="rounded-xl p-2 transition-colors hover:bg-secondary md:hidden"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>

            {/* Logo - 移动端右侧，桌面端左侧 */}
            <Link
              href="/"
              className="flex items-center gap-2 md:gap-3 transition-opacity hover:opacity-80 md:static"
            >
              <div className="flex h-8 w-8 md:h-10 md:w-10 items-center justify-center rounded-lg md:rounded-xl bg-foreground">
                <Sparkles className="h-4 w-4 md:h-5 md:w-5 text-background" />
              </div>
              <span className="text-base md:text-xl font-semibold tracking-tight">Nyx AI</span>
            </Link>

            {/* Desktop Navigation - 居中 */}
            <div className="hidden md:flex items-center justify-center flex-1">
              <div className="flex items-center gap-2">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={(e) => handleNavClick(e, link)}
                    className={cn(
                      'rounded-xl px-4 py-2.5 text-sm font-medium transition-all',
                      pathname === link.href
                        ? 'bg-foreground text-background'
                        : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* Desktop Actions - 右侧 */}
            <div className="hidden items-center gap-4 md:flex">
              {user ? (
                <>
                  <Link href="/create">
                    <Button className="rounded-xl gap-2">
                      <PlusCircle className="h-4 w-4" />
                      创建角色
                    </Button>
                  </Link>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button className="flex items-center gap-3 rounded-xl px-3 py-2 transition-colors hover:bg-secondary">
                        <div className="flex items-center gap-2 text-sm">
                          <Coins className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{user.credits}</span>
                        </div>
                        <Avatar className="h-9 w-9 border-2 border-border">
                          <AvatarImage src={user.avatar} />
                          <AvatarFallback className="bg-secondary text-sm">
                            {user.username[0].toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56 rounded-xl p-2">
                      <div className="px-3 py-2">
                        <p className="font-medium">{user.username}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem asChild className="rounded-lg cursor-pointer">
                        <Link href="/profile" className="flex items-center gap-3">
                          <User className="h-4 w-4" />
                          个人中心
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild className="rounded-lg cursor-pointer">
                        <Link href="/chats" className="flex items-center gap-3">
                          <MessageSquare className="h-4 w-4" />
                          聊天记录
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={handleLogout}
                        className="rounded-lg cursor-pointer text-destructive focus:text-destructive"
                      >
                        <LogOut className="mr-3 h-4 w-4" />
                        退出登录
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    className="rounded-xl"
                    onClick={() => setAuthModal(true, 'login')}
                  >
                    登录
                  </Button>
                  <Button
                    className="rounded-xl"
                    onClick={() => setAuthModal(true, 'register')}
                  >
                    注册
                  </Button>
                </>
              )}
            </div>
          </div>
        </nav>
      </div>

      {/* Mobile Sidebar */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[260px] p-0">
          <SheetHeader className="px-4 pt-4 pb-3 border-b">
            <SheetTitle className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground">
                <Sparkles className="h-3.5 w-3.5 text-background" />
              </div>
              <span className="text-base font-semibold">Nyx AI</span>
            </SheetTitle>
            <SheetDescription className="sr-only">
              导航菜单
            </SheetDescription>
          </SheetHeader>

          <div className="flex flex-col h-[calc(100%-64px)]">
            {/* Navigation Links */}
            <div className="flex-1 px-3 py-3">
              <div className="flex flex-col gap-0.5">
                <Link
                  href="/"
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    'rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    pathname === '/'
                      ? 'bg-foreground text-background'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                  )}
                >
                  探索宇宙
                </Link>
                {user && (
                  <>
                    <Link
                      href="/my-characters"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        pathname === '/my-characters'
                          ? 'bg-foreground text-background'
                          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                      )}
                    >
                      我的羁绊
                    </Link>
                    <Link
                      href="/chats"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        pathname === '/chats'
                          ? 'bg-foreground text-background'
                          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                      )}
                    >
                      最近聊天
                    </Link>
                    <Link
                      href="/profile"
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        'rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        pathname === '/profile'
                          ? 'bg-foreground text-background'
                          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                      )}
                    >
                      个人中心
                    </Link>
                  </>
                )}
              </div>
            </div>

            {/* User Section */}
            <div className="px-3 py-3 border-t">
              {user ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 px-1">
                    <Avatar className="h-9 w-9 border-2 border-border">
                      <AvatarImage src={user.avatar} />
                      <AvatarFallback className="bg-secondary text-sm">
                        {user.username[0].toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{user.username}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Coins className="h-3 w-3" />
                        {user.credits} 积分
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <LogOut className="inline-block mr-2 h-4 w-4" />
                    退出登录
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <Button
                    className="w-full rounded-lg h-9 text-sm"
                    onClick={() => {
                      setAuthModal(true, 'register')
                      setMobileMenuOpen(false)
                    }}
                  >
                    注册
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full rounded-lg h-9 text-sm"
                    onClick={() => {
                      setAuthModal(true, 'login')
                      setMobileMenuOpen(false)
                    }}
                  >
                    登录
                  </Button>
                </div>
              )}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  )
}
