<template>
	<AppShell active="mall">
		<view class="page-container mall-page">
			<view class="page-heading">
				<view>
					<text class="page-title">宠物商城</text>
					<text class="page-subtitle">严选好物，认真照顾每一份陪伴</text>
				</view>
				<view class="search-box">
					<text>⌕</text>
					<input v-model="keyword" placeholder="搜索商品" confirm-type="search" @confirm="loadProducts" />
				</view>
			</view>

			<view class="mall-layout">
				<view class="category-sidebar">
					<view class="sidebar-title">全部分类</view>
					<view class="category-node root" :class="{ active: !categoryId }" @click="selectAllCategories">
						<text class="node-icon">▦</text>
						<text class="node-name">全部商品</text>
						<text class="node-arrow">›</text>
					</view>
					<view v-for="first in firstCategories" :key="first.id" class="tree-group">
						<view class="category-node level-1" :class="{ active: firstCategoryId === first.id }" @click="toggleFirst(first)">
							<text class="node-icon">{{ categoryIcon(first.name) }}</text>
							<text class="node-name">{{ first.name }}</text>
							<text class="node-arrow" :class="{ expanded: expandedFirstId === first.id }">›</text>
						</view>
						<view v-if="expandedFirstId === first.id" class="second-list">
							<view v-for="second in childCategories(first.id)" :key="second.id" class="second-group">
								<view class="category-node level-2" :class="{ active: secondCategoryId === second.id }" @click="toggleSecond(second)">
									<text class="node-name">{{ second.name }}</text>
									<text class="node-arrow" :class="{ expanded: expandedSecondId === second.id }">›</text>
								</view>
								<view v-if="expandedSecondId === second.id" class="third-list">
									<view v-for="third in childCategories(second.id)" :key="third.id" class="category-node level-3" :class="{ active: thirdCategoryId === third.id }" @click="selectThirdCategory(third)">
										<text class="node-name">{{ third.name }}</text>
									</view>
								</view>
							</view>
						</view>
					</view>
				</view>

				<view class="mall-main">
					<view class="filter-panel">
						<view class="filter-row">
							<text class="filter-label">宠物类别</text>
							<view v-for="item in petTypeOptions" :key="item.value || 'all-pet'" class="filter-chip" :class="{ active: petType === item.value }" @click="selectPetType(item.value)">
								{{ item.label }}
							</view>
						</view>
						<view class="filter-row">
							<text class="filter-label">品牌</text>
							<view v-for="item in brandOptions" :key="item.value || 'all-brand'" class="filter-chip" :class="{ active: brandKeyword === item.value }" @click="selectBrand(item.value)">
								{{ item.label }}
							</view>
						</view>
						<view class="filter-row">
							<text class="filter-label">价格区间</text>
							<view v-for="item in priceOptions" :key="item.label" class="filter-chip" :class="{ active: selectedPriceLabel === item.label }" @click="selectPrice(item)">
								{{ item.label }}
							</view>
						</view>
						<view class="filter-row sort-row">
							<text class="filter-label">综合</text>
							<view class="sort-chip" :class="{ active: sort === 'sales' }" @click="selectSort('sales')">销量</view>
							<view class="sort-chip" :class="{ active: sort === 'newest' }" @click="selectSort('newest')">新品</view>
							<view class="sort-chip" :class="{ active: sort === 'price_asc' || sort === 'price_desc' }" @click="togglePriceSort">
								价格{{ sort === 'price_asc' ? '↑' : sort === 'price_desc' ? '↓' : '' }}
							</view>
						</view>
					</view>

					<view v-if="loading" class="product-grid">
						<view v-for="i in 8" :key="i" class="skeleton card"></view>
					</view>
					<StatePanel v-else-if="error" icon="⚠" title="商品加载失败" :description="error" action="重新加载" @action="loadProducts" />
					<StatePanel v-else-if="!products.length" icon="🛍" title="暂时没有商品" description="换个关键词或分类看看吧" />
					<view v-else class="product-grid">
						<view v-for="(product,index) in products" :key="product.id" class="product-card card" @click="detail(product.id)">
							<image v-if="product.cover_image" class="product-image" :src="assetUrl(product.cover_image)" mode="aspectFill" />
							<view v-else class="product-image placeholder">{{ ['🥫','🦴','🧸','🧴','🍖'][index%5] }}</view>
							<view class="product-body">
								<text class="product-title">{{ product.title }}</text>
								<view class="product-tags">
									<text class="product-tag">{{ product.applicable_pet_type || '猫犬通用' }}</text>
									<text v-if="product.brand" class="product-tag brand-tag">{{ product.brand }}</text>
								</view>
								<view class="product-bottom">
									<text class="price">{{ money(product.price) }}</text>
									<button class="cart-add" @click.stop="detail(product.id)">＋</button>
								</view>
							</view>
						</view>
					</view>
					<view v-if="totalPages > 1" class="pagination-panel">
						<text class="pagination-summary">共 {{ total }} 件 / 第 {{ page }} 页</text>
						<view class="pagination-actions">
							<button class="page-button" :disabled="page <= 1 || loadingPage" @click="previousPage">上一页</button>
							<button
								v-for="item in paginationPages"
								:key="item"
								class="page-button number"
								:class="{ active: item === page }"
								:disabled="item === page || loadingPage"
								@click="goPage(item)"
							>{{ item }}</button>
							<button class="page-button" :disabled="page >= totalPages || loadingPage" @click="nextPage">下一页</button>
						</view>
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
			keyword: '',
			firstCategoryId: null,
			secondCategoryId: null,
			thirdCategoryId: null,
			expandedFirstId: null,
			expandedSecondId: null,
			petType: '',
			brandKeyword: '',
			priceRange: null,
			sort: 'sales',
			categories: [],
			products: [],
			page: 1,
			pageSize: 8,
			total: 0,
			loading: true,
			loadingPage: 0,
			error: '',
			petTypeOptions: [
				{ label: '全部', value: '' },
				{ label: '猫', value: '猫' },
				{ label: '狗', value: '狗' },
				{ label: '猫犬通用', value: '猫犬通用' },
				{ label: '小宠', value: '小宠' },
				{ label: '水族', value: '水族' },
				{ label: '其他', value: '其他' }
			],
			brandOptions: [
				{ label: '全部', value: '' },
				{ label: '皇家', value: '皇家' },
				{ label: '伯纳天纯', value: '伯纳天纯' },
				{ label: '麦富迪', value: '麦富迪' },
				{ label: '网易严选', value: '网易严选' },
				{ label: 'pidan', value: 'pidan' },
				{ label: '卫仕', value: '卫仕' },
				{ label: '其他', value: '其他' }
			],
			priceOptions: [
				{ label: '全部', min: null, max: null },
				{ label: '0-50', min: 0, max: 5000 },
				{ label: '50-100', min: 5000, max: 10000 },
				{ label: '100-200', min: 10000, max: 20000 },
				{ label: '200-300', min: 20000, max: 30000 },
				{ label: '300以上', min: 30000, max: null }
			]
		}
	},
	computed: {
		firstCategories() {
			return this.categories.filter(item => !item.parent_id)
		},
		categoryId() {
			return this.thirdCategoryId || this.secondCategoryId || this.firstCategoryId
		},
		selectedPriceLabel() {
			return this.priceRange?.label || '全部'
		},
		totalPages() {
			return Math.max(1, Math.ceil(this.total / this.pageSize))
		},
		paginationPages() {
			const pages = []
			const start = Math.max(1, this.page - 2)
			const end = Math.min(this.totalPages, start + 4)
			const normalizedStart = Math.max(1, end - 4)
			for (let item = normalizedStart; item <= end; item += 1) {
				pages.push(item)
			}
			return pages
		}
	},
	onLoad() {
		this.keyword = uni.getStorageSync('mall_keyword') || ''
		uni.removeStorageSync('mall_keyword')
		this.load()
	},
	methods: {
		assetUrl,
		money: formatMoney,
		childCategories(parentId) {
			return this.categories.filter(item => item.parent_id === parentId)
		},
		async load() {
			await Promise.allSettled([
				productApi.categories().then(categories => {
					this.categories = categories || []
				}),
				this.loadProducts()
			])
		},
		async loadProducts(targetPage = 1) {
			const nextPage = Math.max(1, Number(targetPage) || 1)
			this.loading = true
			this.loadingPage = nextPage
			this.error = ''
			try {
				const params = { page: nextPage, page_size: this.pageSize, sort: this.sort }
				if (this.keyword) params.keyword = this.keyword
				if (this.categoryId) params.category_id = this.categoryId
				if (this.petType) params.pet_type = this.petType
				if (this.brandKeyword) params.brand_keyword = this.brandKeyword
				if (this.priceRange?.min !== null && this.priceRange?.min !== undefined) params.min_price = this.priceRange.min
				if (this.priceRange?.max !== null && this.priceRange?.max !== undefined) params.max_price = this.priceRange.max
				const response = await productApi.list(params)
				this.products = response?.items || []
				this.total = response?.total || 0
				this.page = response?.page || nextPage
				this.pageSize = response?.page_size || this.pageSize
			} catch (error) {
				this.error = error.message
			} finally {
				this.loading = false
				this.loadingPage = 0
			}
		},
		goPage(page) {
			if (page === this.page || this.loadingPage) return
			this.loadProducts(page)
			this.scrollToProducts()
		},
		previousPage() {
			if (this.page <= 1) return
			this.goPage(this.page - 1)
		},
		nextPage() {
			if (this.page >= this.totalPages) return
			this.goPage(this.page + 1)
		},
		scrollToProducts() {
			uni.pageScrollTo({ scrollTop: 0, duration: 180 })
		},
		categoryIcon(name) {
			if (name.includes('食品')) return '☷'
			if (name.includes('用品')) return '▣'
			if (name.includes('洗护')) return '◌'
			if (name.includes('健康')) return '◇'
			if (name.includes('服饰')) return '◈'
			if (name.includes('活体')) return '♡'
			if (name.includes('服务')) return '◎'
			return '▸'
		},
		selectAllCategories() {
			this.firstCategoryId = null
			this.secondCategoryId = null
			this.thirdCategoryId = null
			this.expandedFirstId = null
			this.expandedSecondId = null
			this.loadProducts(1)
		},
		toggleFirst(item) {
			const willCollapse = this.expandedFirstId === item.id
			this.firstCategoryId = item.id
			this.secondCategoryId = null
			this.thirdCategoryId = null
			this.expandedFirstId = willCollapse ? null : item.id
			this.expandedSecondId = null
			this.loadProducts(1)
		},
		toggleSecond(item) {
			const willCollapse = this.expandedSecondId === item.id
			this.secondCategoryId = item.id
			this.thirdCategoryId = null
			this.expandedSecondId = willCollapse ? null : item.id
			this.loadProducts(1)
		},
		selectThirdCategory(item) {
			this.thirdCategoryId = item.id
			this.loadProducts(1)
		},
		selectPetType(value) {
			this.petType = value
			this.loadProducts(1)
		},
		selectBrand(value) {
			this.brandKeyword = value
			this.loadProducts(1)
		},
		selectPrice(item) {
			this.priceRange = item.min === null && item.max === null ? null : item
			this.loadProducts(1)
		},
		selectSort(value) {
			this.sort = value
			this.loadProducts(1)
		},
		togglePriceSort() {
			this.sort = this.sort === 'price_asc' ? 'price_desc' : 'price_asc'
			this.loadProducts(1)
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/mall/detail?id=${id}` })
		}
	}
}
</script>

<style scoped lang="scss">
.page-heading{display:flex;align-items:flex-end;justify-content:space-between;margin:12px 0 24px}.page-title,.page-subtitle{display:block}.page-title{font-size:30px;font-weight:800}.page-subtitle{margin-top:8px;color:var(--color-text-secondary);font-size:14px}.search-box{display:flex;align-items:center;width:330px;height:44px;padding:0 16px;border:1px solid var(--color-border);border-radius:23px;background:#fff;color:#999}.search-box input{width:100%;margin-left:8px;font-size:14px}.mall-layout{display:grid;grid-template-columns:234px minmax(0,1fr);gap:30px;align-items:start}.category-sidebar{position:sticky;top:96px;overflow:hidden;border:1px solid var(--color-border);border-radius:8px;background:#fff}.sidebar-title{padding:18px 24px;border-bottom:1px solid #f1e8df;color:var(--color-text);font-size:20px;font-weight:800}.category-node{display:grid;grid-template-columns:22px minmax(0,1fr) 14px;gap:10px;align-items:center;min-height:56px;padding:0 22px;color:var(--color-text-secondary);font-size:15px;cursor:pointer}.category-node.root,.category-node.level-1{border-top:1px solid #f8f1ea}.category-node.level-2{grid-template-columns:minmax(0,1fr) 14px;min-height:42px;padding-left:54px;font-size:14px}.category-node.level-3{display:flex;min-height:34px;padding-left:70px;font-size:13px}.category-node.active,.category-node:hover{background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.node-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.node-icon{color:inherit;text-align:center}.node-arrow{color:#b9aea4;text-align:right;transition:.2s}.node-arrow.expanded{transform:rotate(90deg);color:var(--color-primary)}.second-list,.third-list{background:#fffdfa}.mall-main{min-width:0}.filter-panel{margin-bottom:18px;overflow:hidden;border:1px solid var(--color-border);border-radius:8px;background:#fff}.filter-row{display:flex;min-height:62px;align-items:center;gap:14px;padding:11px 20px;border-bottom:1px solid #f1e8df}.filter-row:last-child{border-bottom:0}.filter-label{width:76px;flex:none;color:var(--color-primary);font-size:15px;font-weight:800}.filter-chip,.sort-chip{min-height:34px;padding:7px 18px;border:1px solid transparent;border-radius:18px;color:var(--color-text-secondary);font-size:14px;line-height:20px;cursor:pointer}.filter-chip.active,.filter-chip:hover,.sort-chip.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.sort-row{background:#fffdfa}.product-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.product-card{overflow:hidden;border-radius:8px;transition:.2s}.product-card:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(89,56,29,.12)}.product-image{width:100%;height:190px;background:#f7efe7}.placeholder{display:flex;align-items:center;justify-content:center;font-size:64px}.product-body{display:flex;flex-direction:column;padding:13px}.product-title{display:-webkit-box;overflow:hidden;min-height:40px;font-size:14px;font-weight:700;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:2}.product-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.product-tag{align-self:flex-start;padding:3px 8px;border-radius:5px;background:#f7f3ef;color:#8a8179;font-size:10px}.brand-tag{background:#eef7ff;color:#4d779c}.product-bottom{display:flex;align-items:center;justify-content:space-between;margin-top:12px}.price{color:var(--color-primary);font-size:18px;font-weight:800}.cart-add{display:flex;width:30px;height:30px;align-items:center;justify-content:center;margin:0;border-radius:50%;background:var(--color-primary);color:#fff;font-size:18px;line-height:30px}.skeleton{height:292px;background:linear-gradient(90deg,#f7f0e9 25%,#fff8f2 37%,#f7f0e9 63%);background-size:400% 100%;animation:pulse 1.4s infinite}@keyframes pulse{0%{background-position:100% 0}100%{background-position:0 0}}@media(max-width:1200px){.mall-layout{grid-template-columns:210px minmax(0,1fr);gap:20px}.product-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:900px){.page-heading{display:block;margin:6px 0 14px}.page-title{font-size:23px}.page-subtitle{font-size:12px}.search-box{width:100%;margin-top:14px}.mall-layout{display:block}.category-sidebar{position:static;margin-bottom:12px}.sidebar-title{padding:12px 16px;font-size:16px}.category-node{min-height:42px;padding:0 14px;font-size:13px}.category-node.level-2{padding-left:38px}.category-node.level-3{padding-left:52px}.filter-panel{margin-bottom:12px}.filter-row{overflow:auto;min-height:46px;padding:8px 10px}.filter-label{width:auto;min-width:max-content}.filter-chip,.sort-chip{min-width:max-content}.product-grid{grid-template-columns:repeat(2,1fr);gap:10px}.product-image{height:165px}.placeholder{font-size:55px}.product-body{padding:11px}.product-title{min-height:38px;font-size:13px}.price{font-size:16px}.skeleton{height:255px}}
.pagination-panel{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:22px;padding:14px 18px;border:1px solid var(--color-border);border-radius:8px;background:#fff}.pagination-summary{color:var(--color-text-secondary);font-size:13px}.pagination-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.page-button{display:flex;min-width:42px;height:34px;align-items:center;justify-content:center;margin:0;padding:0 12px;border:1px solid var(--color-border);border-radius:8px;background:#fff;color:var(--color-text);font-size:13px;line-height:34px}.page-button::after{display:none}.page-button.number{padding:0;min-width:34px}.page-button.active{border-color:var(--color-primary);background:var(--color-primary);color:#fff;font-weight:800}.page-button[disabled]{opacity:.45;cursor:not-allowed}
@media(max-width:900px){.pagination-panel{display:block;margin-top:16px;padding:12px}.pagination-summary{display:block;margin-bottom:10px}.pagination-actions{justify-content:flex-start;overflow-x:auto;flex-wrap:nowrap;padding-bottom:2px}.page-button{flex:none;height:32px;line-height:32px}}
</style>
