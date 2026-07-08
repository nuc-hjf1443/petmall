<template>
	<AppShell active="mall">
		<view class="page-container product-page">
			<view v-if="loading" class="card empty-inline">正在加载商品详情...</view>
			<StatePanel v-else-if="error" icon="!" title="商品加载失败" :description="error" action="重试" @action="load" />
			<template v-else-if="product">
				<view class="product-layout">
					<view class="card gallery">
						<image v-if="activeImage" :src="assetUrl(activeImage)" mode="aspectFill" />
						<view v-else class="placeholder">
							<text>宠物食品</text>
							<text>建议上传狗粮包装或宠物食品实拍图</text>
						</view>
					</view>

					<view class="card product-info">
						<view class="title-row">
							<view>
								<text class="page-title">{{ product.title }}</text>
								<view v-if="product.merchant" class="merchant-line">
									<text>{{ product.merchant.shop_name }}</text>
									<text class="merchant-stats">已售 1280 · 好评率 98%</text>
									<button v-if="!isOwnMerchant" class="link-button" @click="toggleMerchantFollow">
										{{ product.following_merchant ? '取消关注' : '关注商家' }}
									</button>
									<text v-else class="owner-note">自己的店铺</text>
								</view>
							</view>
						</view>

						<text class="description">{{ product.description || '适合日常喂养，营养均衡，支持 7 天无理由。' }}</text>
						<text class="price">{{ money(selectedSku?.price ?? product.price) }}</text>

						<view class="block">
							<text class="label">规格</text>
							<view class="sku-row">
								<view
									v-for="sku in product.skus"
									:key="sku.id"
									class="sku-chip"
									:class="{ active: selectedSku?.id === sku.id }"
									@click="selectedSku = sku"
								>
									{{ sku.name }} · 库存 {{ sku.stock }}
								</view>
							</view>
						</view>

						<view class="block quantity-block">
							<text class="label">数量</text>
							<view class="quantity">
								<button @click="quantity = Math.max(1, quantity - 1)">-</button>
								<text>{{ quantity }}</text>
								<button @click="quantity = Math.min(99, quantity + 1)">+</button>
							</view>
						</view>

						<view class="button-row action-row">
							<button class="action-button" :loading="adding" @click="addCart">加入购物车</button>
							<button class="secondary-button buy-button" @click="addCart">立即购买</button>
							<button class="secondary-button" @click="toggleFavorite">{{ product.favorited_by_me ? '取消收藏' : '收藏' }}</button>
							<button class="secondary-button" :disabled="isOwnMerchant" @click="contactMerchant">{{ isOwnMerchant ? '自己的店铺' : '联系商家' }}</button>
						</view>
					</view>
				</view>

				<view class="card panel reviews">
					<view class="review-head">
						<text class="panel-title">用户评价 {{ reviewData.total || 0 }}</text>
						<text class="review-hint">购买后可发布真实评价</text>
					</view>
					<view v-if="!reviewData.items?.length" class="empty-review">暂无评价，购买后可以发布真实评价。</view>
					<view v-else class="review-list">
						<view v-for="item in reviewData.items" :key="item.id" class="review-card">
							<text class="review-stars">{{ '★'.repeat(item.rating) }}</text>
							<text class="review-sku">{{ item.sku_name }}</text>
							<text class="review-content">{{ item.content || '用户未填写文字评价' }}</text>
						</view>
					</view>

					<view class="review-form">
						<text class="panel-title small">购买后评价</text>
						<view class="form-grid">
							<label class="form-field">
								<text>选择已完成订单</text>
								<input v-model.number="reviewForm.order_item_id" type="number" placeholder="请输入可评价订单商品 ID" />
							</label>
							<label class="form-field">
								<text>评分</text>
								<input v-model.number="reviewForm.rating" type="number" placeholder="1-5" />
							</label>
							<label class="form-field full">
								<text>评价内容</text>
								<textarea v-model="reviewForm.content" placeholder="分享真实购买体验" />
							</label>
						</view>
						<view class="button-row">
							<button class="action-button" @click="createReview">提交评价</button>
						</view>
					</view>
				</view>
			</template>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { assetUrl, cartApi, getAccessToken, merchantApi, productApi, supportApi, userApi } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			id: null,
			product: null,
			selectedSku: null,
			quantity: 1,
			currentUserId: null,
			reviewData: { items: [] },
			reviewForm: { order_item_id: null, rating: 5, content: '', is_anonymous: false },
			loading: true,
			adding: false,
			error: ''
		}
	},
	computed: {
		activeImage() {
			return this.product?.images?.find(item => item.is_primary)?.image_url || this.product?.cover_image
		},
		isOwnMerchant() {
			return !!this.currentUserId && this.product?.merchant?.owner_user_id === this.currentUserId
		}
	},
	onLoad(query) {
		this.id = query.id
		this.load()
	},
	methods: {
		assetUrl,
		money: formatMoney,
		ensureLogin() {
			if (getAccessToken()) return true
			uni.navigateTo({ url: '/pages/auth/login' })
			return false
		},
		async load() {
			this.loading = true
			this.error = ''
			try {
				const tasks = [
					productApi.detail(this.id),
					productApi.reviews(this.id, { page: 1, page_size: 20 })
				]
				if (getAccessToken()) tasks.push(userApi.me())
				const result = await Promise.allSettled(tasks)
				if (result[0].status === 'fulfilled') {
					this.product = result[0].value
					this.selectedSku = this.product.skus?.find(item => item.stock > 0 && item.is_enabled) || this.product.skus?.[0]
				} else {
					throw result[0].reason
				}
				if (result[1].status === 'fulfilled') this.reviewData = result[1].value
				if (result[2]?.status === 'fulfilled') this.currentUserId = result[2].value?.id
			} catch (error) {
				this.error = error.message
			} finally {
				this.loading = false
			}
		},
		async addCart() {
			if (!this.ensureLogin()) return
			if (!this.selectedSku) return uni.showToast({ title: '请选择规格', icon: 'none' })
			this.adding = true
			try {
				await cartApi.add({ sku_id: this.selectedSku.id, quantity: this.quantity })
				uni.showToast({ title: '已加入购物车' })
			} finally {
				this.adding = false
			}
		},
		async toggleFavorite() {
			if (!this.ensureLogin()) return
			await (this.product.favorited_by_me ? productApi.unfavorite(this.id) : productApi.favorite(this.id))
			this.product.favorited_by_me = !this.product.favorited_by_me
			uni.showToast({ title: this.product.favorited_by_me ? '已收藏' : '已取消收藏' })
		},
		async toggleMerchantFollow() {
			if (!this.ensureLogin() || !this.product?.merchant || this.isOwnMerchant) return
			const merchantId = this.product.merchant.id
			await (this.product.following_merchant ? merchantApi.unfollow(merchantId) : merchantApi.follow(merchantId))
			this.product.following_merchant = !this.product.following_merchant
			uni.showToast({ title: this.product.following_merchant ? '已关注商家' : '已取消关注' })
		},
		async contactMerchant() {
			if (!this.ensureLogin()) return
			if (this.isOwnMerchant) return uni.showToast({ title: '不能联系自己的店铺客服', icon: 'none' })
			const conversation = await supportApi.merchantByProduct(this.id)
			uni.navigateTo({ url: `/pages/support/merchant?id=${conversation.id}` })
		},
		async createReview() {
			if (!this.ensureLogin()) return
			if (!this.reviewForm.order_item_id) return uni.showToast({ title: '请选择可评价的订单', icon: 'none' })
			await productApi.createReview(this.id, this.reviewForm)
			this.reviewForm = { order_item_id: null, rating: 5, content: '', is_anonymous: false }
			uni.showToast({ title: '评价已发布' })
			this.load()
		}
	}
}
</script>

<style scoped lang="scss">
.product-page{max-width:1180px}.product-layout{display:grid;grid-template-columns:minmax(390px,1fr) minmax(420px,1fr);gap:22px;align-items:stretch}.gallery{display:flex;min-height:500px;align-items:center;justify-content:center;overflow:hidden}.gallery image{width:100%;height:500px}.placeholder{display:flex;width:100%;height:500px;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(145deg,#fff4ea,#ffffff);color:var(--color-text-secondary);gap:10px;text-align:center}.placeholder text:first-child{color:var(--color-primary);font-size:30px;font-weight:900}.product-info{display:flex;flex-direction:column;padding:26px 28px}.title-row{display:block}.page-title{font-size:28px;line-height:1.25;word-break:break-all}.merchant-line{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;margin-top:14px;padding-bottom:14px;border-bottom:1px solid var(--color-border);color:var(--color-text-secondary);font-size:13px}.merchant-stats{min-width:0;text-align:left}.link-button{height:30px;margin:0;padding:0 12px;border:1px solid var(--color-border);border-radius:15px;background:#fff;color:var(--color-primary);font-size:12px;line-height:30px}.owner-note{padding:5px 10px;border-radius:14px;background:var(--color-primary-soft);color:var(--color-primary);font-size:12px;white-space:nowrap}.description{display:block;margin:22px 0 8px;color:var(--color-text-secondary);font-size:15px;line-height:1.75}.price{display:block;margin:18px 0 20px;color:var(--color-primary);font-size:34px;font-weight:900;line-height:1}.block{margin-top:16px}.label{display:block;margin-bottom:10px;color:var(--color-text);font-size:15px;font-weight:900}.sku-row{display:flex;flex-wrap:wrap;gap:10px}.sku-chip{padding:10px 14px;border:1px solid var(--color-border);border-radius:10px;background:#fff;font-size:13px;line-height:1.4}.sku-chip.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.quantity-block{display:flex;align-items:center;gap:16px}.quantity{display:flex;align-items:center;width:max-content;border:1px solid var(--color-border);border-radius:18px;background:#fff;overflow:hidden}.quantity button{width:38px;margin:0;background:#fff;color:var(--color-text);font-size:16px}.quantity text{width:42px;text-align:center}.action-row{margin-top:26px}.action-row button{height:42px;min-width:104px;line-height:42px}.action-row button[disabled]{opacity:.55}.buy-button{border-color:var(--color-primary);color:var(--color-primary)}.reviews{margin-top:22px}.review-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.review-hint{color:var(--color-text-secondary);font-size:12px}.empty-review{padding:20px;border-radius:12px;background:#fff8f2;color:var(--color-text-secondary);font-size:14px}.review-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.review-card{padding:16px;border:1px solid var(--color-border);border-radius:12px;background:#fff}.review-stars,.review-sku,.review-content{display:block}.review-stars{color:var(--color-primary)}.review-sku{margin-top:6px;font-size:13px;font-weight:800}.review-content{margin-top:8px;color:var(--color-text-secondary);font-size:13px;line-height:1.6}.review-form{margin-top:22px;padding-top:20px;border-top:1px solid var(--color-border)}.panel-title.small{font-size:16px}@media(max-width:900px){.product-layout{grid-template-columns:1fr}.gallery,.gallery image,.placeholder{height:320px;min-height:320px}.product-info{padding:22px}.merchant-line{grid-template-columns:1fr;align-items:start}.review-list{grid-template-columns:1fr}.action-row button{width:100%}}
</style>
