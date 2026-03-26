import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export const metadata = {
    title: '隐私政策 - Nyx AI',
    description: 'Nyx AI 隐私政策',
}

export default function PrivacyPage() {
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

                <h1 className="text-3xl font-bold mb-2">隐私政策</h1>
                <p className="text-sm text-muted-foreground mb-10">最后更新：2026 年 3 月</p>

                <div className="prose prose-neutral dark:prose-invert max-w-none space-y-8 text-sm leading-7">

                    {/* 一、概述 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">一、概述</h2>
                        <p>
                            Nyx AI（以下简称"我们"）深知隐私对您的重要性。本隐私政策说明我们如何收集、使用、存储和保护您在使用本平台时提供的个人信息。
                            使用本平台即表示您同意本隐私政策所述的数据处理方式。
                        </p>
                    </section>

                    {/* 二、收集的信息 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">二、我们收集的信息</h2>

                        <h3 className="font-medium mb-2">2.1 您主动提供的信息</h3>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground mb-4">
                            <li><strong>账户信息：</strong>用户名、密码（加密存储）、邮箱地址（可选）</li>
                            <li><strong>年龄声明：</strong>注册时的 18+ 年龄确认记录</li>
                            <li><strong>内容数据：</strong>您创建的角色设定、与 AI 的对话记录</li>
                            <li><strong>支付信息：</strong>充值订单记录（我们不存储银行卡或支付账号信息，支付由第三方平台处理）</li>
                        </ul>

                        <h3 className="font-medium mb-2">2.2 自动收集的信息</h3>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground mb-4">
                            <li><strong>日志数据：</strong>IP 地址、访问时间、请求记录（用于安全审计）</li>
                            <li><strong>使用数据：</strong>功能使用频率、积分消耗记录（用于服务优化）</li>
                            <li><strong>设备信息：</strong>浏览器类型、操作系统（通过 User-Agent 获取）</li>
                        </ul>

                        <h3 className="font-medium mb-2">2.3 我们不收集的信息</h3>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>真实姓名或身份证件信息</li>
                            <li>精确地理位置</li>
                            <li>通讯录或设备文件</li>
                        </ul>
                    </section>

                    {/* 三、信息使用方式 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">三、信息使用方式</h2>
                        <p className="mb-3">我们使用收集的信息用于以下目的：</p>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li><strong>提供服务：</strong>维护账户、处理对话请求、生成 AI 内容</li>
                            <li><strong>安全保障：</strong>检测违规行为、防范欺诈和滥用</li>
                            <li><strong>服务改进：</strong>分析使用模式以优化产品体验（仅使用匿名化数据）</li>
                            <li><strong>积分管理：</strong>记录充值、消费及赠送的积分流水</li>
                            <li><strong>法律合规：</strong>响应合法的政府或法院要求</li>
                        </ul>
                        <p className="mt-3 text-muted-foreground">
                            我们<strong>不会</strong>将您的个人信息出售给第三方，也不会将其用于与服务无关的商业广告目的。
                        </p>
                    </section>

                    {/* 四、数据存储与安全 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">四、数据存储与安全</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>用户数据存储于安全的云数据库服务，服务器位于境外数据中心。</li>
                            <li>密码使用 bcrypt 算法单向加密存储，我们无法获取您的明文密码。</li>
                            <li>数据传输通过 HTTPS 加密协议保护。</li>
                            <li>我们定期进行安全审计，并采取合理的技术和管理措施防止数据泄露。</li>
                            <li>对话记录保存于您的账户下，您可以随时通过注销账户的方式请求删除。</li>
                        </ul>
                    </section>

                    {/* 五、数据共享 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">五、数据共享与第三方服务</h2>
                        <p className="mb-3">为提供服务，我们会与以下类型的第三方共享必要的数据：</p>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>
                                <strong>AI 服务提供商：</strong>对话内容会发送至 AI 模型服务商进行处理，以生成回复。
                                这些服务商有自己的隐私政策，我们建议您查阅。
                            </li>
                            <li>
                                <strong>支付平台：</strong>充值时会跳转至第三方支付平台（爱发电），
                                我们不接触您的支付账户信息。
                            </li>
                            <li>
                                <strong>语音服务：</strong>TTS 功能会将文本内容发送至语音合成服务商进行处理。
                            </li>
                            <li>
                                <strong>图像生成：</strong>文生图功能会将描述词发送至图像生成服务商。
                            </li>
                        </ul>
                        <p className="mt-3 text-muted-foreground">
                            除上述情况外，我们不会未经您的明确同意向第三方披露您的个人信息，
                            但法律法规要求或保护我们、用户及公众的安全所必需的情况除外。
                        </p>
                    </section>

                    {/* 六、Cookie */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">六、Cookie 与本地存储</h2>
                        <p className="text-muted-foreground mb-3">
                            本平台使用浏览器 localStorage 存储您的登录凭证（JWT Token），以维持登录状态。
                            该数据仅存储于您的设备本地，不会上传至服务器。
                        </p>
                        <p className="text-muted-foreground">
                            您可以随时通过清除浏览器数据来删除本地存储的登录信息，这将使您退出登录状态。
                        </p>
                    </section>

                    {/* 七、未成年人保护 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">七、未成年人保护</h2>
                        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800 px-5 py-4">
                            <p className="text-red-700 dark:text-red-400">
                                本平台<strong>严格禁止未满 18 周岁的未成年人</strong>注册或使用。
                                我们不会故意收集未成年人的个人信息。如发现有未成年人用户，
                                我们将立即终止其账户并删除相关数据。
                                如果您是家长或监护人，并认为您的孩子可能在未经授权的情况下使用了本平台，
                                请立即联系我们。
                            </p>
                        </div>
                    </section>

                    {/* 八、您的权利 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">八、您的数据权利</h2>
                        <p className="mb-3">您对自己的个人数据拥有以下权利：</p>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li><strong>访问权：</strong>您可以在账户设置中查看您的账户信息和积分记录。</li>
                            <li><strong>修改权：</strong>您可以修改账户资料和密码。</li>
                            <li><strong>删除权：</strong>您可以申请注销账户，注销后我们将删除或匿名化您的个人数据（法律要求保留的除外）。</li>
                            <li><strong>导出权：</strong>如需导出您的对话记录，请联系我们。</li>
                        </ul>
                        <p className="mt-3 text-muted-foreground">
                            请注意，账户注销后无法恢复，剩余积分也将被清空。
                        </p>
                    </section>

                    {/* 九、数据保留 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">九、数据保留期限</h2>
                        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                            <li>账户数据：在您主动注销前持续保留。</li>
                            <li>对话记录：与账户数据同步，注销后删除。</li>
                            <li>支付记录：依据法律要求保留不少于 5 年。</li>
                            <li>安全日志：保留 90 天后自动清除。</li>
                        </ul>
                    </section>

                    {/* 十、隐私政策变更 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">十、隐私政策变更</h2>
                        <p className="text-muted-foreground">
                            我们可能会根据业务发展或法律要求更新本隐私政策。重大变更将通过平台公告通知您。
                            建议您定期查阅本页面以了解最新政策。在变更生效后继续使用本平台，
                            即表示您接受更新后的隐私政策。
                        </p>
                    </section>

                    {/* 十一、联系我们 */}
                    <section>
                        <h2 className="text-lg font-semibold mb-3">十一、联系我们</h2>
                        <p className="text-muted-foreground mb-3">
                            如您对本隐私政策有任何疑问，或希望行使您的数据权利，请通过以下方式联系我们：
                        </p>
                        <p className="text-muted-foreground">
                            Telegram 群组：
                            <a href="https://t.me/nyxai_chat" className="text-foreground hover:underline ml-1" target="_blank" rel="noopener noreferrer">
                                @nyxai_chat
                            </a>
                        </p>
                        <p className="mt-2 text-muted-foreground text-xs">
                            我们承诺在收到您的合理请求后 30 天内回复。
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
