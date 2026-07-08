<template>
	<AppShell active="agent">
		<view class="chat-page">
			<view class="chat-sidebar">
				<view class="assistant-brand">
					<view class="ai-logo">AI</view>
					<view>
						<text>AI 养宠助手</text>
						<text>温柔、耐心、有边界</text>
					</view>
				</view>
				<button class="new-chat" @click="newChat">新建会话</button>
				<view class="history-block">
					<view class="history-title">历史会话</view>
					<scroll-view class="history-list" scroll-y>
						<view v-if="!sessions.length" class="history-empty">还没有历史会话，发起一次咨询后会显示在这里。</view>
						<view
							v-for="item in visibleSessions"
							:key="item.id"
							class="history-item"
							:class="{ active: item.id === sessionId }"
							@click="openSession(item.id)"
						>
							<view class="history-row">
								<text class="history-name">{{ sessionTitle(item) }}</text>
								<button class="delete-chat" @click.stop="confirmDeleteSession(item)">删</button>
							</view>
							<text class="history-preview">{{ previewText(item.last_message) }}</text>
							<view class="history-meta">
								<text>{{ timeText(item.updated_at) }}</text>
								<text v-if="item.is_pending" class="pending-dot">生成中</text>
							</view>
						</view>
					</scroll-view>
				</view>
				<view class="pet-context">
					<text class="side-label">当前咨询</text>
					<text>日常养宠问答</text>
					<text class="muted">健康相关内容会保留风险提示，不替代兽医诊断。</text>
				</view>
			</view>
			<view class="chat-main">
				<view class="chat-header">
					<view>
						<text class="chat-title">今天想了解什么？</text>
						<text class="chat-sub">我会尽量说得轻松一点，也会把重要提醒讲清楚。</text>
					</view>
					<text class="shield">安全问答</text>
				</view>
				<scroll-view class="mobile-history" scroll-x>
					<view v-if="!sessions.length" class="mobile-history-empty">暂无历史会话</view>
					<view
						v-for="item in visibleSessions"
						:key="item.id"
						class="mobile-history-item"
						:class="{ active: item.id === sessionId }"
						@click="openSession(item.id)"
					>
						<text>{{ sessionTitle(item) }}</text>
						<button class="mobile-delete-chat" @click.stop="confirmDeleteSession(item)">×</button>
					</view>
				</scroll-view>
				<scroll-view class="messages" scroll-y scroll-with-animation :scroll-into-view="scrollTarget">
					<view v-if="!messages.length" class="welcome">
						<view class="welcome-icon">AI</view>
						<text class="welcome-title">你好，我是小宠</text>
						<text class="welcome-sub">可以问我日常护理、喂养、行为习惯和知识库相关问题。严肃健康问题我会提醒你及时找兽医。</text>
						<view class="suggestions">
							<view v-for="item in suggestions" :key="item" @click="ask(item)">{{ item }}</view>
						</view>
					</view>
					<view
						v-for="(msg,index) in messages"
						:id="`msg-${index}`"
						:key="msg.id || index"
						class="message-row"
						:class="msg.role"
					>
						<view class="message-avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</view>
						<view class="message-wrap">
							<view class="message-time">{{ messageTime(msg) }}</view>
							<view class="bubble">
								<view v-for="(block, blockIndex) in formatMessage(msg.content)" :key="blockIndex" :class="`message-${block.type}`">
									<text v-if="block.type !== 'list'">{{ block.text }}</text>
									<view v-else>
										<view v-for="(line, lineIndex) in block.items" :key="lineIndex" class="message-list-item">
											<text class="list-marker">{{ lineIndex + 1 }}.</text>
											<text>{{ line }}</text>
										</view>
									</view>
								</view>
								<view v-if="msg.risk_level && ['medical','high'].includes(msg.risk_level)" class="risk">
									这条回复涉及健康风险。如果症状持续、加重或出现急症，请及时联系兽医。
								</view>
							</view>
						</view>
					</view>
					<view v-if="sending" id="pending-answer" class="message-row assistant">
						<view class="message-avatar">AI</view>
						<view class="message-wrap">
							<view class="message-time">正在生成</view>
							<view class="bubble typing">
								<text>我在整理回答，稍等一下就好。</text>
							</view>
						</view>
					</view>
				</scroll-view>
				<view class="composer">
					<textarea
						v-model="input"
						auto-height
						maxlength="1000"
						placeholder="输入你的问题，比如：幼猫每天应该吃几顿？"
						@confirm="send"
					/>
					<button :disabled="sending" @click="send">发送</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { agentApi } from '../../api'

const ACTIVE_SESSION_KEY = 'agent_qa_active_session_id'

function cleanAssistantText(content = '') {
	return String(content)
		.replace(/\r\n/g, '\n')
		.replace(/[\u200B-\u200D\uFEFF]/g, '')
		.replace(/#{1,6}\s*/g, '')
		.replace(/\*\*(.*?)\*\*/g, '$1')
		.replace(/__(.*?)__/g, '$1')
		.replace(/`([^`]+)`/g, '$1')
		.replace(/^\s*[-*_]{3,}\s*$/gm, '')
		.replace(/[•●◆◇▶▷]+/g, '-')
		.replace(/[🐾✨🌟💡✅❗️❌🔥]+/g, '')
		.replace(/\n{3,}/g, '\n\n')
		.trim()
}

function formatMessageTime(value, withDate = false) {
	if (!value) return ''
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return ''

	const now = new Date()
	const isSameDay = date.toDateString() === now.toDateString()
	const yesterday = new Date(now)
	yesterday.setDate(now.getDate() - 1)
	const isYesterday = date.toDateString() === yesterday.toDateString()
	const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
	const period = date.getHours() < 6 ? '凌晨' : date.getHours() < 12 ? '上午' : date.getHours() < 18 ? '下午' : '晚上'

	if (withDate) {
		return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${period} ${time}`
	}
	if (isSameDay) return `今天 ${period} ${time}`
	if (isYesterday) return `昨天 ${period} ${time}`
	return `${date.getMonth() + 1}/${date.getDate()} ${period} ${time}`
}

export default {
	components: { AppShell },
	data() {
		return {
			sessionId: null,
			input: '',
			messages: [],
			sessions: [],
			sending: false,
			loadingSession: false,
			scrollTarget: '',
			pollTimer: null,
			suggestions: [
				'幼猫每天应该吃几顿？',
				'狗狗突然不爱喝水怎么办？',
				'怎样帮宠物适应新环境？'
			]
		}
	},
	computed: {
		visibleSessions() {
			return this.sessions.slice(0, 10)
		}
	},
	onShow() {
		this.restore()
	},
	onHide() {
		this.stopPolling()
	},
	onUnload() {
		this.stopPolling()
	},
	methods: {
		async restore() {
			if (!uni.getStorageSync('access_token')) return
			await this.loadSessions()
			const storedId = Number(uni.getStorageSync(ACTIVE_SESSION_KEY) || 0)
			const activeId = storedId || this.sessions[0]?.id
			if (activeId) await this.openSession(activeId, { silent: true })
		},
		async loadSessions() {
			try {
				this.sessions = await agentApi.listSessions() || []
			} catch (e) {
				this.sessions = []
			}
		},
		async openSession(id, options = {}) {
			if (!id || this.loadingSession) return
			this.loadingSession = true
			try {
				const session = await agentApi.session(id)
				this.sessionId = session.id
				this.messages = session.messages || []
				uni.setStorageSync(ACTIVE_SESSION_KEY, session.id)
				this.sending = this.hasPendingAnswer()
				if (this.sending) this.startPolling()
				else this.stopPolling()
				if (options.scroll !== false) this.scroll()
			} catch (e) {
				if (!options.silent) uni.showToast({ title: e.message, icon: 'none' })
			} finally {
				this.loadingSession = false
			}
		},
		async newChat() {
			this.stopPolling()
			this.sessionId = null
			this.messages = []
			this.sending = false
			uni.removeStorageSync(ACTIVE_SESSION_KEY)
			await this.loadSessions()
		},
		confirmDeleteSession(item) {
			uni.showModal({
				title: '删除会话',
				content: `确定删除“${this.sessionTitle(item)}”吗？删除后当前聊天记录将不再显示。`,
				confirmText: '删除',
				confirmColor: '#d94b3d',
				success: res => {
					if (res.confirm) this.deleteSession(item.id)
				}
			})
		},
		async deleteSession(id) {
			if (!id) return
			const deletingActive = id === this.sessionId
			try {
				await agentApi.deleteSession(id)
				await this.loadSessions()
				if (deletingActive) {
					this.stopPolling()
					const next = this.sessions[0]
					if (next) {
						await this.openSession(next.id, { scroll: false })
					} else {
						this.sessionId = null
						this.messages = []
						this.sending = false
						uni.removeStorageSync(ACTIVE_SESSION_KEY)
					}
				}
				uni.showToast({ title: '会话已删除', icon: 'none' })
			} catch (e) {
				uni.showToast({ title: e.message || '删除失败', icon: 'none' })
			}
		},
		ask(text) {
			this.input = text
			this.send()
		},
		async send() {
			const content = this.input.trim()
			if (!content || this.sending) return
			if (!uni.getStorageSync('access_token')) {
				uni.navigateTo({ url: '/pages/auth/login' })
				return
			}
			this.input = ''
			this.sending = true
			try {
				if (!this.sessionId) {
					const session = await agentApi.createSession({ title: content.slice(0, 48) })
					this.sessionId = session.id
					uni.setStorageSync(ACTIVE_SESSION_KEY, session.id)
				}
				const res = await agentApi.send(this.sessionId, content, true)
				this.messages.push(res.user_message || { role: 'user', content, created_at: new Date().toISOString() })
				if (res.assistant_message) {
					this.messages.push(res.assistant_message)
					this.sending = false
				}
				await this.loadSessions()
				this.scroll()
				if (this.sending) this.startPolling()
			} catch (e) {
				this.sending = false
				this.messages.push({ role: 'assistant', content: `暂时无法提交问题：${e.message}`, created_at: new Date().toISOString() })
				this.scroll()
			}
		},
		startPolling() {
			this.stopPolling()
			this.pollTimer = setInterval(() => {
				this.refreshActiveSession()
			}, 2500)
		},
		stopPolling() {
			if (this.pollTimer) {
				clearInterval(this.pollTimer)
				this.pollTimer = null
			}
		},
		async refreshActiveSession() {
			if (!this.sessionId) return
			try {
				const session = await agentApi.session(this.sessionId)
				const oldLength = this.messages.length
				this.messages = session.messages || []
				this.sending = this.hasPendingAnswer()
				await this.loadSessions()
				if (!this.sending) this.stopPolling()
				if (this.messages.length !== oldLength) this.scroll()
			} catch (e) {
				this.stopPolling()
				this.sending = false
			}
		},
		hasPendingAnswer() {
			const last = this.messages[this.messages.length - 1]
			return Boolean(last && last.role === 'user')
		},
		scroll() {
			this.$nextTick(() => {
				this.scrollTarget = this.sending ? 'pending-answer' : `msg-${this.messages.length - 1}`
			})
		},
		sessionTitle(item) {
			return cleanAssistantText(item.title || item.last_message || `会话 ${item.id}`).slice(0, 16)
		},
		previewText(value) {
			return cleanAssistantText(value || '还没有对话内容').slice(0, 28)
		},
		timeText(value) {
			return formatMessageTime(value)
		},
		messageTime(msg) {
			return formatMessageTime(msg.created_at, true)
		},
		formatMessage(content = '') {
			const lines = cleanAssistantText(content).split('\n')
			const blocks = []
			let list = []
			const flushList = () => {
				if (list.length) {
					blocks.push({ type: 'list', items: list })
					list = []
				}
			}
			lines.forEach(raw => {
				const line = raw.trim()
				if (!line) {
					flushList()
					return
				}
				const listMatch = line.match(/^(\d+[.)]|[-])\s*(.+)$/)
				if (listMatch) {
					list.push(listMatch[2])
					return
				}
				flushList()
				if (/^(小提醒|建议|注意|原因|步骤|总结|风险|处理方式)[:：]/.test(line)) {
					blocks.push({ type: 'heading', text: line })
				} else {
					blocks.push({ type: 'paragraph', text: line })
				}
			})
			flushList()
			return blocks.length ? blocks : [{ type: 'paragraph', text: content }]
		}
	}
}
</script>

<style scoped lang="scss">
.chat-page{display:grid;height:calc(100vh - var(--header-height));height:calc(100dvh - var(--header-height));min-height:0;overflow:hidden;grid-template-columns:280px minmax(0,1fr);background:#fff}.chat-sidebar{display:flex;min-height:0;overflow:hidden;flex-direction:column;padding:20px;border-right:1px solid var(--color-border);background:#fffaf6}.assistant-brand{display:flex;align-items:center;gap:12px;font-size:15px;font-weight:800}.assistant-brand text{display:block}.assistant-brand text:last-child{margin-top:3px;color:var(--color-text-secondary);font-size:10px;font-weight:400}.ai-logo{display:flex;width:42px;height:42px;align-items:center;justify-content:center;border-radius:14px;background:linear-gradient(145deg,#ff9e4d,#ff6d14);color:#fff;font-weight:900}.new-chat{height:38px;margin:20px 0 16px;padding:0;border:1px solid var(--color-primary);border-radius:19px;background:#fff;color:var(--color-primary);font-size:12px;line-height:38px}.history-block{display:flex;min-height:0;flex:1 1 auto;flex-direction:column;margin-bottom:1.4em}.history-title{margin-bottom:8px;color:var(--color-text-secondary);font-size:10px;font-weight:800}.history-list{height:100%;min-height:0}.history-empty{padding:12px;border:1px dashed var(--color-border);border-radius:8px;background:#fff;color:var(--color-text-secondary);font-size:11px;line-height:1.6}.history-item{margin-bottom:8px;padding:10px;border:1px solid transparent;border-radius:8px;background:#fff;cursor:pointer}.history-item.active{border-color:var(--color-primary);box-shadow:0 6px 16px rgba(255,109,20,.12)}.history-row{display:flex;align-items:center;justify-content:space-between;gap:8px}.history-name{overflow:hidden;min-width:0;font-size:13px;font-weight:800;text-overflow:ellipsis;white-space:nowrap}.delete-chat{display:flex;width:24px;height:24px;flex:none;align-items:center;justify-content:center;margin:0;padding:0;border:1px solid #ffd7cf;border-radius:12px;background:#fff7f4;color:#c34838;font-size:10px;line-height:22px}.history-preview{display:block;overflow:hidden;margin-top:6px;color:var(--color-text-secondary);font-size:11px;line-height:1.4;text-overflow:ellipsis;white-space:nowrap}.history-meta{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-top:6px;color:var(--color-text-secondary);font-size:10px}.pending-dot{color:#4b8b66}.pet-context{display:flex;flex:none;flex-direction:column;gap:8px;padding:14px;border:1px solid #ffd4b5;border-radius:8px;background:#fff7f1;font-size:12px}.side-label{color:var(--color-primary);font-size:10px;font-weight:700}.pet-context .muted{font-size:10px;line-height:1.6}.chat-main{display:flex;height:100%;min-width:0;min-height:0;overflow:hidden;flex-direction:column}.chat-header{display:flex;height:72px;flex:none;align-items:center;justify-content:space-between;padding:0 28px;border-bottom:1px solid var(--color-border)}.chat-title,.chat-sub{display:block}.chat-title{font-size:18px;font-weight:800}.chat-sub{margin-top:4px;color:var(--color-text-secondary);font-size:11px}.shield{color:#4b8b66;font-size:11px}.mobile-history{display:none}.messages{height:0;min-height:0;flex:1 1 0;overflow:hidden;padding:24px 5%}.welcome{display:flex;max-width:640px;flex-direction:column;align-items:center;margin:5vh auto 30px;text-align:center}.welcome-icon{display:flex;width:66px;height:66px;align-items:center;justify-content:center;border-radius:20px;background:var(--color-primary-soft);color:var(--color-primary);font-size:22px;font-weight:900}.welcome-title{margin-top:16px;font-size:23px;font-weight:800}.welcome-sub{max-width:500px;margin-top:10px;color:var(--color-text-secondary);font-size:13px;line-height:1.7}.suggestions{display:flex;flex-wrap:wrap;justify-content:center;gap:9px;margin-top:20px}.suggestions view{padding:9px 15px;border:1px solid var(--color-border);border-radius:18px;background:#fff;font-size:11px}.message-row{display:flex;max-width:780px;gap:10px;margin:18px auto}.message-row.user{flex-direction:row-reverse}.message-avatar{display:flex;width:34px;height:34px;flex:none;align-items:center;justify-content:center;border-radius:11px;background:#fff0e4;color:var(--color-primary);font-size:11px;font-weight:800}.message-wrap{display:flex;max-width:75%;min-width:0;flex-direction:column}.user .message-wrap{align-items:flex-end}.message-time{margin:0 2px 5px;color:var(--color-text-secondary);font-size:10px}.bubble{max-width:100%;padding:14px 16px;border-radius:5px 16px 16px 16px;background:#f8f3ee;color:var(--color-text);font-size:13px;line-height:1.75}.user .bubble{border-radius:16px 5px 16px 16px;background:var(--color-primary);color:#fff}.message-heading{margin:4px 0 8px;font-size:14px;font-weight:800}.message-paragraph{margin:6px 0}.message-list{margin:8px 0}.message-list-item{display:flex;gap:8px;margin:6px 0}.list-marker{flex:none;color:var(--color-primary);font-weight:900}.user .list-marker{color:#fff}.risk{margin-top:12px;padding:10px;border-radius:8px;background:#fff0e7;color:#a64f1c;font-size:11px;line-height:1.6}.typing{color:var(--color-text-secondary)}.composer{display:flex;flex:none;align-items:flex-end;gap:10px;margin:16px 5% 24px;padding:10px 10px 10px 17px;border:1px solid var(--color-border);border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(70,45,24,.08)}.composer textarea{flex:1;min-height:26px;max-height:100px;padding:5px 0;font-size:13px}.composer button{display:flex;min-width:54px;height:38px;align-items:center;justify-content:center;margin:0;border-radius:12px;background:var(--color-primary);color:#fff;font-size:13px;line-height:38px}.composer button[disabled]{opacity:.55}
@media(max-width:900px){.chat-page{height:calc(100vh - var(--bottom-nav-height) - env(safe-area-inset-bottom));height:calc(100dvh - var(--bottom-nav-height) - env(safe-area-inset-bottom));grid-template-columns:1fr}.chat-sidebar{display:none}.chat-header{height:64px;padding:0 16px}.chat-title{font-size:16px}.chat-sub{font-size:9px}.shield{display:none}.mobile-history{display:block;flex:none;min-height:44px;padding:8px 12px;border-bottom:1px solid var(--color-border);white-space:nowrap}.mobile-history-empty,.mobile-history-item{display:inline-flex;align-items:center;gap:6px;height:28px;margin-right:8px;padding:0 8px 0 12px;border:1px solid var(--color-border);border-radius:14px;background:#fff;color:var(--color-text-secondary);font-size:11px}.mobile-history-item.active{border-color:var(--color-primary);color:var(--color-primary);font-weight:800}.mobile-delete-chat{display:flex;width:18px;height:18px;align-items:center;justify-content:center;margin:0;padding:0;border-radius:9px;background:#fff1ee;color:#c34838;font-size:14px;line-height:18px}.messages{padding:15px 14px 95px}.welcome{margin-top:3vh}.welcome-icon{width:58px;height:58px;font-size:18px}.welcome-title{font-size:20px}.welcome-sub{font-size:11px}.suggestions{flex-direction:column}.message-row{margin:15px auto}.message-wrap{max-width:82%}.bubble{font-size:12px}.composer{position:fixed;right:12px;bottom:calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + 8px);left:12px;z-index:40;margin:0}}
</style>
