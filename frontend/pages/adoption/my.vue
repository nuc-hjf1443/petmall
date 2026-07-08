<template>
	<AppShell active="adoption">
		<view class="page-container">
			<view class="page-heading">
				<view>
					<text class="page-title">我的领养申请</text>
					<text class="page-subtitle">查看审核状态、管理员反馈和发布人沟通记录</text>
				</view>
			</view>
			<view class="card panel">
				<view v-if="loading" class="empty-inline">正在加载申请...</view>
				<StatePanel v-else-if="!items.length" icon="-" title="还没有领养申请" action="看看待领养宠物" @action="back" />
				<view v-else class="data-list">
					<view v-for="item in items" :key="item.id" class="data-row">
						<view class="data-main">
							<text class="data-title">申请 #{{ item.id }}</text>
							<text class="data-meta">{{ item.living_city }} · {{ item.reason }}<br />{{ item.audit_reason || '等待审核反馈' }}</text>
						</view>
						<text class="status-chip">{{ item.status }}</text>
						<button class="secondary-button" @click="chat(item)">沟通</button>
					</view>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { adoptionApi, supportApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return { items: [], loading: true }
	},
	onShow() {
		this.load()
	},
	methods: {
		async load() {
			this.loading = true
			try {
				this.items = await adoptionApi.myApplications() || []
			} catch (error) {
			} finally {
				this.loading = false
			}
		},
		async chat(item) {
			const conversation = await supportApi.adoption(item.adoption_pet_id, item.id)
			uni.navigateTo({ url: `/pages/support/adoption?id=${conversation.id}` })
		},
		back() {
			uni.reLaunch({ url: '/pages/adoption/index' })
		}
	}
}
</script>
