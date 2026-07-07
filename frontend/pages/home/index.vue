<template>
	<AppShell active="home">
		<view class="page-container home-page">
			<view class="mobile-topbar">
				<view><text class="city">杭州市⌄</text><text class="hello">你好，欢迎回家</text></view>
				<view class="top-actions">♡　◌</view>
			</view>
			<view class="mobile-search" @click="go('/pages/mall/index')">⌕　搜索商品、服务、问题</view>

			<view class="hero-grid">
				<view class="hero">
					<view class="hero-copy">
						<text class="eyebrow">PETMALL · 宠爱有家</text>
						<text class="hero-title">用心陪伴，宠爱一生</text>
						<text class="hero-subtitle">商城、健康档案、智能问答与温暖社区，一站式照顾毛孩子</text>
						<button class="hero-button" @click="go('/pages/pet/index')">记录它的每一天</button>
					</view>
					<view class="pet-visual">
						<text class="pet-emoji">🐶</text><text class="pet-emoji cat">🐱</text>
					</view>
				</view>
				<view class="pet-summary card">
					<template v-if="pets.length">
						<view class="pet-head">
							<view class="pet-avatar">{{ petEmoji(pets[0].pet_type) }}</view>
							<view><text class="pet-name">{{ pets[0].name }}</text><text class="pet-meta">{{ pets[0].breed || '可爱伙伴' }}</text></view>
							<text class="manage" @click="go('/pages/pet/index')">管理 ></text>
						</view>
						<view class="pet-stats">
							<view><text class="stat-value">{{ pets[0].weight || '--' }}</text><text>kg 体重</text></view>
							<view><text class="stat-value">{{ pets[0].vaccine_status || '待完善' }}</text><text>疫苗</text></view>
						</view>
						<view class="health-tip">💚 今天也要记得陪它玩一会儿</view>
					</template>
					<StatePanel v-else icon="🐾" title="建立宠物档案" description="记录健康与成长，获得更贴心的照护建议" action="立即添加" @action="go('/pages/pet/index')" />
				</view>
			</view>

			<view class="quick-grid">
				<view v-for="item in quickActions" :key="item.label" class="quick-item" @click="go(item.path)">
					<view class="quick-icon" :style="{ background: item.bg }">{{ item.icon }}</view>
					<text>{{ item.label }}</text>
				</view>
			</view>

			<view class="section-title"><text>为你推荐</text><text class="section-more" @click="go('/pages/mall/index')">查看全部 ></text></view>
			<scroll-view class="product-scroll" scroll-x>
				<view class="product-row">
					<view v-for="(product, index) in products" :key="product.id || index" class="product-card card" @click="go(`/pages/mall/detail?id=${product.id}`)">
						<image v-if="product.cover_image" class="product-image" :src="assetUrl(product.cover_image)" mode="aspectFill" />
						<view v-else class="product-placeholder">{{ ['🥫','🦴','🧸','🧴'][index % 4] }}</view>
						<text class="product-title">{{ product.title }}</text>
						<text class="product-price">{{ money(product.price) }}</text>
					</view>
				</view>
			</scroll-view>

			<view class="content-columns">
				<view class="feature-card card adoption-feature" @click="go('/pages/adoption/index')">
					<view><text class="feature-kicker">温暖领养</text><text class="feature-title">用领养，给彼此一个家</text><text class="feature-link">看看等待中的它们 →</text></view>
					<text class="feature-emoji">🐕</text>
				</view>
				<view class="feature-card card ai-feature" @click="go('/pages/agent/chat')">
					<view><text class="feature-kicker">AI 养宠助手</text><text class="feature-title">有问题，随时问小宠</text><text class="feature-link">开始咨询 →</text></view>
					<text class="feature-emoji">✨</text>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { assetUrl, petApi, productApi } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			pets: [],
			products: [
				{ id: 'demo1', title: '低温烘焙全价犬粮', price: 12800 },
				{ id: 'demo2', title: '营养鲜肉猫咪主食罐', price: 6800 },
				{ id: 'demo3', title: '耐咬洁齿磨牙玩具', price: 2900 },
				{ id: 'demo4', title: '温和免洗清洁泡沫', price: 5900 }
			],
			quickActions: [
				{ label: '宠物商城', icon: '▣', bg: '#fff0e3', path: '/pages/mall/index' },
				{ label: '温暖领养', icon: '♡', bg: '#fff5dc', path: '/pages/adoption/index' },
				{ label: 'AI 助手', icon: 'AI', bg: '#eaf4ff', path: '/pages/agent/chat' },
				{ label: '宠物档案', icon: '🐾', bg: '#e9f8ef', path: '/pages/pet/index' },
				{ label: '知识库', icon: '▤', bg: '#f0ebff', path: '/pages/knowledge/index' },
				{ label: '宠物币', icon: 'P', bg: '#fff2d8', path: '/pages/coin/index' },
				{ label: '社区', icon: '◌', bg: '#ffecef', path: '/pages/community/index' },
				{ label: '购物车', icon: '🛒', bg: '#eef3ff', path: '/pages/cart/index' }
			]
		}
	},
	onShow() {
		this.load()
	},
	methods: {
		assetUrl,
		go(url) { uni.navigateTo({ url }) },
		money: formatMoney,
		petEmoji(type) { return String(type).toLowerCase().includes('cat') || type === '猫' ? '🐱' : '🐶' },
		async load() {
			const jobs = [
				productApi.list({ page: 1, page_size: 4 }).then(res => { if (res?.items?.length) this.products = res.items }).catch(() => {}),
				petApi.list().then(res => { this.pets = Array.isArray(res) ? res : [] }).catch(() => {})
			]
			await Promise.allSettled(jobs)
		}
	}
}
</script>

<style scoped lang="scss">
.mobile-topbar,.mobile-search { display:none; }
.hero-grid { display:grid; grid-template-columns:minmax(0,2.1fr) minmax(280px,.8fr); gap:18px; }
.hero {
	position:relative; display:flex; min-height:330px; overflow:hidden; padding:56px;
	border-radius:24px; background:radial-gradient(circle at 78% 34%,#fff 0,#ffe4c8 19%,transparent 20%),linear-gradient(115deg,#fff1dc,#ffd7ae);
	box-shadow:var(--shadow-card);
}
.hero::before,.hero::after { position:absolute; color:rgba(255,122,26,.18); font-size:58px; content:"🐾"; transform:rotate(-18deg); }
.hero::before { top:24px; right:36px; }.hero::after { bottom:18px; left:46%; font-size:36px; }
.hero-copy { position:relative; z-index:2; display:flex; width:55%; flex-direction:column; align-items:flex-start; }
.eyebrow { color:var(--color-primary); font-size:13px; font-weight:800; letter-spacing:2px; }
.hero-title { margin-top:22px; color:#713d1e; font-size:40px; font-weight:800; line-height:1.25; }
.hero-subtitle { max-width:520px; margin-top:14px; color:#805d46; font-size:16px; line-height:1.8; }
.hero-button { margin:26px 0 0; padding:0 25px; border-radius:22px; background:var(--color-primary); color:#fff; font-size:14px; }
.pet-visual { position:absolute; right:6%; bottom:14%; z-index:1; display:flex; align-items:flex-end; }
.pet-emoji { font-size:120px; filter:drop-shadow(0 15px 12px rgba(93,54,22,.12)); }.pet-emoji.cat { margin-left:-25px; font-size:105px; }
.pet-summary { padding:22px; }
.pet-head { display:flex; align-items:center; gap:12px; }
.pet-avatar { display:flex; width:58px; height:58px; align-items:center; justify-content:center; border-radius:50%; background:#fff0df; font-size:35px; }
.pet-name,.pet-meta { display:block; }.pet-name { font-size:18px; font-weight:700; }.pet-meta { margin-top:5px; color:var(--color-text-secondary); font-size:12px; }
.manage { margin-left:auto; color:var(--color-primary); font-size:12px; }
.pet-stats { display:grid; grid-template-columns:1fr 1fr; margin:24px 0; }
.pet-stats view { display:flex; flex-direction:column; align-items:center; gap:5px; color:var(--color-text-secondary); font-size:11px; }
.pet-stats view+view { border-left:1px solid var(--color-border); }.stat-value { color:var(--color-text); font-size:17px; font-weight:700; }
.health-tip { padding:14px; border-radius:12px; background:#f0faf4; color:#43815e; font-size:12px; }
.quick-grid { display:grid; grid-template-columns:repeat(8,1fr); margin-top:18px; padding:20px 16px; border:1px solid var(--color-border); border-radius:18px; background:#fff; }
.quick-item { display:flex; flex-direction:column; align-items:center; gap:8px; font-size:13px; cursor:pointer; }
.quick-icon { display:flex; width:48px; height:48px; align-items:center; justify-content:center; border-radius:15px; color:var(--color-primary); font-weight:800; }
.product-scroll { width:100%; white-space:nowrap; }.product-row { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.product-card { display:flex; min-width:0; flex-direction:column; overflow:hidden; padding-bottom:16px; }
.product-image,.product-placeholder { width:100%; height:180px; }.product-placeholder { display:flex; align-items:center; justify-content:center; background:linear-gradient(145deg,#fff8ef,#f4e8da); font-size:70px; }
.product-title { overflow:hidden; margin:14px 14px 7px; font-size:14px; font-weight:600; text-overflow:ellipsis; white-space:nowrap; }
.product-price { margin:0 14px; color:var(--color-primary); font-size:17px; font-weight:800; }
.content-columns { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:28px; }
.feature-card { display:flex; min-height:150px; align-items:center; justify-content:space-between; padding:28px 34px; cursor:pointer; }
.adoption-feature { background:linear-gradient(120deg,#fff,#fff1e7); }.ai-feature { background:linear-gradient(120deg,#fff,#eef6ff); }
.feature-kicker,.feature-title,.feature-link { display:block; }.feature-kicker { color:var(--color-primary); font-size:12px; font-weight:700; }.feature-title { margin:10px 0; font-size:21px; font-weight:800; }.feature-link { color:var(--color-text-secondary); font-size:13px; }.feature-emoji { font-size:68px; }
@media(max-width:900px) {
	.mobile-topbar { display:flex; align-items:center; justify-content:space-between; padding:8px 2px 12px; }
	.city,.hello { display:block; }.city { font-size:18px; font-weight:800; }.hello { margin-top:3px; color:var(--color-text-secondary); font-size:11px; }.top-actions { font-size:18px; }
	.mobile-search { display:block; height:40px; margin-bottom:12px; padding:0 14px; border-radius:20px; background:#fff; color:#9b948e; font-size:13px; line-height:40px; }
	.hero-grid { display:block; }.pet-summary { margin-top:12px; }
	.hero { min-height:190px; padding:24px 22px; border-radius:18px; }.hero-copy { width:67%; }.eyebrow { font-size:10px; }.hero-title { margin-top:11px; font-size:25px; }.hero-subtitle { margin-top:8px; font-size:12px; line-height:1.5; }.hero-button { height:32px; margin-top:14px; padding:0 15px; font-size:11px; line-height:32px; }
	.pet-visual { right:0; bottom:11%; }.pet-emoji { font-size:65px; }.pet-emoji.cat { margin-left:-18px; font-size:55px; }
	.quick-grid { grid-template-columns:repeat(4,1fr); row-gap:18px; padding:18px 4px; }.quick-item { font-size:11px; }.quick-icon { width:42px; height:42px; }
	.product-row { display:flex; gap:10px; }.product-card { width:145px; flex:none; }.product-image,.product-placeholder { height:125px; }.product-placeholder { font-size:50px; }
	.content-columns { grid-template-columns:1fr; gap:12px; }.feature-card { min-height:120px; padding:22px; }.feature-title { font-size:17px; }.feature-emoji { font-size:50px; }
}
</style>
