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
				<view class="summary-card">
					<view class="panel-heading">
						<text>我的需求摘要</text>
						<text class="panel-action" @click="toggleSummaryEdit">{{ summaryEditing ? '完成' : '修改' }}</text>
					</view>
					<view v-for="item in summaryRows" :key="item.key" class="summary-row">
						<text class="summary-icon">{{ item.icon }}</text>
						<text class="summary-label">{{ item.label }}</text>
						<input
							v-if="summaryEditing"
							v-model="demandSummary[item.key]"
							class="summary-input"
							:placeholder="item.placeholder"
							:maxlength="item.maxlength"
							:focus="summaryFocusKey === item.key"
						/>
						<text v-else class="summary-value">{{ summaryValue(item.key) }}</text>
					</view>
					<view v-if="showMoreDemand" class="more-demand-panel">
						<textarea
							v-model="demandSummary.other"
							:focus="moreDemandFocus"
							auto-height
							maxlength="160"
							placeholder="例如：肠胃敏感、希望小颗粒、不要鸡肉、适合出门携带"
						/>
					</view>
					<button class="more-demand" @click="toggleMoreDemand">
						{{ showMoreDemand ? '收起补充需求' : '＋ 补充更多需求' }}
					</button>
				</view>
				<view class="history-card">
					<view class="panel-heading">
						<text>历史对话</text>
						<text class="panel-action" @click="loadHistory">查看全部</text>
					</view>
					<view v-if="loadingHistory" class="history-empty">正在加载...</view>
					<view v-else-if="!historySessions.length" class="history-empty">暂无历史导购</view>
					<view v-else>
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
					<view v-for="(msg,index) in messages" :id="`guide-msg-${index}`" :key="index" class="message-row" :class="msg.role">
						<view class="message-avatar">{{ msg.role === 'user' ? '我' : '荐' }}</view>
						<view class="bubble"><text>{{ displayMessageContent(msg) }}</text></view>
					</view>
					<view v-if="recommendations.length" class="recommendations">
						<text class="recommend-intro">根据你的需求，我筛选了以下真实在售商品，兼顾适配度、价格和库存。</text>
						<view class="product-grid">
							<view v-for="item in recommendations" :key="item.product_id" class="product-card">
								<image class="product-image" :src="productImage(item.product)" mode="aspectFit" />
								<text class="product-title">{{ item.product.title }}</text>
								<view class="product-tags">
									<text v-for="tag in recommendTags(item)" :key="tag">{{ tag }}</text>
								</view>
								<text class="product-price">￥{{ formatPrice(item.product.price) }}</text>
								<text class="product-reason">推荐理由：{{ item.reason }}</text>
								<text v-if="item.caution" class="product-caution">{{ item.caution }}</text>
								<button class="detail-btn" @click="detail(item.product_id)">查看详情</button>
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
			historySessions: [],
			loadingHistory: false,
			summaryEditing: false,
			summaryFocusKey: '',
			showMoreDemand: false,
			moreDemandFocus: false,
			sending: false,
			scrollTarget: '',
			demandSummary: {
				budget: '待补充',
				purpose: '待补充',
				preference: '待补充',
				brand: '品牌不限',
				other: '待补充'
			},
			summaryRows: [
				{ key: 'budget', label: '预算', icon: '¥', placeholder: '待补充', maxlength: 24 },
				{ key: 'purpose', label: '用途', icon: '用', placeholder: '待补充', maxlength: 32 },
				{ key: 'preference', label: '偏好', icon: '偏', placeholder: '待补充', maxlength: 48 },
				{ key: 'brand', label: '品牌', icon: '牌', placeholder: '品牌不限', maxlength: 32 },
				{ key: 'other', label: '其他', icon: '其', placeholder: '补充更多需求', maxlength: 80 }
			],
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
		emptySummary() {
			return {
				budget: '待补充',
				purpose: '待补充',
				preference: '待补充',
				brand: '品牌不限',
				other: '待补充'
			}
		},
		reset() {
			this.sessionId = null
			this.input = ''
			this.messages = []
			this.recommendations = []
			this.demandSummary = this.emptySummary()
			this.summaryEditing = false
			this.summaryFocusKey = ''
			this.showMoreDemand = false
			this.moreDemandFocus = false
		},
		ask(text) {
			this.input = text
			this.send()
		},
		focusInput() {
			this.input = this.input || ''
		},
		toggleSummaryEdit() {
			this.summaryEditing = !this.summaryEditing
			this.summaryFocusKey = ''
			if (this.summaryEditing) {
				this.$nextTick(() => {
					this.summaryFocusKey = 'budget'
				})
			}
		},
		toggleMoreDemand() {
			this.showMoreDemand = !this.showMoreDemand
			this.moreDemandFocus = false
			if (this.showMoreDemand) {
				this.summaryEditing = true
				if (!this.normalizeDemandValue(this.demandSummary.other)) {
					this.demandSummary.other = ''
				}
				this.$nextTick(() => {
					this.moreDemandFocus = true
				})
			}
		},
		async send() {
			const content = this.input.trim()
			if (!content || this.sending) return
			if (!uni.getStorageSync('access_token')) {
				return uni.navigateTo({ url: '/pages/auth/login' })
			}
			this.input = ''
			this.mergeParsedDemand(content)
			const guideContent = this.buildGuideContent(content)
			this.messages.push({ role: 'user', content })
			this.sending = true
			this.scroll()
			try {
				if (!this.sessionId) {
					this.sessionId = (await aiApi.createGuideSession({ title: this.makeSessionTitle(content) })).id
				}
				const response = await aiApi.sendGuideMessage(this.sessionId, { content: guideContent, limit: 5 })
				this.messages.push(response.assistant_message)
				this.recommendations = response.recommendations || []
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
			try {
				const session = await aiApi.session(item.id)
				this.sessionId = session.id
				this.messages = (session.messages || []).slice().sort((a, b) => a.id - b.id)
				const latestUserMessage = this.messages.filter(message => message.role === 'user').slice(-1)[0]
				this.demandSummary = latestUserMessage ? this.parseDemand(latestUserMessage.content) : this.emptySummary()
				this.recommendations = await aiApi.guideRecommendations(session.id)
				this.scroll()
			} catch (error) {
				uni.showToast({ title: '历史会话加载失败', icon: 'none' })
			}
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
		detail(id) {
			uni.navigateTo({ url: `/pages/mall/detail?id=${id}` })
		},
		parseDemand(content) {
			const text = content || ''
			const budgetMatch = text.match(/(?:预算|价格|价位)?\s*(\d{2,6})\s*(?:元|块|rmb|RMB)?/)
			const purposeKeywords = ['猫粮', '狗粮', '零食', '玩具', '用品', '牵引', '猫砂', '狗窝', '猫窝', '营养', '洗护']
			const preferenceKeywords = ['低敏', '耐咬', '轻便', '便携', '高蛋白', '无谷', '除臭', '屏幕清晰', '续航', '护眼']
			const purpose = purposeKeywords.find(keyword => text.includes(keyword))
			const preferences = preferenceKeywords.filter(keyword => text.includes(keyword)).slice(0, 3)
			return {
				budget: budgetMatch ? `${budgetMatch[1]} 元` : '待补充',
				purpose: purpose || '待补充',
				preference: preferences.length ? preferences.join('、') : '待补充',
				brand: '品牌不限',
				other: text.length > 18 ? `${text.slice(0, 18)}...` : (text || '待补充')
			}
		},
		normalizeDemandValue(value) {
			const text = String(value || '').trim()
			return ['待补充', '补充更多需求'].includes(text) ? '' : text
		},
		summaryValue(key) {
			return this.normalizeDemandValue(this.demandSummary[key]) || (key === 'brand' ? '品牌不限' : '待补充')
		},
		mergeParsedDemand(content) {
			const parsed = this.parseDemand(content)
			Object.keys(parsed).forEach(key => {
				if (!this.normalizeDemandValue(this.demandSummary[key])) {
					this.demandSummary[key] = parsed[key]
				}
			})
		},
		buildGuideContent(question) {
			const labels = {
				budget: '预算',
				purpose: '用途',
				preference: '偏好',
				brand: '品牌',
				other: '其他'
			}
			const summaryLines = Object.keys(labels)
				.map(key => {
					const value = this.normalizeDemandValue(this.demandSummary[key])
					if (!value) return ''
					return `${labels[key]}：${value}`
				})
				.filter(Boolean)
			if (!summaryLines.length) return question
			return [
				`用户问题：${question}`,
				'左侧需求摘要：',
				...summaryLines,
				'请同时依据用户问题和左侧需求摘要推荐真实在售商品。'
			].join('\n')
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
	grid-template-columns: 360px minmax(0, 1fr);
	background: #fff;
}
.guide-sidebar {
	width: 360px;
	min-width: 360px;
	max-width: 360px;
	min-height: 0;
	overflow: auto;
	padding: 24px 22px;
	border-right: 1px solid var(--color-border);
	background: var(--color-bg);
	scrollbar-gutter: stable both-edges;
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
	height: 42px;
	margin: 24px 0;
	padding: 0;
	border: 1px solid var(--color-primary);
	border-radius: 21px;
	background: #fff;
	color: var(--color-primary);
	font-size: 13px;
	line-height: 42px;
}
.summary-card,
.history-card,
.product-card {
	border: 1px solid var(--color-border);
	background: var(--color-surface);
	box-shadow: var(--shadow-card);
}
.summary-card,
.history-card {
	width: 100%;
	padding: 16px;
	border-radius: var(--radius-sm);
}
.history-card { margin-top: 14px; }
.panel-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 12px;
	font-size: 13px;
	font-weight: 800;
}
.panel-action {
	color: var(--color-primary);
	font-size: 10px;
	font-weight: 600;
}
.summary-row {
	display: grid;
	grid-template-columns: 22px 52px minmax(0, 1fr);
	align-items: center;
	gap: 6px;
	margin-top: 8px;
	padding: 9px 10px;
	border: 1px solid transparent;
	border-radius: var(--radius-sm);
	background: #fffaf6;
	font-size: 11px;
}
.summary-row:focus-within {
	border-color: rgba(255, 116, 23, .28);
	background: #fff;
}
.summary-icon {
	display: flex;
	width: 18px;
	height: 18px;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 10px;
	font-weight: 800;
}
.summary-label {
	color: var(--color-text);
	font-weight: 700;
}
.summary-value {
	overflow: hidden;
	min-width: 0;
	color: var(--color-text-secondary);
	text-align: right;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.summary-input {
	width: 100%;
	min-width: 0;
	height: 22px;
	padding: 0;
	border: 0;
	outline: 0;
	background: transparent;
	color: var(--color-text-secondary);
	text-align: right;
	font-size: 11px;
	line-height: 22px;
}
.summary-input::placeholder { color: #b9ada3; }
.more-demand-panel {
	margin-top: 10px;
	padding: 10px;
	border: 1px solid var(--color-border);
	border-radius: var(--radius-sm);
	background: #fffaf6;
}
.more-demand-panel textarea {
	width: 100%;
	min-height: 72px;
	color: var(--color-text);
	font-size: 12px;
	line-height: 1.6;
}
.more-demand {
	height: 34px;
	margin: 12px 0 0;
	padding: 0;
	border: 1px solid var(--color-border);
	border-radius: var(--radius-sm);
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 11px;
	line-height: 34px;
}
.history-empty {
	padding: 16px 0;
	color: var(--color-text-secondary);
	text-align: center;
	font-size: 11px;
}
.history-item {
	display: grid;
	grid-template-columns: 18px minmax(0, 1fr) 58px;
	gap: 6px;
	align-items: center;
	margin-top: 8px;
	padding: 10px;
	border-radius: var(--radius-sm);
	background: #fffaf6;
	font-size: 10px;
	cursor: pointer;
}
.history-item.active,
.history-item:hover { background: var(--color-primary-soft); }
.history-clock,
.history-time { color: var(--color-text-secondary); }
.history-title {
	overflow: hidden;
	color: var(--color-text);
	text-overflow: ellipsis;
	white-space: nowrap;
}
.history-time { text-align: right; }
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
.recommendations {
	max-width: 980px;
	margin: 8px auto 24px;
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
	width: 100%;
	height: 116px;
	border-radius: var(--radius-sm);
	background: #fffaf6;
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
