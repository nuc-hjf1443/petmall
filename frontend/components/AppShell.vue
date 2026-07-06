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
						<text class="nav-icon">{{ item.icon }}</text>{{ item.label }}
					</view>
					<view class="nav-item" :class="{ active: active === 'agent' }" @click="go('/pages/agent/chat')">AI 助手</view>
				</view>
				<view class="global-search">
					<text>⌕</text><input placeholder="搜索商品、社区内容" confirm-type="search" @confirm="search" />
				</view>
				<view class="cart-button" @click="go('/pages/cart/index')">🛒<text v-if="cartCount" class="badge">{{ cartCount }}</text></view>
			</view>
		</view>
		<slot />
		<view class="mobile-nav">
			<view v-for="item in navItems" :key="item.path" class="mobile-nav-item" :class="{ active: active === item.key }" @click="go(item.path)">
				<text class="mobile-nav-icon">{{ item.icon }}</text>
				<text>{{ item.label }}</text>
			</view>
		</view>
	</view>
</template>

<script>
export default {
	props: {
		active: { type: String, default: 'home' },
		cartCount: { type: Number, default: 0 }
	},
	data() {
		return {
			navItems: [
				{ key: 'home', label: '首页', icon: '⌂', path: '/pages/home/index' },
				{ key: 'mall', label: '商城', icon: '▣', path: '/pages/mall/index' },
				{ key: 'adoption', label: '领养', icon: '♡', path: '/pages/adoption/index' },
				{ key: 'community', label: '社区', icon: '◌', path: '/pages/community/index' },
				{ key: 'profile', label: '我的', icon: '♙', path: '/pages/profile/index' }
			]
		}
	},
	methods: {
		go(url) {
			uni.reLaunch({ url })
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
