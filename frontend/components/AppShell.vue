<template>
	<view class="app-shell">
		<view class="desktop-header">
			<view class="header-inner">
				<view class="brand" @click="go('/pages/home/index')">
					<text class="brand-paw">🐾</text>
					<text>宠爱有家</text>
				</view>
				<view class="desktop-nav">
					<view v-for="item in navItems" :key="item.path" class="nav-item" :class="{ active: active === item.key }" @click="go(item.path)">
						<text v-if="item.icon" class="nav-icon">{{ item.icon }}</text>{{ item.label }}
					</view>
				</view>
				<view class="global-search">
					<text>⌕</text><input placeholder="搜索商品、社区内容" confirm-type="search" @confirm="search" />
				</view>
				<view class="cart-button" @click="openCartDrawer">🛒<text v-if="effectiveCartCount" class="badge">{{ effectiveCartCount }}</text></view>
			</view>
		</view>
		<slot />
		<view v-if="cartDrawerOpen" class="cart-mask" @click="closeCartDrawer"></view>
		<view class="cart-drawer" :class="{ open: cartDrawerOpen }">
			<view class="drawer-head">
				<view>
					<text class="drawer-title">购物车</text>
					<text class="drawer-subtitle">{{ loggedIn ? `${drawerItems.length} 件商品` : '登录后查看购物车' }}</text>
				</view>
				<button class="drawer-close" @click="closeCartDrawer">×</button>
			</view>
			<view v-if="!loggedIn" class="drawer-empty">
				<text class="empty-icon">🛒</text>
				<text class="empty-title">请先登录</text>
				<text class="empty-text">登录后可以查看购物车商品</text>
				<button class="drawer-action" @click="goLogin">去登录</button>
			</view>
			<view v-else-if="cartLoading" class="drawer-empty">
				<text class="empty-title">正在加载购物车...</text>
			</view>
			<view v-else-if="cartError" class="drawer-empty">
				<text class="empty-title">购物车加载失败</text>
				<text class="empty-text">{{ cartError }}</text>
				<button class="drawer-action" @click="loadCartItems">重试</button>
			</view>
			<view v-else-if="!drawerItems.length" class="drawer-empty">
				<text class="empty-icon">🛒</text>
				<text class="empty-title">购物车还是空的</text>
				<text class="empty-text">去商城挑选适合毛孩子的好物吧</text>
				<button class="drawer-action" @click="goMall">去逛逛</button>
			</view>
			<scroll-view v-else class="drawer-list" scroll-y>
				<view v-for="item in drawerItems" :key="item.id" class="drawer-item" :class="{ disabled: !item.available }" @click="goProduct(item.product.id)">
					<image v-if="item.product.cover_image" class="drawer-image" :src="assetUrl(item.product.cover_image)" mode="aspectFill" />
					<view v-else class="drawer-image placeholder">🥫</view>
					<view class="drawer-copy">
						<text class="drawer-product">{{ item.product.title }}</text>
						<text class="drawer-meta">{{ item.sku.name }} · {{ money(item.sku.price) }}</text>
						<text v-if="!item.available" class="drawer-unavailable">商品暂不可购买</text>
					</view>
					<view class="drawer-quantity" @click.stop>
						<button @click="updateCartQuantity(item, -1)">−</button>
						<text>{{ item.quantity }}</text>
						<button @click="updateCartQuantity(item, 1)">＋</button>
					</view>
				</view>
			</scroll-view>
		</view>
		<view class="mobile-nav">
			<view v-for="item in navItems" :key="item.path" class="mobile-nav-item" :class="{ active: active === item.key }" @click="go(item.path)">
				<text v-if="item.icon" class="mobile-nav-icon">{{ item.icon }}</text>
				<text>{{ item.label }}</text>
			</view>
		</view>
	</view>
</template>

<script>
import { assetUrl, cartApi } from '../api'
import { formatMoney } from '../utils/format'

export default {
	props: {
		active: { type: String, default: 'home' },
		cartCount: { type: Number, default: 0 }
	},
	data() {
		return {
			cartDrawerOpen: false,
			cartLoading: false,
			cartError: '',
			drawerItems: [],
			navItems: [
				{ key: 'home', label: '首页', icon: '⌂', path: '/pages/home/index' },
				{ key: 'mall', label: '商城', icon: '▣', path: '/pages/mall/index' },
				{ key: 'adoption', label: '领养', icon: '♡', path: '/pages/adoption/index' },
				{ key: 'community', label: '社区', icon: '◌', path: '/pages/community/index' },
				{ key: 'guide', label: 'AI 导购', icon: '✦', path: '/pages/agent/guide' },
				{ key: 'agent', label: 'AI 助手', icon: '◎', path: '/pages/agent/chat' },
				{ key: 'profile', label: '我的', icon: '♙', path: '/pages/profile/index' }
			]
		}
	},
	computed: {
		loggedIn() {
			return !!uni.getStorageSync('access_token')
		},
		effectiveCartCount() {
			return this.drawerItems.length || this.cartCount
		}
	},
	methods: {
		money: formatMoney,
		assetUrl,
		go(url) {
			uni.reLaunch({ url })
		},
		openCartDrawer() {
			this.cartDrawerOpen = true
			if (this.loggedIn) this.loadCartItems()
		},
		closeCartDrawer() {
			this.cartDrawerOpen = false
		},
		async loadCartItems() {
			this.cartLoading = true
			this.cartError = ''
			try {
				this.drawerItems = await cartApi.list() || []
			} catch (error) {
				this.cartError = error.message
			} finally {
				this.cartLoading = false
			}
		},
		async updateCartQuantity(item, delta) {
			const next = Math.max(1, Math.min(99, Number(item.quantity) + delta))
			if (next === item.quantity) return
			const before = item.quantity
			item.quantity = next
			try {
				const fresh = await cartApi.update(item.id, { quantity: next })
				Object.assign(item, fresh)
			} catch (error) {
				item.quantity = before
			}
		},
		goProduct(productId) {
			this.closeCartDrawer()
			uni.navigateTo({ url: `/pages/mall/detail?id=${productId}` })
		},
		goLogin() {
			this.closeCartDrawer()
			uni.navigateTo({ url: '/pages/auth/login' })
		},
		goMall() {
			this.closeCartDrawer()
			this.go('/pages/mall/index')
		},
		search(event) {
			const keyword = event.detail.value
			uni.setStorageSync('mall_keyword', keyword)
			this.go('/pages/mall/index')
		}
	}
}
</script>

<style scoped lang="scss">
.desktop-header {
	position: sticky;
	top: 0;
	z-index: 50;
	height: var(--header-height);
	background: rgba(255,255,255,.96);
	border-bottom: 1px solid var(--color-border);
}
.header-inner {
	display: flex;
	align-items: center;
	gap: 28px;
	max-width: 1440px;
	height: 100%;
	margin: 0 auto;
	padding: 0 28px;
}
.brand {
	display: flex;
	align-items: center;
	color: var(--color-primary);
	font-size: 23px;
	font-weight: 800;
	white-space: nowrap;
	cursor: pointer;
}
.brand-paw { margin-right: 8px; font-size: 26px; }
.desktop-nav { display: flex; align-items: stretch; height: 100%; }
.nav-item {
	position: relative;
	display: flex;
	align-items: center;
	gap: 7px;
	padding: 0 16px;
	font-size: 15px;
	white-space: nowrap;
	cursor: pointer;
}
.nav-item.active { color: var(--color-primary); font-weight: 700; }
.nav-item.active::after {
	position: absolute; right: 16px; bottom: 0; left: 16px; height: 3px;
	border-radius: 3px 3px 0 0; background: var(--color-primary); content: "";
}
.nav-icon { font-size: 17px; }
.global-search {
	display: flex; align-items: center; gap: 8px; width: 260px; height: 38px;
	margin-left: auto; padding: 0 14px; border: 1px solid var(--color-border);
	border-radius: 20px; color: var(--color-text-secondary);
}
.global-search input { width: 100%; font-size: 13px; }
.cart-button { position: relative; font-size: 22px; cursor: pointer; }
.badge {
	position: absolute; top: -8px; right: -10px; min-width: 17px; height: 17px;
	padding: 0 4px; border-radius: 10px; background: var(--color-primary);
	color: #fff; font-size: 10px; line-height: 17px; text-align: center;
}
.cart-mask {
	position: fixed;
	inset: 0;
	z-index: 80;
	background: rgba(25, 18, 12, .24);
}
.cart-drawer {
	position: fixed;
	top: 0;
	right: 0;
	z-index: 81;
	display: flex;
	width: 380px;
	max-width: 92vw;
	height: 100vh;
	flex-direction: column;
	border-left: 1px solid var(--color-border);
	background: #fff;
	box-shadow: -18px 0 42px rgba(56,38,22,.18);
	transform: translateX(100%);
	transition: transform .24s ease;
}
.cart-drawer.open { transform: translateX(0); }
.drawer-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 14px;
	padding: 22px 20px 16px;
	border-bottom: 1px solid var(--color-border);
}
.drawer-title,.drawer-subtitle { display: block; }
.drawer-title { font-size: 22px; font-weight: 800; }
.drawer-subtitle { margin-top: 5px; color: var(--color-text-secondary); font-size: 12px; }
.drawer-close {
	width: 34px;
	height: 34px;
	margin: 0;
	padding: 0;
	border-radius: 50%;
	background: #fff7f0;
	color: var(--color-primary);
	font-size: 20px;
	line-height: 34px;
}
.drawer-list {
	min-height: 0;
	flex: 1;
	padding: 8px 16px 18px;
}
.drawer-item {
	display: grid;
	grid-template-columns: 58px minmax(0,1fr) auto;
	gap: 11px;
	align-items: center;
	padding: 14px 0;
	border-bottom: 1px solid #f2e8df;
	cursor: pointer;
}
.drawer-item.disabled { opacity: .62; }
.drawer-image {
	display: block;
	width: 58px;
	height: 58px;
	overflow: hidden;
	border-radius: 8px;
	background: #f7efe7;
	object-fit: cover;
}
.drawer-image.placeholder {
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 28px;
}
.drawer-copy {
	display: flex;
	min-width: 0;
	flex-direction: column;
}
.drawer-product {
	overflow: hidden;
	color: var(--color-text);
	font-size: 13px;
	font-weight: 700;
	line-height: 1.4;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.drawer-meta {
	margin-top: 5px;
	color: var(--color-text-secondary);
	font-size: 11px;
}
.drawer-unavailable {
	margin-top: 4px;
	color: var(--color-danger);
	font-size: 10px;
}
.drawer-quantity {
	display: flex;
	align-items: center;
	border: 1px solid var(--color-border);
	border-radius: 17px;
	background: #fff;
}
.drawer-quantity button {
	width: 27px;
	height: 27px;
	margin: 0;
	padding: 0;
	background: #fff;
	color: var(--color-text);
	font-size: 13px;
	line-height: 27px;
}
.drawer-quantity text {
	width: 24px;
	text-align: center;
	font-size: 12px;
}
.drawer-empty {
	display: flex;
	flex: 1;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 28px;
	text-align: center;
}
.empty-icon { font-size: 48px; }
.empty-title {
	margin-top: 12px;
	color: var(--color-text);
	font-size: 18px;
	font-weight: 800;
}
.empty-text {
	margin-top: 8px;
	color: var(--color-text-secondary);
	font-size: 13px;
	line-height: 1.6;
}
.drawer-action {
	margin-top: 20px;
	padding: 0 24px;
	border: 1px solid var(--color-primary);
	border-radius: 22px;
	background: #fff;
	color: var(--color-primary);
	font-size: 14px;
}
.mobile-nav { display: none; }
@media (max-width: 900px) {
	.desktop-header { display: none; }
	.mobile-nav {
		position: fixed; right: 0; bottom: 0; left: 0; z-index: 50;
		display: flex; height: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom));
		padding-bottom: env(safe-area-inset-bottom); background: rgba(255,255,255,.97);
		border-top: 1px solid var(--color-border);
	}
	.mobile-nav-item {
		display: flex; flex: 1; flex-direction: column; align-items: center; justify-content: center;
		gap: 3px; color: #8b8179; font-size: 11px;
	}
	.mobile-nav-item.active { color: var(--color-primary); font-weight: 700; }
	.mobile-nav-icon { font-size: 20px; line-height: 22px; }
}
</style>
