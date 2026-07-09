<template>
	<AppShell active="profile">
		<view class="merchant-page">
			<view v-if="loading" class="page-container">
				<view class="card loading-card">正在加载商家资料...</view>
			</view>

			<view v-else-if="!canEnterBackend" class="page-container apply-page">
				<view class="apply-hero">
					<view>
						<text class="apply-kicker">Merchant Center</text>
						<text class="apply-title">{{ gateTitle }}</text>
						<text class="apply-desc">{{ gateDescription }}</text>
					</view>
					<view class="apply-status" :class="merchantStatusClass">
						<text>{{ merchantStatusText }}</text>
					</view>
				</view>

				<view class="apply-grid">
					<view class="card apply-form-card">
						<view class="section-head">
							<view>
								<text class="section-title">{{ merchant ? '店铺资料' : '申请成为商家' }}</text>
								<text class="section-subtitle">提交后由平台审核，审核通过后自动开放商家后台。</text>
							</view>
						</view>
						<view class="form-grid">
							<label v-for="field in fields" :key="field.key" class="form-field" :class="{ full: field.full }">
								<text>{{ field.label }}<text v-if="field.required" class="required">*</text></text>
								<textarea v-if="field.full" v-model.trim="form[field.key]" :placeholder="field.placeholder" />
								<input v-else v-model.trim="form[field.key]" :placeholder="field.placeholder" />
							</label>
						</view>
						<view v-if="merchant?.audit_reason" class="audit-note">
							<text>审核备注：{{ merchant.audit_reason }}</text>
						</view>
						<view class="button-row">
							<button class="action-button" :loading="saving" :disabled="saving || merchant?.status === 'pending' || merchant?.status === 'frozen'" @click="save">
								{{ applyButtonText }}
							</button>
						</view>
					</view>

					<view class="card apply-side-card">
						<text class="section-title">入驻后可使用</text>
						<view class="benefit-list">
							<view v-for="item in benefits" :key="item.title" class="benefit-item">
								<text class="benefit-icon">{{ item.icon }}</text>
								<view>
									<text>{{ item.title }}</text>
									<text>{{ item.desc }}</text>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>

			<view v-else class="merchant-console">
				<view class="merchant-sidebar">
					<view class="merchant-brand">
						<view class="brand-mark">宠</view>
						<view>
							<text>{{ merchant.shop_name }}</text>
							<text>商家后台</text>
						</view>
					</view>
					<view class="sidebar-menu">
						<view
							v-for="item in menuItems"
							:key="item.key"
							class="sidebar-item"
							:class="{ active: activeTab === item.key }"
							@click="setActiveTab(item.key)"
						>
							<text>{{ item.icon }}</text>
							<text>{{ item.label }}</text>
						</view>
					</view>
				</view>

				<view class="console-main">
					<view class="console-topbar">
						<view>
							<text class="welcome">欢迎回来，{{ merchant.contact_name || merchant.shop_name }}</text>
							<text class="topbar-subtitle">管理店铺资料、商品和订单履约</text>
						</view>
						<view class="topbar-actions">
							<view class="avatar">{{ avatarText }}</view>
						</view>
					</view>

					<view v-if="activeTab === 'home'" class="console-content">
						<view class="summary-grid">
							<view v-for="item in todayStats" :key="item.label" class="card summary-card">
								<text>{{ item.label }}</text>
								<text>{{ item.value }}</text>
								<text>{{ item.desc }}</text>
							</view>
						</view>

						<view class="dashboard-grid">
							<view class="card panel store-panel">
								<view class="section-head">
									<view>
										<text class="section-title">店铺设置</text>
										<text class="section-subtitle">基础资料会影响消费者识别和平台审核。</text>
									</view>
									<button class="action-button compact" :loading="saving" @click="save">保存</button>
								</view>
								<view class="form-grid">
									<label v-for="field in fields" :key="field.key" class="form-field" :class="{ full: field.full }">
										<text>{{ field.label }}<text v-if="field.required" class="required">*</text></text>
										<textarea v-if="field.full" v-model.trim="form[field.key]" :placeholder="field.placeholder" />
										<input v-else v-model.trim="form[field.key]" :placeholder="field.placeholder" />
									</label>
								</view>
							</view>

							<view class="side-stack">
								<view class="card panel">
									<view class="section-head">
										<text class="section-title">待办事项</text>
									</view>
									<view class="todo-grid">
										<view v-for="item in todos" :key="item.label" class="todo-item">
											<text>{{ item.value }}</text>
											<text>{{ item.label }}</text>
										</view>
									</view>
								</view>

								<view class="card panel rating-panel">
									<view class="section-head">
										<view>
											<text class="section-title">店铺评分</text>
											<text class="section-subtitle">暂无真实评分接口，当前为展示占位。</text>
										</view>
									</view>
									<view class="rating-score">
										<text>4.8</text>
										<text>★★★★★</text>
									</view>
									<view class="rating-row">
										<text>描述相符 4.8</text>
										<text>服务态度 4.8</text>
										<text>物流服务 4.7</text>
									</view>
								</view>
							</view>
						</view>

						<view class="card panel">
							<view class="section-head">
								<view>
									<text class="section-title">数据概览</text>
									<text class="section-subtitle">近 7 天支付趋势，后续可接入真实经营数据。</text>
								</view>
							</view>
							<view class="trend-line">
								<view v-for="(point, index) in trendPoints" :key="index" class="trend-point" :style="{ height: point + 'px' }"></view>
							</view>
						</view>
					</view>

					<view v-if="activeTab === 'products'" class="console-content">
						<view class="card panel">
							<view class="section-head product-head">
								<view>
									<text class="section-title">商品管理</text>
									<text class="section-subtitle">管理商品草稿、审核、上下架和价格。</text>
								</view>
								<button class="action-button compact" @click="newProduct">发布商品</button>
							</view>
							<view class="tabs">
								<view
									v-for="item in productFilters"
									:key="item.key"
									class="tab"
									:class="{ active: productFilter === item.key }"
									@click="setProductFilter(item.key)"
								>
									{{ item.label }}
								</view>
							</view>
							<view class="product-search">
								<text>⌕</text>
								<input
									v-model="productKeyword"
									placeholder="搜索商品名称、品牌或描述"
									confirm-type="search"
									maxlength="100"
									@input="onProductKeywordInput"
									@confirm="searchProducts"
								/>
								<button v-if="productKeyword" class="secondary-button mini" @click="clearProductKeyword">清空</button>
							</view>
							<view class="table">
								<view class="table-row table-head">
									<text>商品</text>
									<text>库存</text>
									<text>状态</text>
									<text>审核备注</text>
									<text>操作</text>
								</view>
								<view v-if="productLoading && !filteredProducts.length" class="empty-inline">正在加载商品...</view>
								<view v-else-if="!filteredProducts.length" class="empty-inline">暂无商品，先发布第一件商品。</view>
								<view v-for="item in filteredProducts" :key="item.id" class="table-row product-row">
									<text class="strong">{{ item.title }}</text>
									<text>{{ item.stock || 0 }}</text>
									<text><text class="status-badge" :class="item.status">{{ productStatusText(item.status) }}</text></text>
									<text>{{ item.audit_reason || '无' }}</text>
									<view class="row-actions">
										<button class="secondary-button mini" @click="editProduct(item.id)">编辑</button>
										<button v-if="['draft','rejected','off_shelf'].includes(item.status)" class="action-button mini" @click="submit(item.id)">提交</button>
										<button v-if="item.status === 'off_shelf'" class="secondary-button mini" @click="onSale(item.id)">上架</button>
										<button v-if="item.status === 'on_sale'" class="secondary-button mini" @click="offSale(item.id)">下架</button>
										<button v-if="['on_sale','off_shelf'].includes(item.status)" class="secondary-button mini" @click="discount(item.id)">改价</button>
									</view>
								</view>
							</view>
							<view v-if="filteredProducts.length" class="load-more">
								<button v-if="hasMoreProducts" class="secondary-button compact" :loading="productLoadingMore" :disabled="productLoadingMore" @click="loadMoreProducts">
									{{ productLoadingMore ? '加载中...' : '加载更多' }}
								</button>
								<text v-else>已加载全部 {{ productTotal }} 个商品</text>
							</view>
						</view>
					</view>

					<view v-if="activeTab === 'orders'" class="console-content">
						<view class="card panel">
							<view class="section-head">
								<view>
									<text class="section-title">订单管理</text>
									<text class="section-subtitle">当前项目暂未提供商家订单接口，此处先保留后台模块入口。</text>
								</view>
							</view>
							<view class="tabs">
								<view v-for="item in orderFilters" :key="item.key" class="tab" :class="{ active: orderFilter === item.key }" @click="orderFilter = item.key">
									{{ item.label }}
								</view>
							</view>
							<view class="table">
								<view class="table-row table-head order-head">
									<text>订单号</text>
									<text>商品</text>
									<text>买家</text>
									<text>金额</text>
									<text>状态</text>
									<text>下单时间</text>
								</view>
								<view class="empty-state">
									<text>暂无订单数据</text>
									<text>后续接入 /merchants/me/orders 后可在这里展示商家订单和发货处理。</text>
								</view>
							</view>
						</view>
					</view>

					<view v-if="activeTab === 'audit'" class="console-content">
						<view class="card panel">
							<view class="section-head">
								<view>
									<text class="section-title">审核中心</text>
									<text class="section-subtitle">查看商品提交审核、审核中和驳回原因。</text>
								</view>
							</view>
							<view v-if="!auditProducts.length" class="empty-inline">暂无需要关注的审核事项</view>
							<view v-else class="data-list">
								<view v-for="item in auditProducts" :key="item.id" class="data-row">
									<view class="data-main">
										<text class="data-title">{{ item.title }}</text>
										<text class="data-meta">{{ productStatusText(item.status) }} · {{ item.audit_reason || auditHint(item.status) }}</text>
									</view>
									<text class="status-chip">{{ productStatusText(item.status) }}</text>
									<button v-if="['draft','rejected','off_shelf'].includes(item.status)" class="action-button" @click="submit(item.id)">提交审核</button>
									<button class="secondary-button" @click="editProduct(item.id)">编辑</button>
								</view>
							</view>
						</view>
					</view>

					<view v-if="activeTab === 'support'" class="console-content">
						<view class="card panel">
							<view class="section-head">
								<view>
									<text class="section-title">客服消息</text>
									<text class="section-subtitle">处理用户咨询，必要时可移交平台客服。</text>
								</view>
								<button class="secondary-button compact" @click="loadSupport">刷新</button>
							</view>
							<view class="tabs">
								<view class="tab" :class="{ active: supportFilter === 'pending' }" @click="setSupportFilter('pending')">未处理</view>
								<view class="tab" :class="{ active: supportFilter === 'resolved' }" @click="setSupportFilter('resolved')">已处理</view>
							</view>
							<view v-if="!supportConversations.length" class="empty-inline">暂无客服会话</view>
							<view v-else class="data-list">
								<view v-for="item in supportConversations" :key="item.id" class="data-row">
									<view class="data-main">
										<text class="data-title">{{ item.merchant_name || '商家客服' }} #{{ item.id }}</text>
										<text class="data-meta">{{ item.messages?.slice(-1)[0]?.content || '暂无消息' }}</text>
									</view>
									<text class="status-chip">{{ item.status === 'resolved' ? '已处理' : '未处理' }}</text>
									<button class="secondary-button" @click="openSupport(item, 'merchant')">打开</button>
									<button class="secondary-button" @click="setSupportStatus(item, item.status === 'resolved' ? 'pending' : 'resolved')">{{ item.status === 'resolved' ? '标记未处理' : '标记已处理' }}</button>
									<button v-if="!item.assigned_to_platform" class="danger-button" @click="transferSupport(item)">移交平台</button>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { merchantApi, supportApi } from '../../api'

const PRODUCT_CHANGE_STORAGE_KEY = 'merchantProductChange'

export default {
	components: { AppShell },
	data() {
		return {
			merchant: null,
			dashboard: null,
			products: [],
			productPage: 1,
			productPageSize: 20,
			productTotal: 0,
			productLoading: false,
			productLoadingMore: false,
			productKeyword: '',
			productSearchTimer: null,
			supportConversations: [],
			loading: true,
			saving: false,
			initialized: false,
			activeTab: 'home',
			productFilter: 'all',
			orderFilter: 'all',
			supportFilter: 'pending',
			form: {
				shop_name: '',
				contact_name: '',
				contact_phone: '',
				business_scope: '',
				city: '',
				address: '',
				description: ''
			},
			fields: [
				{ key: 'shop_name', label: '店铺名称', required: true, placeholder: '例如：宠爱小铺' },
				{ key: 'contact_name', label: '联系人', required: true, placeholder: '请输入联系人姓名' },
				{ key: 'contact_phone', label: '联系电话', required: true, placeholder: '请输入手机号' },
				{ key: 'business_scope', label: '经营范围', required: true, placeholder: '例如：宠物食品、用品、护理服务' },
				{ key: 'city', label: '城市', placeholder: '请输入所在城市' },
				{ key: 'address', label: '地址', placeholder: '请输入经营地址' },
				{ key: 'description', label: '店铺介绍', placeholder: '简要介绍店铺特色和服务范围', full: true }
			],
			menuItems: [
				{ key: 'home', label: '首页', icon: '⌂' },
				{ key: 'products', label: '商品管理', icon: '□' },
				{ key: 'orders', label: '订单管理', icon: '◎' },
				{ key: 'audit', label: '审核中心', icon: '✓' },
				{ key: 'support', label: '客服消息', icon: 'S' }
			],
			productFilters: [
				{ key: 'all', label: '全部' },
				{ key: 'draft', label: '草稿' },
				{ key: 'pending', label: '待审核' },
				{ key: 'on_sale', label: '已上架' },
				{ key: 'off_shelf', label: '已下架' },
				{ key: 'rejected', label: '已拒绝' }
			],
			orderFilters: [
				{ key: 'all', label: '全部' },
				{ key: 'pending_payment', label: '待付款' },
				{ key: 'pending_ship', label: '待发货' },
				{ key: 'pending_receive', label: '待收货' },
				{ key: 'completed', label: '已完成' },
				{ key: 'refund', label: '售后/退款' }
			],
			benefits: [
				{ icon: '1', title: '商品经营', desc: '发布商品、提交审核、管理上下架。' },
				{ icon: '2', title: '订单履约', desc: '集中处理订单、发货和售后状态。' },
				{ icon: '3', title: '店铺数据', desc: '查看经营概览、待办和店铺评分。' }
			],
			trendPoints: [42, 58, 54, 76, 88, 82, 104]
		}
	},
	computed: {
		canEnterBackend() {
			return this.merchant?.status === 'approved'
		},
		merchantStatusText() {
			if (!this.merchant) return '未入驻'
			const map = {
				pending: '审核中',
				rejected: '已驳回',
				frozen: '已冻结',
				approved: '已入驻'
			}
			return map[this.merchant.status] || this.merchant.status
		},
		merchantStatusClass() {
			return this.merchant?.status || 'none'
		},
		gateTitle() {
			if (!this.merchant) return '申请成为商家'
			if (this.merchant.status === 'pending') return '商家申请审核中'
			if (this.merchant.status === 'rejected') return '商家申请未通过'
			if (this.merchant.status === 'frozen') return '店铺已被冻结'
			return '申请成为商家'
		},
		gateDescription() {
			if (!this.merchant) return '填写店铺资料并提交审核，审核通过后即可进入商家后台。'
			if (this.merchant.status === 'pending') return '平台正在审核你的入驻申请，审核通过后将开放后台。'
			if (this.merchant.status === 'rejected') return '请根据审核备注修改资料，保存后等待平台重新处理。'
			if (this.merchant.status === 'frozen') return '当前店铺无法进入后台，请联系平台管理员处理。'
			return '填写店铺资料并提交审核。'
		},
		applyButtonText() {
			if (!this.merchant) return '提交入驻申请'
			if (this.merchant.status === 'pending') return '审核中'
			if (this.merchant.status === 'rejected') return '保存修改资料'
			if (this.merchant.status === 'frozen') return '已冻结'
			return '保存店铺资料'
		},
		avatarText() {
			return (this.merchant?.shop_name || '商').slice(0, 1)
		},
		filteredProducts() {
			return this.products
		},
		hasMoreProducts() {
			return this.products.length < this.productTotal
		},
		auditProducts() {
			return this.products.filter(item => ['draft', 'pending', 'rejected', 'off_shelf'].includes(item.status))
		},
		todayStats() {
			return [
				{ label: '支付金额', value: '¥ 0.00', desc: '今日实收' },
				{ label: '订单数', value: this.dashboard?.order_count || 0, desc: '今日订单' },
				{ label: '访客数', value: 0, desc: '待接入埋点' },
				{ label: '新增客户', value: 0, desc: '待接入用户统计' }
			]
		},
		todos() {
			return [
				{ label: '待发货', value: 0 },
				{ label: '待售后', value: 0 },
				{ label: '退款中', value: 0 },
				{ label: '商品待审核', value: this.dashboard?.pending_product_count || 0 }
			]
		}
	},
	onShow() {
		const change = this.consumeProductChange()
		if (!this.initialized) {
			this.load()
			return
		}
		if (change) this.handleProductChange(change)
	},
	onReachBottom() {
		if (this.activeTab === 'products') this.loadMoreProducts()
	},
	onUnload() {
		if (this.productSearchTimer) clearTimeout(this.productSearchTimer)
	},
	methods: {
		async load() {
			this.loading = true
			this.dashboard = null
			this.products = []
			this.productPage = 1
			this.productTotal = 0
			this.supportConversations = []
			try {
				this.merchant = await merchantApi.me()
				this.syncForm()
			} catch (error) {
				this.merchant = null
			}

			if (this.merchant?.status === 'approved') {
				const result = await Promise.allSettled([
					merchantApi.dashboard(),
					merchantApi.products(this.productQueryParams(1)),
					supportApi.merchantList({ status: this.supportFilter, page: 1, page_size: 100 })
				])
				if (result[0].status === 'fulfilled') this.dashboard = result[0].value
				if (result[1].status === 'fulfilled') this.applyProductPage(result[1].value, true)
				if (result[2].status === 'fulfilled') this.supportConversations = result[2].value?.items || []
			}
			this.loading = false
			this.initialized = true
		},
		setActiveTab(tab) {
			this.activeTab = tab
			if (tab === 'products' && !this.products.length && !this.productLoading) {
				this.loadProducts(true)
			}
		},
		async setProductFilter(filter) {
			if (this.productFilter === filter) return
			this.productFilter = filter
			await this.loadProducts(true)
		},
		productQueryParams(page) {
			const keyword = this.productKeyword.trim()
			return {
				page,
				page_size: this.productPageSize,
				status: this.productFilter === 'all' ? undefined : this.productFilter,
				keyword: keyword || undefined
			}
		},
		applyProductPage(result, reset = false) {
			const items = result?.items || []
			this.products = reset ? items : this.products.concat(items)
			this.productPage = result?.page || (reset ? 1 : this.productPage)
			this.productTotal = result?.total || 0
		},
		async loadProducts(reset = false) {
			if (!this.merchant || this.merchant.status !== 'approved') return
			if (this.productLoading || this.productLoadingMore) return
			const nextPage = reset ? 1 : this.productPage + 1
			if (!reset && !this.hasMoreProducts) return
			if (reset) this.productLoading = true
			else this.productLoadingMore = true
			try {
				const result = await merchantApi.products(this.productQueryParams(nextPage))
				this.applyProductPage(result, reset)
			} finally {
				this.productLoading = false
				this.productLoadingMore = false
			}
		},
		loadMoreProducts() {
			return this.loadProducts(false)
		},
		onProductKeywordInput() {
			if (this.productSearchTimer) clearTimeout(this.productSearchTimer)
			this.productSearchTimer = setTimeout(() => {
				this.loadProducts(true)
			}, 300)
		},
		searchProducts() {
			if (this.productSearchTimer) {
				clearTimeout(this.productSearchTimer)
				this.productSearchTimer = null
			}
			return this.loadProducts(true)
		},
		clearProductKeyword() {
			if (!this.productKeyword) return
			this.productKeyword = ''
			return this.searchProducts()
		},
		async loadSupport() {
			const result = await supportApi.merchantList({ status: this.supportFilter, page: 1, page_size: 100 })
			this.supportConversations = result.items || []
		},
		async setSupportFilter(status) {
			this.supportFilter = status
			await this.loadSupport()
		},
		openSupport(item, role) {
			uni.navigateTo({ url: `/pages/support/merchant?id=${item.id}&role=${role}` })
		},
		async setSupportStatus(item, status) {
			await supportApi.merchantStatus(item.id, status)
			uni.showToast({ title: status === 'resolved' ? '已标记处理' : '已标记未处理' })
			this.loadSupport()
		},
		async transferSupport(item) {
			await supportApi.merchantTransfer(item.id)
			uni.showToast({ title: '已移交平台客服' })
			this.loadSupport()
		},
		syncForm() {
			Object.keys(this.form).forEach(key => {
				this.form[key] = this.merchant?.[key] || ''
			})
		},
		validateForm() {
			if (['shop_name', 'contact_name', 'contact_phone', 'business_scope'].some(key => !this.form[key])) {
				uni.showToast({ title: '请填写必填资料', icon: 'none' })
				return false
			}
			return true
		},
		async save() {
			if (!this.validateForm()) return
			if (this.merchant?.status === 'pending' || this.merchant?.status === 'frozen') return

			this.saving = true
			try {
				if (this.merchant) {
					await merchantApi.update(this.form)
					uni.showToast({ title: '店铺资料已保存' })
				} else {
					await merchantApi.apply({ ...this.form, qualifications: [] })
					uni.showToast({ title: '入驻申请已提交' })
				}
				this.load()
			} catch (error) {
			} finally {
				this.saving = false
			}
		},
		productStatusText(status) {
			const map = {
				draft: '草稿',
				pending: '待审核',
				on_sale: '已上架',
				off_shelf: '已下架',
				rejected: '已拒绝'
			}
			return map[status] || status || '未知'
		},
		auditHint(status) {
			const map = {
				draft: '草稿商品尚未提交平台审核',
				pending: '平台正在审核，请等待结果',
				off_shelf: '商品当前已下架，可修改后重新提交',
				rejected: '请根据审核备注修改后重新提交'
			}
			return map[status] || '暂无备注'
		},
		productMatchesCurrentView(product) {
			if (this.productFilter !== 'all' && product.status !== this.productFilter) return false
			const keyword = this.productKeyword.trim().toLowerCase()
			if (!keyword) return true
			return [product.title, product.brand, product.description]
				.some(value => String(value || '').toLowerCase().includes(keyword))
		},
		upsertProductRow(product) {
			const index = this.products.findIndex(item => item.id === product.id)
			if (!this.productMatchesCurrentView(product)) {
				if (index !== -1) {
					this.products.splice(index, 1)
					this.productTotal = Math.max(this.productTotal - 1, 0)
				}
				return
			}
			if (index === -1) {
				this.products.unshift(product)
				this.productTotal += 1
				return
			}
			this.products.splice(index, 1, { ...this.products[index], ...product })
		},
		applyProductPatch(id, patch) {
			const current = this.products.find(item => item.id === id)
			if (!current) return
			this.upsertProductRow({ ...current, ...patch })
		},
		async refreshProductRow(id, fallback = {}) {
			try {
				const response = await merchantApi.product(id)
				if (response?.product) {
					this.upsertProductRow({ ...fallback, ...response.product })
					return
				}
			} catch (error) {}
			if (Object.keys(fallback).length) this.applyProductPatch(id, fallback)
		},
		consumeProductChange() {
			try {
				const change = uni.getStorageSync(PRODUCT_CHANGE_STORAGE_KEY)
				if (change) uni.removeStorageSync(PRODUCT_CHANGE_STORAGE_KEY)
				return change?.id ? change : null
			} catch (error) {
				return null
			}
		},
		handleProductChange(change) {
			return this.refreshProductRow(change.id)
		},
		newProduct() {
			uni.navigateTo({ url: '/pages/merchant/product-edit' })
		},
		editProduct(id) {
			uni.navigateTo({ url: `/pages/merchant/product-edit?id=${id}` })
		},
		async submit(id) {
			try {
				const result = await merchantApi.submitProduct(id, {})
				uni.showToast({ title: '商品已提交审核' })
				this.applyProductPatch(id, { status: result.status, audit_reason: null })
			} catch (error) {}
		},
		async onSale(id) {
			try {
				const result = await merchantApi.putProductOnSale(id, {})
				uni.showToast({ title: '商品已上架' })
				this.applyProductPatch(id, { status: result.status })
			} catch (error) {}
		},
		async offSale(id) {
			try {
				const result = await merchantApi.takeProductOffSale(id, {})
				uni.showToast({ title: '商品已下架' })
				this.applyProductPatch(id, { status: result.status })
			} catch (error) {}
		},
		discount(id) {
			uni.showModal({
				title: '设置 SKU 价格',
				editable: true,
				placeholderText: 'JSON，例如 {"12":9900}',
				success: async result => {
					if (!result.confirm) return
					try {
						const response = await merchantApi.setProductDiscount(id, { sku_prices: JSON.parse(result.content) })
						uni.showToast({ title: '价格已更新' })
						await this.refreshProductRow(id, { status: response.status })
					} catch (error) {
						if (error instanceof SyntaxError) {
							uni.showToast({ title: 'JSON 格式错误', icon: 'none' })
						}
					}
				}
			})
		}
	}
}
</script>

<style scoped lang="scss">
.merchant-page { min-height: calc(100vh - var(--header-height)); background: #fffaf5; }
.loading-card { padding: 26px; color: var(--color-text-secondary); }
.apply-page { max-width: 1180px; }
.apply-hero {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 20px;
	margin-bottom: 18px;
	padding: 28px 4px 8px;
}
.apply-kicker, .apply-title, .apply-desc { display: block; }
.apply-kicker { color: var(--color-primary); font-size: 12px; font-weight: 800; text-transform: uppercase; }
.apply-title { margin-top: 8px; color: var(--color-text); font-size: 30px; font-weight: 900; }
.apply-desc { margin-top: 8px; color: var(--color-text-secondary); font-size: 14px; }
.apply-status {
	display: flex;
	min-width: 88px;
	height: 34px;
	align-items: center;
	justify-content: center;
	border-radius: 18px;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 13px;
	font-weight: 800;
}
.apply-status.pending { background: #fff7df; color: var(--color-warning); }
.apply-status.rejected, .apply-status.frozen { background: #fff0f0; color: var(--color-danger); }
.apply-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; }
.apply-form-card, .apply-side-card, .panel { padding: 22px; }
.section-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 18px;
}
.section-title, .section-subtitle { display: block; }
.section-title { color: var(--color-text); font-size: 18px; font-weight: 900; }
.section-subtitle { margin-top: 5px; color: var(--color-text-secondary); font-size: 12px; }
.required { margin-left: 2px; color: var(--color-danger); }
.audit-note {
	margin-top: 14px;
	padding: 12px 14px;
	border-radius: 8px;
	background: #fff7df;
	color: var(--color-warning);
	font-size: 12px;
}
.button-row { display: flex; justify-content: flex-end; margin-top: 18px; }
.benefit-list { display: grid; gap: 14px; margin-top: 18px; }
.benefit-item { display: flex; gap: 12px; align-items: flex-start; }
.benefit-icon {
	display: flex;
	width: 28px;
	height: 28px;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	border-radius: 50%;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 13px;
	font-weight: 800;
}
.benefit-item text { display: block; }
.benefit-item view text:first-child { color: var(--color-text); font-size: 14px; font-weight: 800; }
.benefit-item view text:last-child { margin-top: 4px; color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; }

.merchant-console {
	display: grid;
	grid-template-columns: 220px minmax(0, 1fr);
	min-height: calc(100vh - var(--header-height));
	background: #fffaf5;
}
.merchant-sidebar {
	position: sticky;
	top: var(--header-height);
	height: calc(100vh - var(--header-height));
	padding: 20px 14px;
	border-right: 1px solid var(--color-border);
	background: rgba(255,255,255,.9);
}
.merchant-brand { display: flex; align-items: center; gap: 11px; padding: 8px 8px 20px; }
.brand-mark {
	display: flex;
	width: 42px;
	height: 42px;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	background: var(--color-primary);
	color: #fff;
	font-size: 18px;
	font-weight: 900;
}
.merchant-brand text { display: block; }
.merchant-brand text:first-child { max-width: 130px; overflow: hidden; color: var(--color-text); font-size: 15px; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }
.merchant-brand text:last-child { margin-top: 3px; color: var(--color-text-secondary); font-size: 11px; }
.sidebar-menu { display: grid; gap: 4px; }
.sidebar-item {
	display: flex;
	align-items: center;
	gap: 10px;
	height: 42px;
	padding: 0 12px;
	border-radius: 8px;
	color: var(--color-text-secondary);
	font-size: 14px;
	cursor: pointer;
}
.sidebar-item.active { background: var(--color-primary-soft); color: var(--color-primary); font-weight: 800; }
.console-main { min-width: 0; padding: 0 24px 28px; }
.console-topbar {
	position: sticky;
	top: var(--header-height);
	z-index: 8;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	min-height: 72px;
	padding: 14px 0;
	background: rgba(255,250,245,.94);
	backdrop-filter: blur(8px);
}
.welcome, .topbar-subtitle { display: block; }
.welcome { color: var(--color-text); font-size: 18px; font-weight: 900; }
.topbar-subtitle { margin-top: 5px; color: var(--color-text-secondary); font-size: 12px; }
.topbar-actions { display: flex; align-items: center; gap: 10px; }
.topbar-pill {
	height: 32px;
	padding: 0 13px;
	border: 1px solid var(--color-border);
	border-radius: 17px;
	background: #fff;
	color: var(--color-text-secondary);
	font-size: 12px;
	line-height: 32px;
}
.avatar {
	display: flex;
	width: 34px;
	height: 34px;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	background: #2d2926;
	color: #fff;
	font-size: 13px;
	font-weight: 900;
}
.console-content { max-width: 1280px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 14px; }
.summary-card { padding: 18px; }
.summary-card text { display: block; }
.summary-card text:first-child { color: var(--color-text-secondary); font-size: 12px; }
.summary-card text:nth-child(2) { margin-top: 10px; color: var(--color-text); font-size: 24px; font-weight: 900; }
.summary-card text:last-child { margin-top: 6px; color: var(--color-success); font-size: 11px; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 14px; margin-bottom: 14px; }
.side-stack { display: grid; gap: 14px; align-content: start; }
.compact { min-width: 86px; height: 34px; padding: 0 14px; font-size: 12px; line-height: 34px; }
.todo-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.todo-item { padding: 14px; border-radius: 8px; background: #fff8f1; }
.todo-item text { display: block; }
.todo-item text:first-child { color: var(--color-text); font-size: 24px; font-weight: 900; }
.todo-item text:last-child { margin-top: 5px; color: var(--color-text-secondary); font-size: 12px; }
.rating-score { display: flex; align-items: center; gap: 10px; color: var(--color-primary); }
.rating-score text:first-child { font-size: 28px; font-weight: 900; }
.rating-score text:last-child { letter-spacing: 0; font-size: 15px; }
.rating-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; color: var(--color-text-secondary); font-size: 12px; }
.trend-line {
	display: flex;
	align-items: flex-end;
	gap: 18px;
	height: 140px;
	padding: 18px 10px 4px;
	border-radius: 8px;
	background: linear-gradient(180deg, #fff, #fff8f1);
}
.trend-point { width: 100%; border-radius: 8px 8px 0 0; background: #67a6f4; }
.product-head { align-items: flex-start; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.tab {
	height: 32px;
	padding: 0 14px;
	border: 1px solid var(--color-border);
	border-radius: 17px;
	background: #fff;
	color: var(--color-text-secondary);
	font-size: 12px;
	line-height: 32px;
	cursor: pointer;
}
.tab.active { border-color: var(--color-primary); background: var(--color-primary-soft); color: var(--color-primary); font-weight: 800; }
.product-search {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 14px;
	padding: 9px 12px;
	border: 1px solid var(--color-border);
	border-radius: 8px;
	background: #fff;
}
.product-search > text { color: var(--color-text-secondary); font-size: 14px; }
.product-search input { min-width: 0; flex: 1; font-size: 13px; }
.table { overflow-x: auto; }
.table-row {
	display: grid;
	grid-template-columns: minmax(220px, 1.5fr) 90px 110px minmax(160px, 1fr) 280px;
	align-items: center;
	gap: 12px;
	min-width: 900px;
	padding: 13px 10px;
	border-bottom: 1px solid var(--color-border);
	color: var(--color-text-secondary);
	font-size: 12px;
}
.table-head { border-radius: 8px; border-bottom: 0; background: #fff8f1; color: var(--color-text); font-weight: 800; }
.order-head { grid-template-columns: 150px minmax(180px, 1fr) 100px 100px 110px 150px; }
.strong { color: var(--color-text); font-weight: 800; }
.status-badge {
	display: inline-flex;
	height: 24px;
	align-items: center;
	padding: 0 9px;
	border-radius: 13px;
	background: #f4f0eb;
	color: var(--color-text-secondary);
	font-size: 11px;
}
.status-badge.pending { background: #fff7df; color: var(--color-warning); }
.status-badge.on_sale { background: #eaf8f0; color: var(--color-success); }
.status-badge.rejected { background: #fff0f0; color: var(--color-danger); }
.row-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.mini { min-width: 54px; height: 28px; padding: 0 10px; border-radius: 8px; font-size: 11px; line-height: 28px; }
.load-more {
	display: flex;
	justify-content: center;
	padding: 16px 0 2px;
	color: var(--color-text-secondary);
	font-size: 12px;
}
.empty-inline, .empty-state {
	padding: 28px;
	color: var(--color-text-secondary);
	font-size: 13px;
	text-align: center;
}
.empty-state { display: grid; gap: 8px; min-width: 760px; }
.empty-state text:first-child { color: var(--color-text); font-size: 16px; font-weight: 900; }

@media (max-width: 900px) {
	.merchant-console { display: block; padding-bottom: var(--bottom-nav-height); }
	.merchant-sidebar {
		position: static;
		height: auto;
		padding: 12px;
		border-right: 0;
		border-bottom: 1px solid var(--color-border);
	}
	.merchant-brand { padding-bottom: 12px; }
	.sidebar-menu { display: flex; overflow-x: auto; }
	.sidebar-item { flex: 0 0 auto; }
	.console-main { padding: 0 12px 22px; }
	.console-topbar { position: static; align-items: flex-start; }
	.topbar-actions { display: none; }
	.summary-grid, .dashboard-grid, .apply-grid { grid-template-columns: 1fr; }
	.apply-hero { align-items: flex-start; flex-direction: column; }
	.apply-title { font-size: 25px; }
	.table-row { min-width: 840px; }
}

@media (max-width: 640px) {
	.summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.apply-form-card, .apply-side-card, .panel { padding: 16px; }
	.section-head { align-items: flex-start; flex-direction: column; }
	.button-row { justify-content: stretch; }
	.button-row .action-button { width: 100%; }
}
</style>
