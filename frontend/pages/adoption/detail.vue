<template>
	<AppShell active="adoption">
		<view class="page-container adoption-page">
			<view v-if="loading" class="card empty-inline">正在加载领养信息...</view>
			<StatePanel v-else-if="!pet" icon="!" title="领养信息不存在" action="返回" @action="back" />
			<template v-else>
				<view class="adoption-layout">
					<view class="card pet-card">
						<image v-if="pet.cover_image" :src="assetUrl(pet.cover_image)" mode="aspectFill" />
						<view v-else class="pet-placeholder">
							<text>温暖领养</text>
							<text>建议上传真实猫狗照片或家居背景图</text>
						</view>
						<view class="pet-content">
							<text class="page-title">{{ pet.name }}</text>
							<text class="page-subtitle">{{ pet.species }} · {{ pet.breed || '品种待补充' }} · {{ pet.city }}</text>
							<view class="tag-row">
								<text>健康良好</text>
								<text>性格亲人</text>
								<text>适合家庭</text>
							</view>
							<text class="description">{{ pet.description }}</text>
							<text class="data-meta">健康情况：{{ pet.health_status || '未说明' }}</text>
							<text class="data-meta">领养要求：{{ pet.requirements || '请与发布者沟通' }}</text>
							<view class="button-row">
								<button class="secondary-button" :disabled="isOwnPet" @click="contactPublisher">
									{{ isOwnPet ? '自己发布的信息' : '联系发布人' }}
								</button>
							</view>
						</view>
					</view>

					<view class="card apply-panel">
						<view class="flow-box">
							<text class="panel-title">领养流程</text>
							<view class="flow">
								<text>提交申请</text><text>平台审核</text><text>联系救助人</text><text>线下见面</text><text>完成领养</text>
							</view>
						</view>

						<view class="form-section">
							<text class="section-label">基础信息</text>
							<view class="form-grid">
								<label class="form-field"><text>联系人</text><input v-model="form.contact_name" /></label>
								<label class="form-field"><text>联系电话</text><input v-model="form.contact_phone" /></label>
								<label class="form-field"><text>居住城市</text><input v-model="form.living_city" /></label>
								<label class="form-field"><text>居住条件</text><input v-model="form.living_condition" /></label>
							</view>
						</view>

						<view class="form-section">
							<text class="section-label">养宠情况</text>
							<view class="form-grid">
								<label class="form-field full"><text>养宠经验</text><textarea v-model="form.experience" placeholder="是否有养宠经验、家中是否有人过敏、是否接受回访" /></label>
							</view>
						</view>

						<view class="form-section">
							<text class="section-label">申请理由</text>
							<label class="form-field full"><text>为什么想领养它</text><textarea v-model="form.reason" placeholder="请写下你的领养计划和照顾方式" /></label>
						</view>

						<view class="button-row">
							<button class="action-button" :loading="submitting" @click="apply">提交领养申请</button>
							<button class="secondary-button" @click="my">查看我的申请</button>
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
import { adoptionApi, assetUrl, getAccessToken, supportApi, userApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			id: null,
			pet: null,
			currentUserId: null,
			loading: true,
			submitting: false,
			form: { contact_name: '', contact_phone: '', living_city: '', living_condition: '', experience: '', reason: '' }
		}
	},
	computed: {
		isOwnPet() {
			return !!this.currentUserId && this.pet?.publisher_id === this.currentUserId
		}
	},
	onLoad(query) {
		this.id = query.id
		this.load()
	},
	methods: {
		assetUrl,
		ensureLogin() {
			if (getAccessToken()) return true
			uni.navigateTo({ url: '/pages/auth/login' })
			return false
		},
		async load() {
			this.loading = true
			try {
				const tasks = [adoptionApi.detail(this.id)]
				if (getAccessToken()) tasks.push(userApi.me())
				const result = await Promise.allSettled(tasks)
				this.pet = result[0].status === 'fulfilled' ? result[0].value : null
				if (result[1]?.status === 'fulfilled') this.currentUserId = result[1].value?.id
			} finally {
				this.loading = false
			}
		},
		async apply() {
			if (!this.ensureLogin()) return
			if (['contact_name', 'contact_phone', 'living_city', 'living_condition', 'reason'].some(key => !this.form[key])) {
				return uni.showToast({ title: '请完整填写申请', icon: 'none' })
			}
			this.submitting = true
			try {
				await adoptionApi.apply(this.id, this.form)
				uni.showToast({ title: '领养申请已提交' })
				setTimeout(() => this.my(), 400)
			} finally {
				this.submitting = false
			}
		},
		async contactPublisher() {
			if (!this.ensureLogin()) return
			if (this.isOwnPet) return uni.showToast({ title: '不能联系自己发布的领养信息', icon: 'none' })
			const conversation = await supportApi.adoption(this.id)
			uni.navigateTo({ url: `/pages/support/adoption?id=${conversation.id}` })
		},
		my() {
			uni.navigateTo({ url: '/pages/adoption/my' })
		},
		back() {
			uni.navigateBack()
		}
	}
}
</script>

<style scoped lang="scss">
.adoption-page{max-width:1180px}.adoption-layout{display:grid;grid-template-columns:minmax(360px,.95fr) minmax(440px,1.05fr);gap:24px}.pet-card{overflow:hidden}.pet-card>image,.pet-placeholder{width:100%;height:390px}.pet-card>image{display:block;object-fit:cover}.pet-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;background:linear-gradient(145deg,#fff0df,#fffaf5);color:var(--color-text-secondary);text-align:center}.pet-placeholder text:first-child{color:var(--color-primary);font-size:34px;font-weight:900}.pet-content{padding:28px}.tag-row{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.tag-row text{padding:6px 10px;border-radius:15px;background:var(--color-primary-soft);color:var(--color-primary);font-size:12px;font-weight:700}.description{display:block;margin:16px 0 18px;color:var(--color-text);font-size:15px;line-height:1.8}.apply-panel{padding:26px}.flow-box{padding:18px;border-radius:14px;background:#fff8f2}.flow{display:flex;flex-wrap:wrap;gap:8px}.flow text{position:relative;padding:7px 11px;border-radius:16px;background:#fff;color:var(--color-text-secondary);font-size:12px}.flow text:not(:last-child)::after{content:'→';margin-left:8px;color:var(--color-primary)}.form-section{margin-top:22px}.section-label{display:block;margin-bottom:12px;color:var(--color-text);font-size:16px;font-weight:900}.form-field textarea{min-height:118px}.button-row .action-button,.button-row .secondary-button{height:42px;line-height:42px}@media(max-width:900px){.adoption-layout{grid-template-columns:1fr}.pet-card>image,.pet-placeholder{height:300px}.apply-panel,.pet-content{padding:20px}}
</style>
