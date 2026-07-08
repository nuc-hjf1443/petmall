<template>
	<AppShell active="profile">
		<view class="page-container profile-page">
			<view class="profile-layout">
				<view class="profile-card card">
					<view class="avatar">{{ loggedIn ? '🐾' : '👤' }}</view>
					<view class="user-info">
						<text class="nickname">{{ user.nickname || (loggedIn ? '宠爱用户' : '登录后开启专属服务') }}</text>
						<text class="phone">{{ maskedPhone }}</text>
					</view>
					<button v-if="!loggedIn" class="login-button" @click="go('/pages/auth/login')">登录 / 注册</button>
					<template v-else>
						<text class="edit" @click="go('/pages/profile/edit')">编辑资料 ></text>
						<button class="logout-button" @click="logout">退出登录</button>
					</template>
					<view class="stats">
						<view><text>{{ pets.length }}</text><text>我的宠物</text></view>
						<view><text>{{ coin.balance || 0 }}</text><text>宠物币</text></view>
						<view><text>0</text><text>我的收藏</text></view>
					</view>
					<view class="wallet-summary">
						<view class="wallet-copy" @click="go('/pages/wallet/index')">
							<text>账户余额</text>
							<text>{{ money(wallet.balance) }}</text>
							<text>冻结 {{ money(wallet.frozen_balance) }}</text>
						</view>
						<view class="wallet-actions">
							<button @click="go('/pages/wallet/index')">充值</button>
							<button @click="go('/pages/wallet/index')">提现</button>
						</view>
					</view>
				</view>

				<view class="profile-content">
					<view class="order-card card">
						<view class="card-title">
							<text>我的订单</text>
							<text class="more" @click="go('/pages/order/index')">全部订单 ></text>
						</view>
						<view class="order-actions">
							<view v-for="item in orderActions" :key="item.label" @click="go('/pages/order/index')">
								<text class="action-icon">{{ item.icon }}</text>
								<text>{{ item.label }}</text>
							</view>
						</view>
					</view>

					<view class="menu-card card">
						<view v-for="item in menus" :key="item.label" class="menu-item" @click="go(item.path, item)">
							<view class="menu-icon" :style="{ background: item.bg }">{{ item.icon }}</view>
							<view class="menu-copy">
								<text class="menu-title">{{ item.label }}</text>
								<text class="menu-desc">{{ item.desc }}</text>
							</view>
							<text class="arrow">›</text>
						</view>
					</view>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { authApi, coinApi, petApi, userApi, walletApi } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { AppShell },
	data() {
		return {
			user: {},
			pets: [],
			coin: {},
			wallet: {},
			orderActions: [
				{ icon: '◷', label: '待付款' },
				{ icon: '▣', label: '待发货' },
				{ icon: '⇥', label: '待收货' },
				{ icon: '♡', label: '待评价' }
			],
			menus: [
				{ icon: '🐾', label: '宠物档案', desc: '成长记录、健康提醒与详细资料', bg: '#fff0e3', path: '/pages/pet/index' },
				{ icon: 'AI', label: 'AI 养宠助手', desc: '基于可信知识的日常养宠问答', bg: '#eaf4ff', path: '/pages/agent/chat' },
				{ icon: '荐', label: 'AI 智能导购', desc: '基于真实商城商品生成推荐', bg: '#eaf4ff', path: '/pages/agent/guide' },
				{ icon: '▤', label: '私人知识库', desc: '管理专属于你和宠物的资料', bg: '#f0ebff', path: '/pages/knowledge/index' },
				{ icon: 'P', label: '宠物币中心', desc: '签到、任务与宠物币流水', bg: '#fff2d8', path: '/pages/coin/index' },
				{ icon: '钱', label: '账户余额', desc: '充值、提现与余额流水', bg: '#e9f8ef', path: '/pages/wallet/index' },
				{ icon: '⌖', label: '地址管理', desc: '管理商城收货地址', bg: '#e9f8ef', path: '/pages/address/index' },
				{ icon: '店', label: '商家中心', desc: '申请入驻与管理商品', bg: '#fff0e3', path: '/pages/merchant/index' },
				{ icon: '⚙', label: '资料与安全', desc: '个人偏好与账号密码', bg: '#f5f2ef', path: '/pages/profile/edit' },
				{ icon: '管', label: '管理后台', desc: '管理员审核与平台治理', bg: '#eef3ff', path: '/pages/admin/index', adminOnly: true }
			]
		}
	},
	computed: {
		loggedIn() {
			return !!uni.getStorageSync('access_token')
		},
		maskedPhone() {
			const p = this.user.phone || ''
			return p ? p.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '欢迎来到宠爱有家'
		}
	},
	onShow() {
		if (this.loggedIn) this.load()
	},
	methods: {
		money: formatMoney,
		async go(path, item = null) {
			if (!this.loggedIn && path !== '/pages/auth/login') {
				return uni.navigateTo({ url: '/pages/auth/login' })
			}
			if (item?.adminOnly || path === '/pages/admin/index') {
				try {
					const user = this.user?.id ? this.user : await userApi.me()
					this.user = user || {}
					if (!this.user.is_admin) {
						return uni.showToast({ title: '您还不是管理员,拒绝访问!', icon: 'none' })
					}
				} catch (e) {
					return
				}
			}
			uni.navigateTo({ url: path })
		},
		logout() {
			uni.showModal({
				title: '退出登录',
				content: '确定退出当前账号？',
				success: async res => {
					if (!res.confirm) return
					try {
						await authApi.logout()
					} finally {
						this.user = {}
						this.pets = []
						this.coin = {}
						this.wallet = {}
						uni.showToast({ title: '已退出登录', icon: 'none' })
						setTimeout(() => uni.reLaunch({ url: '/pages/home/index' }), 300)
					}
				}
			})
		},
		async load() {
			const r = await Promise.allSettled([
				userApi.me(),
				petApi.list(),
				coinApi.account(),
				walletApi.account()
			])
			if (r[0].status === 'fulfilled') this.user = r[0].value || {}
			if (r[1].status === 'fulfilled') this.pets = r[1].value || []
			if (r[2].status === 'fulfilled') this.coin = r[2].value || {}
			if (r[3].status === 'fulfilled') this.wallet = r[3].value || {}
		}
	}
}
</script>

<style scoped lang="scss">
.profile-layout{display:grid;grid-template-columns:330px 1fr;gap:22px;align-items:start}.profile-card{position:sticky;top:90px;padding:28px;text-align:center}.avatar{display:flex;width:88px;height:88px;align-items:center;justify-content:center;margin:0 auto;border:5px solid #fff3e8;border-radius:50%;background:#ffe7cf;font-size:48px}.nickname,.phone{display:block}.nickname{margin-top:14px;font-size:21px;font-weight:800}.phone{margin-top:6px;color:var(--color-text-secondary);font-size:12px}.login-button{height:38px;margin:18px auto 0;padding:0 22px;border-radius:20px;background:var(--color-primary);color:#fff;font-size:13px;line-height:38px}.edit{display:block;margin-top:13px;color:var(--color-primary);font-size:12px}.logout-button{height:34px;margin:14px auto 0;padding:0 22px;border:1px solid var(--color-border);border-radius:17px;background:#fff;color:var(--color-text-secondary);font-size:12px;line-height:34px}.logout-button:active{border-color:var(--color-primary);color:var(--color-primary)}.stats{display:grid;grid-template-columns:repeat(3,1fr);margin-top:24px;padding-top:22px;border-top:1px solid var(--color-border)}.stats view{display:flex;flex-direction:column;gap:5px;color:var(--color-text-secondary);font-size:11px}.stats view text:first-child{color:var(--color-text);font-size:19px;font-weight:800}.stats view+view{border-left:1px solid var(--color-border)}.wallet-summary{margin-top:22px;padding:16px;border:1px solid var(--color-border);border-radius:8px;background:#fffaf6;text-align:left}.wallet-copy{display:flex;flex-direction:column;gap:5px}.wallet-copy text:first-child,.wallet-copy text:last-child{color:var(--color-text-secondary);font-size:11px}.wallet-copy text:nth-child(2){color:var(--color-primary);font-size:25px;font-weight:800}.wallet-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.wallet-actions button{height:34px;border-radius:8px;background:var(--color-primary);color:#fff;font-size:12px;line-height:34px}.wallet-actions button+button{background:#fff;border:1px solid var(--color-primary);color:var(--color-primary)}.profile-content{display:flex;flex-direction:column;gap:18px}.order-card,.menu-card{padding:22px}.card-title{display:flex;align-items:center;justify-content:space-between;font-size:18px;font-weight:800}.more{color:var(--color-text-secondary);font-size:12px;font-weight:400}.order-actions{display:grid;grid-template-columns:repeat(4,1fr);margin-top:25px}.order-actions view{display:flex;flex-direction:column;align-items:center;gap:9px;font-size:12px}.action-icon{font-size:27px;color:var(--color-primary)}.menu-card{display:grid;grid-template-columns:1fr 1fr;gap:4px 28px}.menu-item{display:flex;align-items:center;padding:18px 6px;border-bottom:1px solid #f3ece6;cursor:pointer}.menu-icon{display:flex;width:45px;height:45px;align-items:center;justify-content:center;border-radius:13px;color:var(--color-primary);font-size:17px;font-weight:800}.menu-copy{display:flex;flex:1;min-width:0;flex-direction:column;margin-left:13px}.menu-title{font-size:15px;font-weight:700}.menu-desc{overflow:hidden;margin-top:5px;color:var(--color-text-secondary);font-size:11px;text-overflow:ellipsis;white-space:nowrap}.arrow{color:#aaa;font-size:22px}
@media(max-width:900px){.profile-layout{display:block}.profile-card{position:static;padding:20px}.avatar{width:68px;height:68px;font-size:38px}.nickname{font-size:18px}.stats{margin-top:18px;padding-top:17px}.profile-content{margin-top:12px;gap:12px}.order-card,.menu-card{padding:16px}.menu-card{display:block}.menu-item{padding:14px 2px}.menu-icon{width:40px;height:40px}.menu-title{font-size:14px}.menu-desc{font-size:10px}}
</style>
