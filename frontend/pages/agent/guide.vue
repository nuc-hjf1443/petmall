<template>
	<AppShell active="guide">
		<view class="guide-page">
			<view class="guide-sidebar">
				<view class="assistant-brand">
					<view class="guide-logo">荐</view>
					<view>
						<text>AI 智能导购</text>
						<text>真实商品、按需推荐</text>
					</view>
				</view>
				<button class="new-chat" @click="reset">＋ 新建导购</button>
				<view class="history-card">
					<view class="panel-heading">
						<text>历史对话</text>
						<text class="panel-action" @click="loadHistory">查看全部</text>
					</view>
					<view v-if="loadingHistory" class="history-empty">正在加载...</view>
					<view v-else-if="!historySessions.length" class="history-empty">暂无历史导购</view>
					<view v-else class="history-list">
						<view
							v-for="item in historySessions"
							:key="item.id"
							class="history-item"
							:class="{ active: item.id === sessionId }"
							@click="openHistory(item)"
						>
							<text class="history-clock">○</text>
							<text class="history-title">{{ historyTitle(item) }}</text>
							<text class="history-time">{{ formatTime(item.latest_message_at || item.updated_at) }}</text>
							<button class="history-delete" @click.stop="deleteHistory(item)">删除</button>
						</view>
					</view>
				</view>
			</view>

			<view class="guide-main">
				<view class="guide-header">
					<view>
						<text class="guide-title">今天想买点什么？</text>
						<text class="guide-sub">描述宠物类型、年龄、需求和预算，我会帮你挑选合适商品</text>
					</view>
					<text class="shield">▣ 真实商品推荐</text>
				</view>
				<scroll-view class="messages" scroll-y :scroll-into-view="scrollTarget">
					<view v-if="!messages.length" class="welcome">
						<view class="welcome-icon">荐</view>
						<text class="welcome-title">你好，我是导购助手</text>
						<text class="welcome-sub">我会基于商城在售商品生成推荐，并说明推荐理由和注意事项。</text>
						<view class="suggestions">
							<view v-for="item in suggestions" :key="item" @click="ask(item)">{{ item }}</view>
						</view>
					</view>
					<view v-for="(msg,index) in messages" :id="`guide-msg-${index}`" :key="index" class="message-block">
						<view class="message-row" :class="msg.role">
							<view class="message-avatar">{{ msg.role === 'user' ? '我' : '荐' }}</view>
							<view class="bubble"><text>{{ displayMessageContent(msg) }}</text></view>
						</view>
						<view v-if="messageRecommendations(msg).length" class="recommendations message-recommendations">
							<text class="recommend-intro">下面是根据这次需求筛出的真实在售商品，价格、库存和规格以卡片为准。</text>
							<view class="product-grid">
								<view v-for="item in messageRecommendations(msg)" :key="item.product_id" class="product-card">
									<image class="product-image" :src="productImage(item.product)" mode="aspectFill" />
									<text class="product-title">{{ item.product.title }}</text>
									<view class="product-tags">
										<text v-for="tag in recommendTags(item)" :key="tag">{{ tag }}</text>
									</view>
									<text class="product-price">￥{{ formatPrice(item.product.price) }}</text>
									<text class="product-stock">{{ productStockText(item.product) }}</text>
									<text class="product-reason">推荐理由：{{ item.reason }}</text>
									<text v-if="item.caution" class="product-caution">{{ item.caution }}</text>
									<button class="detail-btn" @click="detail(item.product_id)">查看详情</button>
								</view>
							</view>
							<button
								v-if="isLatestRecommendationMessage(index)"
								class="refine-btn"
								:disabled="sending"
								@click="refineRecommendation"
							>不满意？补充要求后重新推荐</button>
						</view>
					</view>
					<view v-if="nextQuestions.length" class="question-panel">
						<view v-for="question in nextQuestions" :key="question.key" class="question-item">
							<text class="question-title">{{ question.question }}</text>
							<view class="question-options">
								<button
									v-for="option in question.options"
									:key="option.value || option.label"
									:disabled="sending"
									@click="answerGuideOption(option)"
								>{{ option.label }}</button>
							</view>
						</view>
					</view>
					<view v-if="sending" class="message-row assistant">
						<view class="message-avatar">荐</view>
						<view class="bubble typing">正在匹配真实商品...</view>
					</view>
				</scroll-view>
				<view class="composer">
					<textarea id="guide-input" v-model="input" auto-height maxlength="1000" placeholder="例如：3 岁柯基，需要低敏狗粮，预算 300 元" @confirm="send" />
					<button :disabled="sending" @click="send">➤</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { aiApi, assetUrl } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			sessionId: null,
			input: '',
			messages: [],
			recommendations: [],
			guideState: null,
			nextQuestions: [],
			requiresUserConfirmation: false,
			historySessions: [],
			loadingHistory: false,
			sending: false,
			refineMode: false,
			scrollTarget: '',
			suggestions: [
				'3 岁柯基，需要低敏狗粮，预算 300 元',
				'幼猫刚到家，需要准备哪些用品？',
				'狗狗爱啃家具，有什么玩具推荐？'
			]
		}
	},
	mounted() {
		this.loadHistory()
	},
	methods: {
		reset() {
			this.sessionId = null
			this.input = ''
			this.messages = []
			this.recommendations = []
			this.guideState = null
			this.nextQuestions = []
			this.requiresUserConfirmation = false
			this.refineMode = false
		},
		answerGuideOption(option) {
			this.input = option.value || option.label || ''
			this.send()
		},
		ask(text) {
			this.input = text
			this.send()
		},
		focusInput() {
			this.input = this.input || ''
		},
		async send() {
			const content = this.input.trim()
			if (!content || this.sending) return
			if (!uni.getStorageSync('access_token')) {
				return uni.navigateTo({ url: '/pages/auth/login' })
			}
			this.input = ''
			this.messages.push({ role: 'user', content })
			this.nextQuestions = []
			this.sending = true
			this.scroll()
			try {
				if (!this.sessionId) {
					const payload = { title: this.makeSessionTitle(content) }
					this.sessionId = (await aiApi.createGuideSession(payload)).id
				}
				const response = this.refineMode
					? await aiApi.refineGuideRecommendation(this.sessionId, { content, limit: 5 })
					: await aiApi.sendGuideMessage(this.sessionId, { content, limit: 5 })
				this.refineMode = false
				this.recommendations = response.recommendations || []
				this.messages.push({
					...response.assistant_message,
					recommendations: this.recommendations
				})
				this.guideState = response.guide_state || null
				this.nextQuestions = response.next_questions || []
				this.requiresUserConfirmation = !!response.requires_user_confirmation
				this.loadHistory()
			} catch (error) {
				this.messages.push({ role: 'assistant', content: `暂时无法生成推荐：${error.message}` })
			} finally {
				this.sending = false
				this.scroll()
			}
		},
		async loadHistory() {
			if (!uni.getStorageSync('access_token')) return
			this.loadingHistory = true
			try {
				const response = await aiApi.sessions({ agent_type: 'guide', page: 1, page_size: 5 })
				this.historySessions = response.items || []
			} catch (error) {
				this.historySessions = []
			} finally {
				this.loadingHistory = false
			}
		},
		async openHistory(item) {
			if (this.sending) return
			this.refineMode = false
			try {
				const timeline = await aiApi.guideTimeline(item.id)
				this.sessionId = item.id
				this.messages = (timeline.messages || []).slice().sort((a, b) => a.id - b.id)
				this.guideState = null
				this.nextQuestions = []
				this.requiresUserConfirmation = false
				this.scroll()
			} catch (error) {
				uni.showToast({ title: '历史会话加载失败', icon: 'none' })
			}
		},
		async deleteHistory(item) {
			if (this.sending) return
			uni.showModal({
				title: '删除历史对话',
				content: '删除后不可恢复，确认删除这条导购对话吗？',
				success: async result => {
					if (!result.confirm) return
					try {
						await aiApi.deleteSession(item.id, { agent_type: 'guide' })
						this.historySessions = this.historySessions.filter(session => session.id !== item.id)
						if (this.sessionId === item.id) {
							this.reset()
						}
						uni.showToast({ title: '已删除', icon: 'success' })
						this.loadHistory()
					} catch (error) {
						uni.showToast({ title: error.message || '删除失败', icon: 'none' })
					}
				}
			})
		},
		scroll() {
			this.$nextTick(() => {
				this.scrollTarget = `guide-msg-${this.messages.length - 1}`
			})
		},
		displayMessageContent(message) {
			if (message.role !== 'user') return message.content
			const match = String(message.content || '').match(/^用户问题：(.+?)(?:\n左侧需求摘要：|$)/s)
			return match ? match[1].trim() : message.content
		},
		messageRecommendations(message) {
			return Array.isArray(message.recommendations) ? message.recommendations : []
		},
		isLatestRecommendationMessage(index) {
			return !this.messages.slice(index + 1).some(message => this.messageRecommendations(message).length)
		},
		refineRecommendation() {
			this.refineMode = true
			this.input = '不满意当前推荐，我希望'
			this.$nextTick(() => this.focusInput())
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/mall/detail?id=${id}` })
		},
		makeSessionTitle(content) {
			return content.length > 18 ? `${content.slice(0, 18)}...` : content
		},
		historyTitle(item) {
			return item.title || item.latest_message_content || '未命名导购'
		},
		formatTime(value) {
			if (!value) return ''
			const date = new Date(value)
			if (Number.isNaN(date.getTime())) return ''
			const now = new Date()
			const sameDay = date.toDateString() === now.toDateString()
			const yesterday = new Date(now)
			yesterday.setDate(now.getDate() - 1)
			const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
			if (sameDay) return `今天 ${time}`
			if (date.toDateString() === yesterday.toDateString()) return `昨天 ${time}`
			return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${time}`
		},
		formatPrice(price) {
			const value = Number(price || 0) / 100
			return Number.isInteger(value) ? String(value) : value.toFixed(2)
		},
		productStockText(product = {}) {
			const stock = Number(product.stock || 0)
			return stock > 0 ? `库存充足 · ${stock} 件` : '库存以详情页为准'
		},
		productImage(product = {}) {
			const primary = (product.images || []).find(image => image.is_primary)
			const first = (product.images || [])[0]
			return assetUrl(product.cover_image || (primary && primary.image_url) || (first && first.image_url) || '/static/logo.png')
		},
		recommendTags(item) {
			const product = item.product || {}
			const tags = []
			if (product.applicable_pet_type === 'cat') tags.push('猫咪适用')
			if (product.applicable_pet_type === 'dog') tags.push('狗狗适用')
			if (item.reason && item.reason.includes('低敏')) tags.push('低敏优先')
			if (item.reason && item.reason.includes('预算')) tags.push('预算友好')
			if (product.stock > 0) tags.push('有库存')
			if (!tags.length) tags.push('真实在售')
			return tags.slice(0, 3)
		}
	}
}
</script>

<style scoped lang="scss">
.guide-page {
	display: grid;
	height: calc(100vh - var(--header-height));
	height: calc(100dvh - var(--header-height));
	min-height: 0;
	overflow: hidden;
	grid-template-columns: 280px minmax(0, 1fr);
	background: #fff;
}
.guide-sidebar {
	display: flex;
	width: 280px;
	min-width: 280px;
	max-width: 280px;
	min-height: 0;
	overflow-y: auto;
	overflow-x: hidden;
	flex-direction: column;
	padding: 20px;
	border-right: 1px solid var(--color-border);
	background: #fffaf6;
}
.assistant-brand {
	display: flex;
	align-items: center;
	gap: 12px;
	font-size: 15px;
	font-weight: 800;
}
.assistant-brand text { display: block; }
.assistant-brand text:last-child {
	margin-top: 4px;
	color: var(--color-text-secondary);
	font-size: 10px;
	font-weight: 400;
}
.guide-logo,
.message-avatar {
	display: flex;
	align-items: center;
	justify-content: center;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-weight: 900;
}
.guide-logo {
	width: 42px;
	height: 42px;
	border-radius: 14px;
	font-size: 20px;
}
.new-chat {
	display: flex;
	height: 38px;
	min-height: 38px;
	align-items: center;
	justify-content: center;
	margin: 20px 0 16px;
	padding: 0;
	border: 1px solid var(--color-primary);
	border-radius: 19px;
	background: #fff;
	color: var(--color-primary);
	font-size: 12px;
	line-height: 1;
}
.history-card,
.product-card {
	border: 1px solid var(--color-border);
	background: var(--color-surface);
	box-shadow: var(--shadow-card);
}
.history-card {
	width: 100%;
	padding: 14px;
	border-radius: 8px;
}
.history-card {
	display: flex;
	flex: none;
	flex-direction: column;
	margin-top: 12px;
	overflow: visible;
}
.panel-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	margin-bottom: 10px;
	font-size: 12px;
	font-weight: 800;
}
.panel-action {
	color: var(--color-primary);
	font-size: 10px;
	font-weight: 600;
}
.history-empty {
	padding: 12px;
	border: 1px dashed var(--color-border);
	border-radius: 8px;
	background: #fff;
	color: var(--color-text-secondary);
	text-align: left;
	font-size: 11px;
	line-height: 1.6;
}
.history-list {
	overflow: visible;
}
.history-item {
	display: grid;
	grid-template-columns: 14px minmax(0, 1fr) auto;
	gap: 6px;
	align-items: center;
	margin-top: 8px;
	padding: 9px;
	border-radius: 8px;
	background: #fffaf6;
	font-size: 10px;
	cursor: pointer;
}
.history-item.active,
.history-item:hover { background: var(--color-primary-soft); }
.history-clock,
.history-time { color: var(--color-text-secondary); }
.history-delete {
	grid-row: 1 / span 2;
	grid-column: 3;
	width: 38px;
	height: 24px;
	margin: 0;
	padding: 0;
	border: 1px solid #ffd7cf;
	border-radius: 12px;
	background: #fff7f4;
	color: #c34838;
	font-size: 10px;
	line-height: 22px;
}
.history-title {
	overflow: hidden;
	color: var(--color-text);
	text-overflow: ellipsis;
	white-space: nowrap;
}
.history-time {
	grid-column: 2;
	text-align: left;
}
.guide-main {
	display: flex;
	height: 100%;
	min-width: 0;
	min-height: 0;
	overflow: hidden;
	flex-direction: column;
}
.guide-header {
	display: flex;
	height: 75px;
	flex: none;
	align-items: center;
	justify-content: space-between;
	padding: 0 30px;
	border-bottom: 1px solid var(--color-border);
}
.guide-title,
.guide-sub { display: block; }
.guide-title {
	font-size: 18px;
	font-weight: 800;
}
.guide-sub {
	margin-top: 4px;
	color: var(--color-text-secondary);
	font-size: 11px;
}
.shield {
	color: var(--color-success);
	font-size: 11px;
}
.messages {
	height: 0;
	min-height: 0;
	flex: 1 1 0;
	overflow: hidden;
	padding: 28px 5%;
}
.welcome {
	display: flex;
	max-width: 650px;
	flex-direction: column;
	align-items: center;
	margin: 4vh auto 30px;
	text-align: center;
}
.welcome-icon {
	display: flex;
	width: 70px;
	height: 70px;
	align-items: center;
	justify-content: center;
	border-radius: 23px;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 30px;
	font-weight: 900;
}
.welcome-title {
	margin-top: 17px;
	font-size: 24px;
	font-weight: 800;
}
.welcome-sub {
	max-width: 500px;
	margin-top: 10px;
	color: var(--color-text-secondary);
	font-size: 13px;
	line-height: 1.7;
}
.suggestions {
	display: flex;
	flex-wrap: wrap;
	justify-content: center;
	gap: 9px;
	margin-top: 20px;
}
.suggestions view {
	padding: 9px 15px;
	border: 1px solid var(--color-border);
	border-radius: 18px;
	background: #fff;
	font-size: 11px;
}
.message-block {
	max-width: 980px;
	margin: 0 auto;
}
.message-row {
	display: flex;
	max-width: 880px;
	gap: 10px;
	margin: 18px auto;
}
.message-row.user { flex-direction: row-reverse; }
.message-avatar {
	width: 34px;
	height: 34px;
	flex: none;
	border-radius: 11px;
	font-size: 11px;
}
.bubble {
	max-width: 75%;
	padding: 13px 16px;
	border-radius: 5px 16px 16px 16px;
	background: #f8f3ee;
	font-size: 13px;
	line-height: 1.8;
}
.user .bubble {
	border-radius: 16px 5px 16px 16px;
	background: var(--color-primary);
	color: #fff;
}
.typing { color: var(--color-text-secondary); }
.question-panel {
	max-width: 880px;
	margin: 8px auto 20px;
	padding-left: 44px;
}
.question-item {
	margin-top: 10px;
	padding: 14px;
	border: 1px solid var(--color-border);
	border-radius: 8px;
	background: #fffaf6;
}
.question-title {
	display: block;
	color: var(--color-text);
	font-size: 13px;
	font-weight: 700;
	line-height: 1.6;
}
.question-options {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-top: 10px;
}
.question-options button {
	height: 30px;
	margin: 0;
	padding: 0 13px;
	border: 1px solid var(--color-border);
	border-radius: 15px;
	background: #fff;
	color: var(--color-primary);
	font-size: 11px;
	line-height: 28px;
}
.recommendations {
	max-width: 980px;
	margin: 8px auto 24px;
}
.message-recommendations {
	margin-top: -4px;
	padding-left: 44px;
}
.recommend-intro {
	display: block;
	margin-bottom: 10px;
	color: var(--color-text);
	font-size: 13px;
	line-height: 1.7;
}
.product-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 14px;
}
.product-card {
	display: flex;
	min-width: 0;
	min-height: 318px;
	flex-direction: column;
	padding: 14px;
	border-radius: var(--radius-sm);
}
.product-image {
	display: block;
	width: 100%;
	height: 116px;
	overflow: hidden;
	border-radius: var(--radius-sm);
	background: #fffaf6;
	object-fit: cover;
}
.product-title {
	overflow: hidden;
	margin-top: 12px;
	color: var(--color-text);
	font-size: 14px;
	font-weight: 800;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.product-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-top: 8px;
}
.product-tags text {
	padding: 4px 7px;
	border-radius: 12px;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 10px;
}
.product-price {
	margin-top: 10px;
	color: var(--color-primary);
	font-size: 18px;
	font-weight: 900;
}
.product-stock {
	margin-top: 3px;
	color: var(--color-text-secondary);
	font-size: 10px;
}
.product-reason {
	display: -webkit-box;
	overflow: hidden;
	min-height: 42px;
	margin-top: 8px;
	color: var(--color-text-secondary);
	font-size: 11px;
	line-height: 1.55;
	-webkit-box-orient: vertical;
	-webkit-line-clamp: 2;
}
.product-caution {
	overflow: hidden;
	margin-top: 6px;
	color: var(--color-warning);
	font-size: 10px;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.detail-btn {
	height: 32px;
	margin: 12px 0 0;
	padding: 0;
	border: 1px solid var(--color-border);
	border-radius: 16px;
	background: #fff;
	color: var(--color-primary);
	font-size: 11px;
	line-height: 32px;
}
.refine-btn {
	width: auto;
	height: 34px;
	margin: 12px 0 0;
	padding: 0 16px;
	border: 1px solid var(--color-primary);
	border-radius: 17px;
	background: #fff;
	color: var(--color-primary);
	font-size: 12px;
	line-height: 32px;
}
.composer {
	display: flex;
	flex: none;
	align-items: flex-end;
	gap: 10px;
	margin: 16px 5% 24px;
	padding: 10px 10px 10px 17px;
	border: 1px solid var(--color-border);
	border-radius: 18px;
	background: #fff;
	box-shadow: var(--shadow-card);
}
.composer textarea {
	flex: 1;
	min-height: 26px;
	max-height: 100px;
	padding: 5px 0;
	font-size: 13px;
}
.composer button {
	display: flex;
	width: 38px;
	height: 38px;
	align-items: center;
	justify-content: center;
	margin: 0;
	border-radius: 12px;
	background: var(--color-primary);
	color: #fff;
	font-size: 15px;
	line-height: 38px;
}
@media(max-width:1100px) {
	.product-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media(max-width:900px) {
	.guide-page {
		height: calc(100vh - var(--bottom-nav-height) - env(safe-area-inset-bottom));
		height: calc(100dvh - var(--bottom-nav-height) - env(safe-area-inset-bottom));
		grid-template-columns: 1fr;
	}
	.guide-sidebar { display: none; }
	.guide-header {
		height: 64px;
		padding: 0 16px;
	}
	.guide-title { font-size: 16px; }
	.guide-sub { font-size: 9px; }
	.messages { padding: 15px 14px 95px; }
	.welcome { margin-top: 3vh; }
	.welcome-icon {
		width: 58px;
		height: 58px;
		font-size: 24px;
	}
	.welcome-title { font-size: 20px; }
	.welcome-sub { font-size: 11px; }
	.suggestions { flex-direction: column; }
	.message-row { margin: 15px auto; }
	.bubble {
		max-width: 82%;
		font-size: 12px;
	}
	.message-recommendations { padding-left: 0; }
	.product-grid { grid-template-columns: 1fr; }
	.product-card { min-height: auto; }
	.composer {
		position: fixed;
		right: 12px;
		bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + 8px);
		left: 12px;
		z-index: 40;
		margin: 0;
	}
}
</style>
