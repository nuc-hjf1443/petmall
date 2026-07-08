<template>
	<AppShell :active="active">
		<view class="chat-page">
			<view class="chat-sidebar">
				<view class="assistant-brand">
					<view class="ai-logo">{{ logo }}</view>
					<view>
						<text>{{ title }}</text>
						<text>{{ onlineText }} · {{ statusText }}</text>
					</view>
				</view>

				<view class="pet-context">
					<text class="side-label">常见问题</text>
					<view class="suggestion-list">
						<view v-for="item in quickQuestions" :key="item" @tap.stop="quickAsk(item)">{{ item }}</view>
					</view>
				</view>

				<view class="pet-context">
					<text class="side-label">服务范围</text>
					<text>{{ serviceScope }}</text>
				</view>
			</view>

			<view class="chat-main">
				<view class="chat-header">
					<view>
						<text class="chat-title">{{ title }}</text>
						<text class="chat-sub">{{ subtitle }}</text>
					</view>
					<text class="refresh" @tap="load">刷新</text>
				</view>

				<scroll-view class="messages" scroll-y :scroll-into-view="scrollTarget">
					<view v-if="!conversation.messages?.length && !loading" class="welcome">
						<view class="welcome-icon">🐾</view>
						<text class="welcome-title">欢迎来到{{ title }}</text>
						<text class="welcome-sub">{{ emptyText }}</text>
						<view class="suggestions">
							<view v-for="item in quickQuestions.slice(0, 4)" :key="item" @tap.stop="quickAsk(item)">{{ item }}</view>
						</view>
					</view>

					<view v-if="loading" class="welcome">
						<text class="welcome-sub">正在加载对话...</text>
					</view>

					<view
						v-for="(message, index) in conversation.messages"
						:id="`msg-${index}`"
						:key="message.id"
						class="message-row"
						:class="message.sender_id === currentUserId ? 'user' : 'assistant'"
					>
						<view class="message-avatar">{{ message.sender_id === currentUserId ? '我' : peerAvatar }}</view>
						<view class="bubble">
							<text>{{ message.content }}</text>
							<text class="message-time">{{ formatTime(message.created_at) }}</text>
						</view>
					</view>

					<view v-if="sending" class="message-row assistant">
						<view class="message-avatar">{{ peerAvatar }}</view>
						<view class="bubble typing">正在发送...</view>
					</view>
				</scroll-view>

				<view class="composer">
					<textarea v-model="content" auto-height maxlength="1000" :placeholder="placeholder" @confirm="send" />
					<button :disabled="sending" @tap="send">发送</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from './AppShell.vue'
import { supportApi, userApi } from '../api'

export default {
	components: { AppShell },
	props: {
		active: { type: String, default: 'profile' },
		conversationId: { type: [Number, String], required: true },
		role: { type: String, default: 'user' },
		scene: { type: String, default: 'platform' }
	},
	data() {
		return {
			conversation: { messages: [] },
			currentUserId: null,
			content: '',
			loading: true,
			sending: false,
			scrollTarget: ''
		}
	},
	computed: {
		id() {
			return Number(this.conversationId)
		},
		effectiveScene() {
			return this.conversation.type || this.scene
		},
		logo() {
			if (this.effectiveScene === 'merchant') return '店'
			if (this.effectiveScene === 'adoption') return '领'
			return 'CS'
		},
		onlineText() {
			if (this.effectiveScene === 'merchant') return '商家客服在线'
			if (this.effectiveScene === 'adoption') return '领养沟通在线'
			return '平台客服在线'
		},
		title() {
			if (this.effectiveScene === 'merchant') return this.conversation.merchant_name || '商家客服'
			if (this.effectiveScene === 'adoption') return this.conversation.adoption_pet_name || '领养对话'
			return '平台客服'
		},
		statusText() {
			return this.conversation.status === 'resolved' ? '已处理' : '未处理'
		},
		subtitle() {
			if (this.effectiveScene === 'merchant') return '商家客服会话，可查看历史咨询'
			if (this.effectiveScene === 'adoption') return '领养双方沟通，审核仍由平台完成'
			return `当前状态：${this.statusText}`
		},
		serviceScope() {
			if (this.effectiveScene === 'merchant') return '商品规格、库存、发货、售后等问题可以在这里咨询商家。'
			if (this.effectiveScene === 'adoption') return '领养意向、宠物情况、线下沟通安排可以在这里交流。'
			return '订单、商品、领养、售后、投诉建议都可以在这里咨询。'
		},
		emptyText() {
			if (this.effectiveScene === 'merchant') return '你可以咨询商品规格、库存、发货和售后问题。'
			if (this.effectiveScene === 'adoption') return '你可以和发布人沟通宠物情况、领养条件和见面安排。'
			return '你可以咨询订单、商品、领养、售后等问题。'
		},
		placeholder() {
			if (this.effectiveScene === 'merchant') return '输入要咨询商家的问题...'
			if (this.effectiveScene === 'adoption') return '输入领养沟通内容...'
			return '输入你的问题...'
		},
		peerAvatar() {
			if (this.effectiveScene === 'merchant') return '店'
			if (this.effectiveScene === 'adoption') return '领'
			return '客'
		},
		quickQuestions() {
			if (this.effectiveScene === 'merchant') return ['商品规格', '库存情况', '多久发货', '售后问题', '优惠咨询', '联系人工']
			if (this.effectiveScene === 'adoption') return ['宠物性格', '健康情况', '领养条件', '见面安排', '申请进度', '联系发布人']
			return ['订单问题', '领养咨询', '退款售后', '投诉建议', '商品咨询', '联系人工']
		}
	},
	watch: {
		conversationId() {
			this.load()
		}
	},
	mounted() {
		this.load()
		this.loadMe()
	},
	methods: {
		async loadMe() {
			try {
				const me = await userApi.me()
				this.currentUserId = me.id
			} catch (error) {}
		},
		async load() {
			if (!this.id) return
			this.loading = true
			try {
				this.conversation = await supportApi.detail(this.id)
				this.scroll()
			} finally {
				this.loading = false
			}
		},
		quickAsk(text) {
			if (this.sending) return
			this.content = text
			this.send()
		},
		formatTime(value) {
			return value ? String(value).replace('T', ' ').slice(0, 16) : ''
		},
		async send() {
			const content = this.content.trim()
			if (!content || this.sending || !this.id) return
			this.content = ''
			this.sending = true
			try {
				const payload = { content }
				if (this.role === 'merchant') this.conversation = await supportApi.merchantSend(this.id, payload)
				else if (this.role === 'admin') this.conversation = await supportApi.adminSend(this.id, payload)
				else this.conversation = await supportApi.send(this.id, payload)
			} finally {
				this.sending = false
				this.scroll()
			}
		},
		scroll() {
			this.$nextTick(() => {
				this.scrollTarget = `msg-${Math.max((this.conversation.messages || []).length - 1, 0)}`
			})
		}
	}
}
</script>

<style scoped lang="scss">
.chat-page{display:grid;height:calc(100vh - var(--header-height));height:calc(100dvh - var(--header-height));min-height:0;overflow:hidden;grid-template-columns:290px minmax(0,1fr);background:#fff}.chat-sidebar{min-height:0;overflow:hidden;padding:24px;border-right:1px solid var(--color-border);background:#fffaf6}.assistant-brand{display:flex;align-items:center;gap:12px;font-size:15px;font-weight:800}.assistant-brand text{display:block}.assistant-brand text:last-child{margin-top:4px;color:var(--color-text-secondary);font-size:10px;font-weight:400}.ai-logo{display:flex;width:42px;height:42px;align-items:center;justify-content:center;border-radius:14px;background:linear-gradient(145deg,#ff9e4d,#ff6d14);color:#fff;font-weight:900}.pet-context{display:flex;flex-direction:column;gap:10px;margin-top:18px;padding:16px;border-radius:14px;background:#fff;font-size:13px;line-height:1.7;box-shadow:0 8px 22px rgba(255,107,26,.06)}.side-label{color:var(--color-primary);font-size:10px;font-weight:700}.suggestion-list{display:grid;grid-template-columns:1fr 1fr;gap:8px}.suggestion-list view{padding:8px 10px;border:1px solid var(--color-border);border-radius:14px;background:#fff;color:var(--color-text);font-size:11px;text-align:center;cursor:pointer;user-select:none}.suggestion-list view:active,.suggestions view:active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary)}.chat-main{display:flex;height:100%;min-width:0;min-height:0;overflow:hidden;flex-direction:column}.chat-header{display:flex;height:75px;flex:none;align-items:center;justify-content:space-between;padding:0 30px;border-bottom:1px solid var(--color-border)}.chat-title,.chat-sub{display:block}.chat-title{font-size:18px;font-weight:800}.chat-sub{margin-top:4px;color:var(--color-text-secondary);font-size:11px}.refresh{color:#4b8b66;font-size:12px;cursor:pointer}.messages{height:0;min-height:0;flex:1 1 0;overflow:hidden;padding:28px 5%}.welcome{display:flex;max-width:650px;flex-direction:column;align-items:center;margin:4vh auto 30px;text-align:center}.welcome-icon{display:flex;width:70px;height:70px;align-items:center;justify-content:center;border-radius:23px;background:var(--color-primary-soft);font-size:38px}.welcome-title{margin-top:17px;font-size:24px;font-weight:800}.welcome-sub{max-width:500px;margin-top:10px;color:var(--color-text-secondary);font-size:13px;line-height:1.7}.suggestions{display:flex;flex-wrap:wrap;justify-content:center;gap:9px;margin-top:20px}.suggestions view{padding:9px 15px;border:1px solid var(--color-border);border-radius:18px;background:#fff;font-size:11px;cursor:pointer;user-select:none}.message-row{display:flex;max-width:780px;gap:10px;margin:20px auto}.message-row.user{flex-direction:row-reverse}.message-avatar{display:flex;width:34px;height:34px;flex:none;align-items:center;justify-content:center;border-radius:11px;background:#fff0e4;color:var(--color-primary);font-size:11px;font-weight:800}.bubble{max-width:75%;padding:13px 16px;border-radius:5px 16px 16px 16px;background:#f8f3ee;font-size:13px;line-height:1.8}.user .bubble{border-radius:16px 5px 16px 16px;background:var(--color-primary);color:#fff}.message-time{display:block;margin-top:6px;opacity:.7;font-size:10px}.typing{color:var(--color-text-secondary)}.composer{display:flex;flex:none;align-items:flex-end;gap:10px;margin:16px 5% 24px;padding:10px 10px 10px 17px;border:1px solid var(--color-border);border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(70,45,24,.08)}.composer textarea{flex:1;min-height:26px;max-height:100px;padding:5px 0;font-size:13px}.composer button{display:flex;width:54px;height:38px;align-items:center;justify-content:center;margin:0;border-radius:12px;background:var(--color-primary);color:#fff;font-size:13px;line-height:38px}
@media(max-width:900px){.chat-page{height:calc(100vh - var(--bottom-nav-height) - env(safe-area-inset-bottom));height:calc(100dvh - var(--bottom-nav-height) - env(safe-area-inset-bottom));grid-template-columns:1fr}.chat-sidebar{display:none}.chat-header{height:64px;padding:0 16px}.messages{padding:15px 14px 95px}.bubble{max-width:82%;font-size:12px}.composer{position:fixed;right:12px;bottom:calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + 8px);left:12px;z-index:40;margin:0}}
</style>
