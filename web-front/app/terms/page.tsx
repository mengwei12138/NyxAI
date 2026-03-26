import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export const metadata = {
    title: '用户协议 - Nyx AI',
    description: 'Nyx AI 用户服务协议',
}

export default function TermsPage() {
    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-3xl mx-auto px-6 py-12">
                {/* 返回 */}
                <Link
                    href="/"
                    className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
                >
                    <ArrowLeft className="h-4 w-4" />
                    返回首页
                </Link>

                <h1 className="text-3xl font-bold mb-2">用户服务协议</h1>
                <p className="text-sm text-muted-foreground mb-10">最后更新：2026 年 3 月</p>

                <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8 text-sm leading-7">

                    {/* 一、接受条款 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">一、接受条款</h2>
                        <p>
                            欢迎使用 Nyx AI（以下简称"本平台"或"我们"）。在使用本平台提供的服务之前，请您仔细阅读本用户服务协议（以下简称"本协议"）。
                            <strong>注册账户即表示您已阅读、理解并同意受本协议约束。</strong>
                            如您不同意本协议的任何条款，请立即停止使用本平台的服务。
                        </p>
                    </section>

                    {/* 二、年龄限制 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">二、年龄限制与成人内容声明</h2>
                        <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 px-5 py-4 mb-4">
                            <p className="font-semibold text-amber-800 dark:text-amber-300 mb-1">⚠️ 重要年龄限制</p>
                            <p className="text-amber-700 dark:text-amber-400">
                                本平台包含成人向内容（包括但不限于成人主题的角色扮演、对话及相关内容），
                                <strong>严格限制 18 周岁以上用户使用。</strong>
                                未满 18 周岁的未成年人禁止注册或使用本平台的任何服务。
                            </p>
                        </div>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>注册时您须确认自己已年满 18 周岁，并对此声明的真实性承担法律责任。</li>
                            <li>若我们发现用户为未成年人，将立即终止该账户并删除相关数据。</li>
                            <li>家长或监护人如发现未成年人使用本平台，请立即联系我们进行处理。</li>
                        </ul>
                    </section>

                    {/* 三、服务内容 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">三、服务内容</h2>
                        <p className="mb-3">Nyx AI 提供基于 AI 技术的角色扮演对话服务，包括：</p>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>与 AI 角色进行沉浸式对话</li>
                            <li>创建、定制和分享 AI 角色</li>
                            <li>文字转语音（TTS）语音合成功能</li>
                            <li>AI 图像生成功能</li>
                            <li>积分充值与消费系统</li>
                        </ul>
                        <p className="mt-3 text-muted-foreground">
                            我们保留在任何时候修改、暂停或终止部分或全部服务的权利，并会尽合理努力提前通知用户。
                        </p>
                    </section>

                    {/* 四、账户注册与安全 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">四、账户注册与安全</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>您须提供真实、准确的注册信息，并及时更新以保持信息准确。</li>
                            <li>您对账户的安全负责，须妥善保管密码，不得将账户转让或共享给他人。</li>
                            <li>如发现账户被未授权访问，须立即通知我们。</li>
                            <li>我们不对因您未妥善保管账户信息而造成的损失承担责任。</li>
                        </ul>
                    </section>

                    {/* 五、积分与付费服务 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">五、积分与付费服务</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>新用户注册后将获赠一定数量的免费积分，具体以平台公告为准。</li>
                            <li>积分仅可用于本平台的虚拟服务消费，不可兑换现金或转让他人。</li>
                            <li>充值积分一经购买，原则上不予退款，但因平台技术故障导致的积分损失除外。</li>
                            <li>我们保留调整积分价格及消耗规则的权利，并会提前公告。</li>
                            <li>账户注销后，剩余积分将被清空，无法找回。</li>
                        </ul>
                    </section>

                    {/* 六、用户行为准则 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">六、用户行为准则</h2>
                        <p className="mb-3">您同意在使用本平台时遵守以下规则：</p>
                        <div className="space-y-2">
                            <p className="font-medium">您不得：</p>
                            <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                                <li>发布、传播违法、有害、骚扰性、诽谤性、侵权、有害他人隐私的内容</li>
                                <li>使用本平台从事任何违法犯罪活动</li>
                                <li>干扰或破坏平台服务的正常运行</li>
                                <li>尝试未经授权访问平台系统或其他用户数据</li>
                                <li>对平台内容进行逆向工程、抓取或未经授权的商业使用</li>
                                <li>创建含有真实人物肖像的不当内容</li>
                                <li>传播涉及未成年人的任何性相关内容（此类行为将立即封号并向相关部门举报）</li>
                            </ul>
                        </div>
                    </section>

                    {/* 七、内容所有权 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">七、内容与知识产权</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>您创建的角色和对话内容归您所有，但您授予我们在平台范围内使用、存储和展示的权利。</li>
                            <li>设置为"公开"的角色将对所有用户可见，您同意此展示行为。</li>
                            <li>平台本身的技术、界面、商标等知识产权归 Nyx AI 所有。</li>
                            <li>AI 生成的内容（包括对话回复、图像等）的使用权归注册用户，但我们不对 AI 生成内容的准确性或适用性作出保证。</li>
                        </ul>
                    </section>

                    {/* 八、免责声明 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">八、免责声明</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>本平台提供的 AI 服务为娱乐性质，AI 角色的回复不构成任何专业建议（包括但不限于医疗、法律、心理健康建议）。</li>
                            <li>我们不对 AI 生成内容的准确性、完整性或适用性作出任何明示或暗示的保证。</li>
                            <li>因不可抗力、第三方服务故障等原因导致的服务中断，我们不承担赔偿责任。</li>
                            <li>在法律允许的最大范围内，我们对使用本服务所产生的间接损失不承担责任。</li>
                        </ul>
                    </section>

                    {/* 九、账户终止 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">九、账户终止</h2>
                        <p className="text-muted-foreground">
                            我们保留在以下情况下暂停或终止您的账户的权利：违反本协议条款、从事违法行为、长期不活跃账户（超过 12 个月）、
                            以及平台停止运营。您也可以随时联系我们注销账户，注销后相关数据将按照隐私政策处理。
                        </p>
                    </section>

                    {/* 十、协议变更 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">十、协议变更</h2>
                        <p className="text-muted-foreground">
                            我们可能会不时更新本协议。重大变更将通过平台公告或邮件通知用户。
                            在变更生效后继续使用本平台，即表示您接受更新后的协议。
                        </p>
                    </section>

                    {/* 十一、联系方式 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">十一、联系我们</h2>
                        <p className="text-muted-foreground">
                            如对本协议有任何疑问，请通过以下方式联系我们：
                        </p>
                        <p className="mt-2 text-muted-foreground">
                            Telegram 群组：
                            <a href="https://t.me/nyxai_chat" className="text-foreground hover:underline ml-1" target="_blank" rel="noopener noreferrer">
                                @nyxai_chat
                            </a>
                        </p>
                    </section>

                </div>

                <div className="mt-12 pt-8 border-t border-border text-center text-xs text-muted-foreground">
                    <p>&copy; 2026 Nyx AI · 保留所有权利</p>
                    <div className="flex items-center justify-center gap-4 mt-2">
                        <Link href="/terms" className="hover:text-foreground transition-colors">用户协议</Link>
                        <span>·</span>
                        <Link href="/privacy" className="hover:text-foreground transition-colors">隐私政策</Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
