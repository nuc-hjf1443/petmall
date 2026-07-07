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
				<view class="guide-context">
					<text class="side-label">当前服务</text>
					<text>商城商品推荐</text>
					<text class="muted">推荐只引用商城真实商品，不编造库存、价格和商品链接。</text>
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
					<view class="welcome">
						<view class="welcome-icon">荐</view>
						<text class="welcome-title">你好，我是导购助手</text>
						<text class="welcome-sub">我会基于商城在售商品生成推荐，并说明推荐理由和注意事项。</text>
						<view class="suggestions">
							<view v-for="item in suggestions" :key="item" @click="ask(item)">{{ item }}</view>
						</view>
					</view>
					<view v-for="(msg,index) in messages" :id="`guide-msg-${index}`" :key="index" class="message-row" :class="msg.role">
						<view class="message-avatar">{{ msg.role === 'user' ? '我' : '荐' }}</view>
						<view class="bubble"><text>{{ msg.content }}</text></view>
					</view>
					<view v-if="recommendations.length" class="recommendations">
						<view v-for="item in recommendations" :key="item.product_id" class="recommend-card" @click="detail(item.product_id)">
							<view class="recommend-rank">#{{ item.rank }}</view>
							<view class="recommend-copy">
								<text class="recommend-title">{{ item.product.title }}</text>
								<text class="recommend-reason">{{ item.reason }}</text>
								<text v-if="item.caution" class="recommend-caution">{{ item.caution }}</text>
							</view>
							<text class="recommend-link">查看</text>
						</view>
					</view>
					<view v-if="sending" class="message-row assistant">
						<view class="message-avatar">荐</view>
						<view class="bubble typing">正在匹配真实商品...</view>
					</view>
				</scroll-view>
				<view class="composer">
					<textarea v-model="input" auto-height maxlength="1000" placeholder="例如：3 岁柯基，需要低敏狗粮，预算 300 元" @confirm="send" />
					<button :disabled="sending" @click="send">➤</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { aiApi } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			sessionId: null,
			input: '',
			messages: [],
			recommendations: [],
			sending: false,
			scrollTarget: '',
			suggestions: [
				'3 岁柯基，需要低敏狗粮，预算 300 元',
				'幼猫刚到家，需要准备哪些用品？',
				'狗狗爱啃家具，有什么玩具推荐？'
			]
		}
	},
	methods: {
		reset() {
			this.sessionId = null
			this.input = ''
			this.messages = []
			this.recommendations = []
		},
		ask(text) {
			this.input = text
			this.send()
		},
		async send() {
			const content = this.input.trim()
			if (!content || this.sending) return
			if (!uni.getStorageSync('access_token')) {
				return uni.navigateTo({ url: '/pages/auth/login' })
			}
			this.input = ''
			this.messages.push({ role: 'user', content })
			this.sending = true
			this.scroll()
			try {
				if (!this.sessionId) {
					this.sessionId = (await aiApi.createGuideSession({})).id
				}
				const response = await aiApi.sendGuideMessage(this.sessionId, { content, limit: 5 })
				this.messages.push(response.assistant_message)
				this.recommendations = response.recommendations || []
			} catch (error) {
				this.messages.push({ role: 'assistant', content: `暂时无法生成推荐：${error.message}` })
			} finally {
				this.sending = false
				this.scroll()
			}
		},
		scroll() {
			this.$nextTick(() => {
				this.scrollTarget = `guide-msg-${this.messages.length - 1}`
			})
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/mall/detail?id=${id}` })
		}
	}
}
</script>

<style scoped lang="scss">
.guide-page{display:grid;height:calc(100vh - var(--header-height));height:calc(100dvh - var(--header-height));min-height:0;overflow:hidden;grid-template-columns:290px minmax(0,1fr);background:#fff}.guide-sidebar{min-height:0;overflow:hidden;padding:24px;border-right:1px solid var(--color-border);background:#fffaf6}.assistant-brand{display:flex;align-items:center;gap:12px;font-size:15px;font-weight:800}.assistant-brand text{display:block}.assistant-brand text:last-child{margin-top:4px;color:var(--color-text-secondary);font-size:10px;font-weight:400}.guide-logo{display:flex;width:42px;height:42px;align-items:center;justify-content:center;border-radius:14px;background:#e8f4ff;color:var(--color-primary);font-size:20px;font-weight:900}.new-chat{height:42px;margin:28px 0;padding:0;border:1px solid var(--color-primary);border-radius:21px;background:#fff;color:var(--color-primary);font-size:13px;line-height:42px}.guide-context{display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:14px;background:#fff;font-size:13px}.side-label{color:var(--color-primary);font-size:10px;font-weight:700}.guide-context .muted{font-size:10px;line-height:1.6}.guide-main{display:flex;height:100%;min-width:0;min-height:0;overflow:hidden;flex-direction:column}.guide-header{display:flex;height:75px;flex:none;align-items:center;justify-content:space-between;padding:0 30px;border-bottom:1px solid var(--color-border)}.guide-title,.guide-sub{display:block}.guide-title{font-size:18px;font-weight:800}.guide-sub{margin-top:4px;color:var(--color-text-secondary);font-size:11px}.shield{color:#4b8b66;font-size:11px}.messages{height:0;min-height:0;flex:1 1 0;overflow:hidden;padding:28px 5%}.welcome{display:flex;max-width:650px;flex-direction:column;align-items:center;margin:4vh auto 30px;text-align:center}.welcome-icon{display:flex;width:70px;height:70px;align-items:center;justify-content:center;border-radius:23px;background:var(--color-primary-soft);color:var(--color-primary);font-size:30px;font-weight:900}.welcome-title{margin-top:17px;font-size:24px;font-weight:800}.welcome-sub{max-width:500px;margin-top:10px;color:var(--color-text-secondary);font-size:13px;line-height:1.7}.suggestions{display:flex;flex-wrap:wrap;justify-content:center;gap:9px;margin-top:20px}.suggestions view{padding:9px 15px;border:1px solid var(--color-border);border-radius:18px;background:#fff;font-size:11px}.message-row{display:flex;max-width:780px;gap:10px;margin:20px auto}.message-row.user{flex-direction:row-reverse}.message-avatar{display:flex;width:34px;height:34px;flex:none;align-items:center;justify-content:center;border-radius:11px;background:#fff0e4;color:var(--color-primary);font-size:11px;font-weight:800}.bubble{max-width:75%;padding:13px 16px;border-radius:5px 16px 16px 16px;background:#f8f3ee;font-size:13px;line-height:1.8}.user .bubble{border-radius:16px 5px 16px 16px;background:var(--color-primary);color:#fff}.typing{color:var(--color-text-secondary)}.recommendations{display:grid;max-width:780px;gap:10px;margin:8px auto 22px}.recommend-card{display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;align-items:center;padding:14px 16px;border:1px solid var(--color-border);border-radius:12px;background:#fff;box-shadow:0 8px 22px rgba(70,45,24,.06);cursor:pointer}.recommend-rank{display:flex;width:36px;height:36px;align-items:center;justify-content:center;border-radius:12px;background:var(--color-primary-soft);color:var(--color-primary);font-size:12px;font-weight:800}.recommend-copy{display:flex;min-width:0;flex-direction:column}.recommend-title{overflow:hidden;font-size:14px;font-weight:800;text-overflow:ellipsis;white-space:nowrap}.recommend-reason{margin-top:5px;color:var(--color-text-secondary);font-size:11px;line-height:1.5}.recommend-caution{margin-top:5px;color:var(--color-warning);font-size:10px}.recommend-link{color:var(--color-primary);font-size:12px;font-weight:800}.composer{display:flex;flex:none;align-items:flex-end;gap:10px;margin:16px 5% 24px;padding:10px 10px 10px 17px;border:1px solid var(--color-border);border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(70,45,24,.08)}.composer textarea{flex:1;min-height:26px;max-height:100px;padding:5px 0;font-size:13px}.composer button{display:flex;width:38px;height:38px;align-items:center;justify-content:center;margin:0;border-radius:12px;background:var(--color-primary);color:#fff;font-size:15px;line-height:38px}
@media(max-width:900px){.guide-page{height:calc(100vh - var(--bottom-nav-height) - env(safe-area-inset-bottom));height:calc(100dvh - var(--bottom-nav-height) - env(safe-area-inset-bottom));grid-template-columns:1fr}.guide-sidebar{display:none}.guide-header{height:64px;padding:0 16px}.guide-title{font-size:16px}.guide-sub{font-size:9px}.messages{padding:15px 14px 95px}.welcome{margin-top:3vh}.welcome-icon{width:58px;height:58px;font-size:24px}.welcome-title{font-size:20px}.welcome-sub{font-size:11px}.suggestions{flex-direction:column}.message-row{margin:15px auto}.bubble{max-width:82%;font-size:12px}.recommend-card{grid-template-columns:36px minmax(0,1fr);align-items:start}.recommend-link{display:none}.composer{position:fixed;right:12px;bottom:calc(var(--bottom-nav-height) + env(safe-area-inset-bottom) + 8px);left:12px;z-index:40;margin:0}}
</style>
