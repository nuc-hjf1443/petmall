<template>
	<AppShell active="profile">
		<view class="page-container favorite-page">
			<view class="page-head">
				<view>
					<text class="title">我的收藏</text>
					<text class="subtitle">你收藏的商城商品会显示在这里</text>
				</view>
				<button @click="load">刷新</button>
			</view>

			<StatePanel v-if="!loggedIn" title="请先登录" desc="登录后查看收藏商品" action-text="去登录" @action="goLogin" />
			<StatePanel v-else-if="error" title="加载失败" :desc="error" action-text="重试" @action="load" />
			<StatePanel v-else-if="!loading && !items.length" title="暂无收藏" desc="在商品详情页点击收藏后会出现在这里" action-text="去商城" @action="goMall" />

			<view v-else class="favorite-grid">
				<view v-for="item in items" :key="item.id" class="product-card card" @click="detail(item.id)">
					<image v-if="item.cover_image" class="product-image" :src="assetUrl(item.cover_image)" mode="aspectFill" />
					<view v-else class="product-image placeholder">宠</view>
					<view class="product-copy">
						<text class="product-title">{{ item.title }}</text>
						<text class="product-meta">{{ item.brand || '精选商品' }} · {{ item.applicable_pet_type || '通用' }}</text>
						<text class="price">{{ money(item.price) }}</text>
					</view>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { assetUrl, productApi } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			items: [],
			loading: true,
			error: ''
		}
	},
	computed: {
		loggedIn() {
			return !!uni.getStorageSync('access_token')
		}
	},
	onShow() {
		if (this.loggedIn) this.load()
		else this.loading = false
	},
	methods: {
		assetUrl,
		money: formatMoney,
		async load() {
			this.loading = true
			this.error = ''
			try {
				const result = await productApi.favorites({ page: 1, page_size: 100 })
				this.items = result?.items || []
			} catch (error) {
				this.error = error.message || '收藏加载失败'
			} finally {
				this.loading = false
			}
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/mall/detail?id=${id}` })
		},
		goLogin() {
			uni.navigateTo({ url: '/pages/auth/login' })
		},
		goMall() {
			uni.reLaunch({ url: '/pages/mall/index' })
		}
	}
}
</script>

<style scoped lang="scss">
.favorite-page{padding-top:34px}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px}.title,.subtitle{display:block}.title{font-size:28px;font-weight:900}.subtitle{margin-top:7px;color:var(--color-text-secondary);font-size:13px}.page-head button{height:36px;padding:0 22px;border:1px solid var(--color-border);border-radius:18px;background:#fff;color:var(--color-text);font-size:12px;line-height:36px}.favorite-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.product-card{overflow:hidden;cursor:pointer}.product-image{display:block;width:100%;height:190px;overflow:hidden;background:#fff2e8;object-fit:cover}.placeholder{display:flex;align-items:center;justify-content:center;color:var(--color-primary);font-size:42px;font-weight:900}.product-copy{display:flex;min-height:118px;flex-direction:column;padding:14px}.product-title{font-size:15px;font-weight:800}.product-meta{margin-top:7px;color:var(--color-text-secondary);font-size:11px}.price{margin-top:auto;color:var(--color-primary);font-size:20px;font-weight:900}
@media(max-width:900px){.favorite-page{padding-top:18px}.favorite-grid{grid-template-columns:1fr 1fr;gap:12px}.product-image{height:140px}.title{font-size:23px}}
</style>
