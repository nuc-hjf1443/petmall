<template>
	<view class="admin-shell">
		<view class="admin-bar">
			<view>
				<text class="brand">PetMall Admin</text>
				<text class="sub">审核与平台治理中心</text>
			</view>
			<view class="admin-actions">
				<text>{{ admin.nickname || admin.phone }}</text>
				<button class="secondary-button" @click="logout">退出</button>
			</view>
		</view>

		<view class="admin-layout">
			<view class="sidebar">
				<view
					v-for="item in tabs"
					:key="item.key"
					:class="{ active: tab === item.key }"
					@click="tab = item.key"
				>
					<text>{{ item.icon }}</text>{{ item.label }}
				</view>
				<view @click="home"><text>←</text>返回用户端</view>
			</view>

			<scroll-view scroll-y class="workspace">
				<view class="workspace-inner">
					<view class="page-heading">
						<view>
							<text class="page-title">{{ activeTab.label }}</text>
							<text class="page-subtitle">{{ activeTab.desc }}</text>
						</view>
						<button class="secondary-button" :loading="loading" @click="loadAll">刷新数据</button>
					</view>

					<view v-if="loading" class="card empty-inline">正在加载后台数据...</view>

					<template v-else-if="tab === 'dashboard'">
						<view class="metric-grid">
							<view v-for="m in metrics" :key="m.label" class="card metric">
								<text>{{ m.value }}</text>
								<text>{{ m.label }}</text>
							</view>
						</view>
						<view class="content-grid overview">
							<view class="card panel">
								<text class="panel-title">待办提醒</text>
								<view class="data-list">
									<view class="data-row"><text class="data-main">待审核商品</text><text class="status-chip">{{ products.length }}</text></view>
									<view class="data-row"><text class="data-main">待审核商家</text><text class="status-chip">{{ merchants.length }}</text></view>
									<view class="data-row"><text class="data-main">领养申请</text><text class="status-chip">{{ adoptions.length }}</text></view>
									<view class="data-row"><text class="data-main">提现申请</text><text class="status-chip">{{ pendingWithdrawals.length }}</text></view>
									<view class="data-row"><text class="data-main">内容举报</text><text class="status-chip">{{ pendingReports.length }}</text></view>
								</view>
							</view>
							<view class="card panel">
								<text class="panel-title">经营概览</text>
								<view class="data-list">
									<view class="data-row"><text class="data-main">GMV</text><text class="status-chip">{{ money(overview.gmv) }}</text></view>
									<view class="data-row"><text class="data-main">订单总数</text><text class="status-chip">{{ overview.order_count || 0 }}</text></view>
									<view class="data-row"><text class="data-main">已支付订单</text><text class="status-chip">{{ overview.paid_order_count || 0 }}</text></view>
									<view class="data-row"><text class="data-main">宠物档案</text><text class="status-chip">{{ overview.pet_count || 0 }}</text></view>
								</view>
							</view>
						</view>
					</template>

					<view v-else-if="tab === 'users'" class="card panel">
						<text class="panel-title">平台用户</text>
						<StatePanel v-if="!users.length" icon="-" title="暂无用户数据" />
						<view v-else class="data-list">
							<view v-for="item in users" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.nickname || item.phone }}</text>
									<text class="data-meta">{{ item.phone }} · {{ item.is_admin ? '管理员' : '普通用户' }} · {{ item.is_merchant ? '商家' : '非商家' }}</text>
								</view>
								<text class="status-chip">{{ item.is_frozen ? '已冻结' : '正常' }}</text>
								<button v-if="item.is_frozen" class="secondary-button" @click="unfreeze(item)">解冻</button>
								<button v-else class="danger-button" @click="freeze(item)">冻结</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'products'" class="card panel">
						<text class="panel-title">商品管理</text>
						<StatePanel v-if="!products.length && !saleProducts.length" icon="-" title="暂无商品数据" />
						<view v-if="products.length" class="section-block">
							<text class="section-title">待审核商品</text>
							<view class="data-list">
							<view v-for="item in products" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.title }}</text>
									<text class="data-meta">商家 {{ item.merchant_id }} · 库存 {{ item.stock }} · SKU {{ item.skus?.length || 0 }} · {{ item.status }}</text>
								</view>
								<button v-if="item.status === 'pending'" class="action-button" @click="approveProduct(item)">通过</button>
								<button v-if="item.status === 'pending'" class="danger-button" @click="rejectProduct(item)">驳回</button>
								<button v-if="item.status === 'on_sale'" class="danger-button" @click="offSaleProduct(item)">强制下架</button>
							</view>
							</view>
						</view>
						<view v-if="saleProducts.length" class="section-block">
							<text class="section-title">在售商品</text>
							<view class="data-list">
								<view v-for="item in saleProducts" :key="`sale-${item.id}`" class="data-row">
									<view class="data-main">
										<text class="data-title">{{ item.title }}</text>
										<text class="data-meta">商家 {{ item.merchant_id }} · 库存 {{ item.stock }} · {{ money(item.price) }}</text>
									</view>
									<button class="danger-button" @click="offSaleProduct(item)">强制下架</button>
								</view>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'pets'" class="card panel">
						<text class="panel-title">全平台宠物</text>
						<StatePanel v-if="!pets.length" icon="-" title="暂无宠物档案" />
						<view v-else class="data-list">
							<view v-for="item in pets" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.name }} · {{ item.pet_type }}</text>
									<text class="data-meta">用户 {{ item.owner_phone }} · 品种 {{ item.breed || '未填写' }} · 完整度 {{ item.profile_completeness ?? 0 }}%</text>
								</view>
								<text class="status-chip">{{ item.is_deleted ? '已删除' : '正常' }}</text>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'orders'" class="card panel">
						<text class="panel-title">全平台订单</text>
						<StatePanel v-if="!orders.length" icon="-" title="暂无订单数据" />
						<view v-else class="data-list">
							<view v-for="item in orders" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.order_no }} · {{ money(item.pay_amount) }}</text>
									<text class="data-meta">用户 {{ item.user_phone || item.user_id }} · 商家 {{ item.merchant_name || item.merchant_id }} · {{ item.status }} · 支付 {{ item.payment_status || '无' }}</text>
								</view>
								<text class="status-chip">{{ item.status }}</text>
								<button v-if="canForceCancel(item)" class="danger-button" @click="forceCancelOrder(item)">强制取消</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'merchants'" class="card panel">
						<text class="panel-title">待审核商家</text>
						<StatePanel v-if="!merchants.length" icon="-" title="没有待审核商家" />
						<view v-else class="data-list">
							<view v-for="item in merchants" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.shop_name }}</text>
									<text class="data-meta">{{ item.contact_name }} · {{ item.contact_phone }} · {{ item.business_scope }}</text>
								</view>
								<button class="action-button" @click="approveMerchant(item)">通过</button>
								<button class="danger-button" @click="rejectMerchant(item)">驳回</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'content'" class="card panel">
						<text class="panel-title">内容举报</text>
						<StatePanel v-if="!reports.length" icon="-" title="没有内容举报" />
						<view v-else class="data-list">
							<view v-for="item in reports" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.target_user_nickname || '未设置昵称' }} · {{ item.target_user_phone || '手机号未知' }}</text>
									<text class="data-meta">来源 {{ reportSourceLabel(item) }} · {{ reportStatusLabel(item) }}</text>
								</view>
								<text v-if="item.status !== 'pending'" class="status-chip">{{ reportActionLabel(item) }}</text>
								<button class="secondary-button" @click="showReportDetail(item)">查看详情</button>
								<button v-if="item.status === 'pending'" class="secondary-button" @click="resolveReport(item, 'dismiss')">驳回举报</button>
								<button v-if="item.status === 'pending'" class="danger-button" @click="resolveReport(item, 'take_down')">下架内容</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'adoptions'" class="card panel">
						<text class="panel-title">领养申请审核</text>
						<StatePanel v-if="!adoptions.length" icon="-" title="没有待审核领养申请" />
						<view v-else class="data-list">
							<view v-for="item in adoptions" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.contact_name }} · {{ item.contact_phone }}</text>
									<text class="data-meta">{{ item.living_city }} · {{ item.living_condition }} · {{ item.reason }}</text>
								</view>
								<text class="status-chip">{{ item.status }}</text>
								<button v-if="item.status === 'pending'" class="action-button" @click="approveAdoption(item)">通过</button>
								<button v-if="item.status === 'pending'" class="danger-button" @click="rejectAdoption(item)">驳回</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'withdrawals'" class="card panel">
						<text class="panel-title">提现审核</text>
						<StatePanel v-if="!withdrawals.length" icon="-" title="没有提现申请" />
						<view v-else class="data-list">
							<view v-for="item in withdrawals" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.withdrawal_no }} · {{ money(item.amount) }}</text>
									<text class="data-meta">用户 {{ item.user_id }} · {{ item.account_name }} · {{ item.alipay_account }} · {{ item.status }}</text>
								</view>
								<text class="status-chip">{{ withdrawalStatus(item.status) }}</text>
								<button v-if="item.status === 'pending'" class="action-button" @click="approveWithdrawal(item)">通过</button>
								<button v-if="item.status === 'pending'" class="danger-button" @click="rejectWithdrawal(item)">驳回</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'knowledge'" class="card panel">
						<view class="panel-heading">
							<view>
								<text class="panel-title">平台知识库文件</text>
								<text class="data-meta">用于没有私人知识库时的默认问答资料，也会与私人知识联合检索</text>
							</view>
							<button class="action-button" @click="choosePlatformKnowledgeDocument">上传文件</button>
						</view>
						<StatePanel v-if="!platformDocuments.length" icon="-" title="暂无平台知识文件" />
						<view v-else class="data-list">
							<view v-for="item in platformDocuments" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.file_name }}</text>
									<text class="data-meta">{{ item.file_type }} · {{ item.parse_status }} · {{ item.chunk_count }} 个分块 · v{{ item.index_version }}</text>
									<text v-if="item.error_message" class="error-text">{{ item.error_message }}</text>
								</view>
								<text class="status-chip">{{ item.source_type }}</text>
								<button class="secondary-button" @click="choosePlatformKnowledgeReplacement(item)">替换</button>
								<button class="secondary-button" @click="reindexPlatformKnowledge(item)">重建索引</button>
								<button class="danger-button" @click="deletePlatformKnowledge(item)">删除</button>
							</view>
						</view>
					</view>

					<view v-else-if="tab === 'support'" class="card panel support-panel">
						<view class="panel-heading">
							<view>
								<text class="panel-title">平台客服</text>
								<text class="data-meta">处理用户平台咨询，以及商家移交给平台的客服会话。</text>
							</view>
							<button class="secondary-button" @click="loadSupport">刷新</button>
						</view>
						<view class="support-tabs">
							<view class="support-tab" :class="{ active: supportFilter === 'pending' }" @click="setSupportFilter('pending')">未处理</view>
							<view class="support-tab" :class="{ active: supportFilter === 'resolved' }" @click="setSupportFilter('resolved')">已处理</view>
						</view>
						<StatePanel v-if="!supportConversations.length" icon="-" title="暂无客服会话" />
						<view v-else class="support-list">
							<view v-for="item in supportConversations" :key="item.id" class="support-row">
								<view class="support-main">
									<text class="data-title">{{ supportTitle(item) }}</text>
									<text class="data-meta">{{ item.messages?.slice(-1)[0]?.content || '暂无消息' }}</text>
								</view>
								<view class="support-actions">
									<text class="status-chip" :class="{ resolved: item.status === 'resolved' }">{{ item.status === 'resolved' ? '已处理' : '未处理' }}</text>
									<button class="secondary-button" @click="openSupport(item)">打开</button>
									<button class="secondary-button" @click="setSupportStatus(item, item.status === 'resolved' ? 'pending' : 'resolved')">{{ item.status === 'resolved' ? '标记未处理' : '标记已处理' }}</button>
								</view>
							</view>
						</view>
					</view>
				</view>
			</scroll-view>
		</view>
	</view>
</template>

<script>
import StatePanel from '../../components/StatePanel.vue'
import { adminApi, productApi, supportApi, userApi, walletApi, clearTokens } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { StatePanel },
	data() {
		return {
			tab: 'dashboard',
			loading: true,
			admin: {},
			users: [],
			products: [],
			saleProducts: [],
			pets: [],
			orders: [],
			overview: {},
			merchants: [],
			reports: [],
			adoptions: [],
			withdrawals: [],
			platformKnowledge: null,
			platformDocuments: [],
			supportConversations: [],
			supportFilter: 'pending',
			tabs: [
				{ key: 'dashboard', icon: 'D', label: '数据面板', desc: '平台待办和经营概览' },
				{ key: 'users', icon: 'U', label: '用户管理', desc: '账号状态与冻结管理' },
				{ key: 'products', icon: 'P', label: '商品管理', desc: '商品审核与强制下架' },
				{ key: 'pets', icon: 'A', label: '宠物管理', desc: '全平台宠物档案' },
				{ key: 'orders', icon: 'O', label: '订单管理', desc: '全平台订单与强制取消' },
				{ key: 'merchants', icon: 'M', label: '商家审核', desc: '审核商家入驻申请' },
				{ key: 'content', icon: 'C', label: '内容审核', desc: '处理社区内容举报' },
				{ key: 'adoptions', icon: 'R', label: '领养审核', desc: '审核用户领养申请' },
				{ key: 'withdrawals', icon: 'W', label: '提现审核', desc: '模拟打款与余额扣减审核' },
				{ key: 'support', icon: 'S', label: '平台客服', desc: '处理平台客服与商家移交会话' },
				{ key: 'knowledge', icon: 'K', label: '知识库', desc: '平台知识文件与索引维护' }
			]
		}
	},
	computed: {
		activeTab() {
			return this.tabs.find(v => v.key === this.tab) || this.tabs[0]
		},
		metrics() {
			return [
				{ label: '平台用户', value: this.users.length },
				{ label: '宠物档案', value: this.overview.pet_count || this.pets.length },
				{ label: '订单总数', value: this.overview.order_count || this.orders.length },
				{ label: 'GMV', value: this.money(this.overview.gmv) },
				{ label: '提现申请', value: this.pendingWithdrawals.length }
			]
		},
		pendingWithdrawals() {
			return this.withdrawals.filter(item => item.status === 'pending')
		},
		pendingReports() {
			return this.reports.filter(item => item.status === 'pending')
		}
	},
	onLoad() {
		this.loadAll()
	},
	methods: {
		money(value) {
			return formatMoney(value)
		},
		canForceCancel(order) {
			return !['cancelled', 'completed', 'refunded', 'after_sale'].includes(order.status)
		},
		async loadAll() {
			this.loading = true
			try {
				this.admin = await userApi.me()
				if (!this.admin.is_admin) {
					uni.showToast({ title: '您还不是管理员,拒绝访问!', icon: 'none' })
					setTimeout(() => uni.reLaunch({ url: '/pages/profile/index' }), 800)
					return
				}
			} catch (e) {
				this.loading = false
				return
			}

			const result = await Promise.allSettled([
				adminApi.users(),
				adminApi.pendingProducts({ page: 1, page_size: 100 }),
				adminApi.pendingMerchants(),
				adminApi.reports({ page: 1, page_size: 100 }),
				adminApi.adoptionApplications({}),
				adminApi.pets({ page: 1, page_size: 100 }),
				adminApi.orders({ page: 1, page_size: 100 }),
				adminApi.statisticsOverview(),
				productApi.list({ page: 1, page_size: 100 }),
				walletApi.adminWithdrawals({ page: 1, page_size: 100 }),
				adminApi.platformKnowledge(),
				adminApi.platformKnowledgeDocuments(),
				supportApi.adminList({ status: this.supportFilter, page: 1, page_size: 100 })
			])
			if (result[0].status === 'fulfilled') this.users = result[0].value || []
			if (result[1].status === 'fulfilled') this.products = result[1].value?.items || []
			if (result[2].status === 'fulfilled') this.merchants = result[2].value || []
			if (result[3].status === 'fulfilled') this.reports = result[3].value?.items || []
			if (result[4].status === 'fulfilled') this.adoptions = result[4].value || []
			if (result[5].status === 'fulfilled') this.pets = result[5].value?.items || []
			if (result[6].status === 'fulfilled') this.orders = result[6].value?.items || []
			if (result[7].status === 'fulfilled') this.overview = result[7].value || {}
			if (result[8].status === 'fulfilled') this.saleProducts = result[8].value?.items || []
			if (result[9].status === 'fulfilled') this.withdrawals = result[9].value?.items || []
			if (result[10].status === 'fulfilled') this.platformKnowledge = result[10].value || null
			if (result[11].status === 'fulfilled') this.platformDocuments = result[11].value || []
			if (result[12].status === 'fulfilled') this.supportConversations = result[12].value?.items || []
			this.loading = false
		},
		async loadSupport() {
			const result = await supportApi.adminList({ status: this.supportFilter, page: 1, page_size: 100 })
			this.supportConversations = result.items || []
		},
		async setSupportFilter(status) {
			this.supportFilter = status
			await this.loadSupport()
		},
		supportTitle(item) {
			if (item.type === 'merchant') return `${item.merchant_name || '商家客服'} #${item.id}`
			if (item.type === 'adoption') return `${item.adoption_pet_name || '领养沟通'} #${item.id}`
			return `平台客服 #${item.id}`
		},
		openSupport(item) {
			uni.navigateTo({ url: `/pages/support/platform?id=${item.id}&role=admin` })
		},
		async setSupportStatus(item, status) {
			await supportApi.adminStatus(item.id, status)
			uni.showToast({ title: status === 'resolved' ? '已标记处理' : '已标记未处理' })
			this.loadSupport()
		},
		chooseFile(callback) {
			const done = res => {
				const path = res.tempFiles?.[0]?.path || res.tempFilePaths?.[0]
				if (path) callback(path)
			}
			if (uni.chooseFile) uni.chooseFile({ count: 1, success: done })
			else uni.chooseMessageFile({ count: 1, type: 'file', success: done })
		},
		choosePlatformKnowledgeDocument() {
			this.chooseFile(async filePath => {
				await adminApi.uploadPlatformKnowledgeDocument(filePath)
				uni.showToast({ title: '平台知识文件已提交解析' })
				this.loadAll()
			})
		},
		choosePlatformKnowledgeReplacement(item) {
			this.chooseFile(async filePath => {
				await adminApi.replacePlatformKnowledgeDocument(item.id, filePath)
				uni.showToast({ title: '平台知识文件已替换' })
				this.loadAll()
			})
		},
		async reindexPlatformKnowledge(item) {
			await adminApi.reindexPlatformKnowledgeDocument(item.id)
			uni.showToast({ title: '已提交重建索引' })
			this.loadAll()
		},
		deletePlatformKnowledge(item) {
			uni.showModal({
				title: '删除平台知识文件',
				content: `确定删除 ${item.file_name} 吗？`,
				success: async result => {
					if (!result.confirm) return
					await adminApi.deletePlatformKnowledgeDocument(item.id)
					uni.showToast({ title: '删除任务已提交' })
					this.loadAll()
				}
			})
		},
		withdrawalStatus(status) {
			return { pending: '待审核', approved: '已通过', rejected: '已驳回' }[status] || status
		},
		reportActionLabel(item) {
			if (item.status === 'pending') return '待处理'
			return { dismiss: '已驳回举报', take_down: '已下架内容' }[item.action] || '已处理'
		},
		reportStatusLabel(item) {
			return item.status === 'pending' ? '待处理' : this.reportActionLabel(item)
		},
		reportSourceLabel(item) {
			return {
				community_post: '社区动态',
				community_comment: '社区评论',
				post: '社区动态',
				comment: '社区评论'
			}[item.source_area || item.target_type] || '未知区域'
		},
		showReportDetail(item) {
			const user = `${item.target_user_nickname || '未设置昵称'} / ${item.target_user_phone || '手机号未知'}`
			const content = item.target_content || '无文本内容'
			uni.showModal({
				title: '举报详情',
				content: `来源：${this.reportSourceLabel(item)}\n被举报人：${user}\n举报原因：${item.reason || '未填写'}\n举报内容：${content}`,
				showCancel: false
			})
		},
		reason(title, callback, required = false) {
			uni.showModal({
				title,
				editable: true,
				placeholderText: required ? '请输入原因' : '备注，可选',
				success: result => {
					if (result.confirm && (!required || result.content)) callback(result.content || null)
					else if (result.confirm) uni.showToast({ title: '请输入原因', icon: 'none' })
				}
			})
		},
		freeze(item) {
			this.reason('冻结用户', async reason => {
				await adminApi.freezeUser(item.id, { reason })
				uni.showToast({ title: '用户已冻结' })
				this.loadAll()
			}, true)
		},
		unfreeze(item) {
			this.reason('解冻用户', async reason => {
				await adminApi.unfreezeUser(item.id, { reason })
				uni.showToast({ title: '用户已解冻' })
				this.loadAll()
			})
		},
		approveProduct(item) {
			this.reason('通过商品审核', async reason => {
				await adminApi.approveProduct(item.id, { reason })
				uni.showToast({ title: '商品已通过' })
				this.loadAll()
			})
		},
		rejectProduct(item) {
			this.reason('驳回商品', async reason => {
				await adminApi.rejectProduct(item.id, { reason })
				uni.showToast({ title: '商品已驳回' })
				this.loadAll()
			}, true)
		},
		offSaleProduct(item) {
			this.reason('强制下架商品', async reason => {
				await adminApi.offSaleProduct(item.id, { reason })
				uni.showToast({ title: '商品已下架' })
				this.loadAll()
			}, true)
		},
		forceCancelOrder(item) {
			this.reason('强制取消订单', async reason => {
				await adminApi.forceCancelOrder(item.id, { reason })
				uni.showToast({ title: '订单已取消' })
				this.loadAll()
			}, true)
		},
		approveMerchant(item) {
			this.reason('通过商家审核', async reason => {
				await adminApi.approveMerchant(item.id, { reason })
				uni.showToast({ title: '商家已通过' })
				this.loadAll()
			})
		},
		rejectMerchant(item) {
			this.reason('驳回商家', async reason => {
				await adminApi.rejectMerchant(item.id, { reason })
				uni.showToast({ title: '商家已驳回' })
				this.loadAll()
			}, true)
		},
		resolveReport(item, action) {
			if (item.status !== 'pending') {
				uni.showToast({ title: '举报已处理', icon: 'none' })
				return
			}
			this.reason(action === 'take_down' ? '下架被举报内容' : '驳回举报', async reason => {
				await adminApi.resolveReport(item.id, { action, reason })
				uni.showToast({ title: '举报已处理' })
				this.loadAll()
			})
		},
		approveAdoption(item) {
			this.reason('通过领养申请', async reason => {
				await adminApi.approveAdoptionApplication(item.id, { reason })
				uni.showToast({ title: '申请已通过' })
				this.loadAll()
			})
		},
		rejectAdoption(item) {
			this.reason('驳回领养申请', async reason => {
				await adminApi.rejectAdoptionApplication(item.id, { reason })
				uni.showToast({ title: '申请已驳回' })
				this.loadAll()
			}, true)
		},
		approveWithdrawal(item) {
			this.reason('通过提现申请', async reason => {
				await walletApi.approveWithdrawal(item.id, { reason })
				uni.showToast({ title: '提现已通过' })
				this.loadAll()
			})
		},
		rejectWithdrawal(item) {
			this.reason('驳回提现申请', async reason => {
				await walletApi.rejectWithdrawal(item.id, { reason })
				uni.showToast({ title: '提现已驳回' })
				this.loadAll()
			}, true)
		},
		logout() {
			clearTokens()
			uni.reLaunch({ url: '/pages/auth/login' })
		},
		home() {
			uni.reLaunch({ url: '/pages/home/index' })
		}
	}
}
</script>

<style scoped lang="scss">
.admin-shell{height:100vh;background:#f7f7f8}.admin-bar{display:flex;height:68px;align-items:center;justify-content:space-between;padding:0 25px;border-bottom:1px solid #e7e7e9;background:#fff}.brand,.sub{display:block}.brand{font-size:20px;font-weight:800}.sub{margin-top:3px;color:#888;font-size:10px}.admin-actions{display:flex;align-items:center;gap:12px;font-size:12px}.admin-layout{display:grid;height:calc(100vh - 68px);grid-template-columns:210px 1fr}.sidebar{padding:16px 10px;background:#24262c;color:#bbb}.sidebar view{display:flex;align-items:center;gap:10px;margin:3px 0;padding:12px 14px;border-radius:9px;font-size:12px}.sidebar view.active{background:var(--color-primary);color:#fff}.workspace{height:100%}.workspace-inner{padding:24px}.metric-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.metric{display:flex;flex-direction:column;gap:8px;padding:20px}.metric text:first-child{font-size:27px;font-weight:800}.metric text:last-child{color:var(--color-text-secondary);font-size:11px}.overview{margin-top:16px}.section-block{margin-top:16px}.section-block:first-of-type{margin-top:0}.section-title{display:block;margin-bottom:10px;font-size:13px;font-weight:800;color:var(--color-text-secondary)}.panel-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px}.panel-heading .panel-title{margin-bottom:4px}.error-text{display:block;margin-top:5px;color:var(--color-danger);font-size:11px;line-height:1.5}.support-panel{padding:24px}.support-tabs{display:inline-flex;gap:4px;margin:2px 0 18px;padding:4px;border:1px solid var(--color-border);border-radius:10px;background:#fff8f1}.support-tab{min-width:76px;height:32px;padding:0 14px;border-radius:8px;color:var(--color-text-secondary);font-size:12px;font-weight:700;line-height:32px;text-align:center;cursor:pointer}.support-tab.active{background:#fff;color:var(--color-primary);box-shadow:0 4px 14px rgba(56,38,22,.08)}.support-list{display:grid;gap:10px}.support-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:18px;padding:16px 18px;border:1px solid var(--color-border);border-radius:12px;background:#fff}.support-main{min-width:0}.support-actions{display:flex;align-items:center;gap:10px}.support-actions .secondary-button{height:34px;padding:0 16px;border-radius:17px;font-size:12px;line-height:34px}.status-chip.resolved{background:#eaf8f0;color:var(--color-success)}@media(max-width:767px){.admin-bar{height:58px;padding:0 12px}.admin-layout{height:calc(100vh - 58px);grid-template-columns:64px 1fr}.sidebar{padding:8px 5px}.sidebar view{justify-content:center;padding:11px 5px;font-size:0}.sidebar view text{font-size:18px}.workspace-inner{padding:12px}.metric-grid{grid-template-columns:repeat(2,1fr)}.panel-heading{flex-direction:column}.support-panel{padding:16px}.support-tabs{display:flex;width:100%}.support-tab{flex:1}.support-row{grid-template-columns:1fr;align-items:flex-start;padding:14px}.support-actions{width:100%;flex-wrap:wrap}.support-actions .secondary-button{flex:1;min-width:120px}}
</style>
