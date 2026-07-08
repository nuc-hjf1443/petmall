<template>
	<AppShell active="community">
		<view class="page-container community-page">
			<view class="community-head">
				<view>
					<text class="title">宠友社区</text>
					<text class="subtitle">分享宠物日常、养宠经验和温暖瞬间</text>
				</view>
				<button class="publish" @click="publish">+ 发布动态</button>
			</view>

			<scroll-view scroll-x class="topic-scroll">
				<view class="topics">
					<view v-for="item in filterItems" :key="item.key" class="topic" :class="{ active: activeFilter === item.key }" @click="selectFilter(item)">{{ item.label }}</view>
				</view>
			</scroll-view>

			<StatePanel v-if="loading" icon="..." title="正在加载社区动态" />
			<StatePanel v-else-if="error" icon="!" title="社区加载失败" :description="error" action="重试" @action="load" />
			<StatePanel v-else-if="!displayPosts.length" icon="-" title="社区还没有动态" description="发布第一条与宠物有关的故事吧" action="发布动态" @action="publish" />

			<view v-else class="community-grid">
				<view v-for="(post, index) in displayPosts" :key="post.id || index" class="post-card card" @click="detail(post.id)">
					<image v-if="post.media?.[0]?.file_url" class="post-image" :src="assetUrl(post.media[0].file_url)" mode="aspectFill" />
					<view v-else class="post-image post-placeholder">
						<text>{{ ['猫咪日常', '狗狗公园', '领养故事', '养宠经验'][index % 4] }}</text>
					</view>
					<view class="post-body">
						<view class="author">
							<view class="avatar">宠</view>
							<view>
								<text>宠友 {{ post.user_id || index + 1 }}</text>
								<text>{{ formatTime(post.created_at) }}</text>
							</view>
						</view>
						<text class="post-content">{{ post.content || '分享了一组宠物照片' }}</text>
						<view class="post-footer">
							<text>♡ {{ post.like_count || 0 }}</text>
							<text>💬 {{ post.comment_count || 0 }}</text>
							<text>☆ {{ post.favorite_count || 0 }}</text>
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
import { assetUrl, communityApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			posts: [],
			topics: [],
			defaultTopicNames: ['猫咪', '狗狗', '领养故事', '养宠经验'],
			activeFilter: 'recommend',
			error: '',
			loading: true
		}
	},
	computed: {
		filterItems() {
			const topicItems = this.defaultTopicNames.map(name => {
				const topic = this.topics.find(item => item.name === name)
				return { key: `topic:${name}`, label: name, topicId: topic?.id || null, topicName: name }
			})
			return [
				{ key: 'recommend', label: '推荐' },
				{ key: 'latest', label: '最新' },
				...topicItems,
				{ key: 'other', label: '其他' }
			]
		},
		defaultTopicIds() {
			return this.topics
				.filter(item => this.defaultTopicNames.includes(item.name))
				.map(item => item.id)
		},
		displayPosts() {
			return this.posts
		}
	},
	onLoad() {
		this.load()
	},
	methods: {
		assetUrl,
		formatTime(value) {
			return value ? String(value).replace('T', ' ').slice(0, 10) : ''
		},
		async load() {
			this.loading = true
			this.error = ''
			const activeItem = this.filterItems.find(item => item.key === this.activeFilter)
			const params = this.filterParams(activeItem)
			const result = await Promise.allSettled([
				communityApi.list(params),
				communityApi.topics({ silentNetworkError: true })
			])
			if (result[0].status === 'fulfilled') this.posts = result[0].value || []
			else this.error = result[0].reason.message
			if (result[1].status === 'fulfilled') this.topics = result[1].value || []
			this.loading = false
		},
		selectFilter(item) {
			this.activeFilter = item.key
			this.load()
		},
		filterParams(item) {
			if (!item || item.key === 'latest') return { sort: 'latest' }
			if (item.key === 'recommend') return { sort: 'recommend' }
			if (item.key === 'other') return { topic_scope: 'other', sort: 'latest' }
			if (item.topicId) return { topic_id: item.topicId, sort: 'latest' }
			if (item.topicName) return { topic_name: item.topicName, sort: 'latest' }
			return { sort: 'latest' }
		},
		publish() {
			uni.navigateTo({ url: uni.getStorageSync('access_token') ? '/pages/community/publish' : '/pages/auth/login' })
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/community/detail?id=${id}` })
		}
	}
}
</script>

<style scoped lang="scss">
.community-page{max-width:1180px}.community-head{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:6px 0 22px}.title,.subtitle{display:block}.title{font-size:32px;font-weight:900;line-height:1.25}.subtitle{margin-top:7px;color:var(--color-text-secondary);font-size:14px}.publish{height:42px;margin:0;padding:0 22px;border-radius:22px;background:var(--color-primary);color:#fff;font-size:14px;font-weight:800;line-height:42px}.topic-scroll{white-space:nowrap}.topics{display:flex;gap:10px;padding-bottom:20px}.topic{height:34px;padding:0 16px;border:1px solid var(--color-border);border-radius:17px;background:#fff;color:var(--color-text-secondary);font-size:13px;line-height:34px}.topic.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.community-grid{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}.post-card{width:calc((100% - 48px)/3);overflow:hidden;cursor:pointer;transition:transform .18s ease, box-shadow .18s ease}.post-card:active{transform:translateY(1px)}.post-image{display:block;width:100%;height:220px;background:#f7eee6}.post-placeholder{display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#fff3e8,#fffaf5);color:var(--color-primary);font-size:22px;font-weight:900}.post-body{padding:16px}.author{display:flex;align-items:center;gap:10px}.avatar{display:flex;width:36px;height:36px;align-items:center;justify-content:center;border-radius:50%;background:var(--color-primary-soft);color:var(--color-primary);font-size:13px;font-weight:900}.author text{display:block}.author text:first-child{font-size:13px;font-weight:800}.author text:last-child{margin-top:3px;color:var(--color-text-secondary);font-size:10px}.post-content{display:block;min-height:44px;margin-top:14px;color:var(--color-text);font-size:14px;line-height:1.6}.post-footer{display:flex;gap:18px;margin-top:14px;color:var(--color-text-secondary);font-size:12px}@media(max-width:900px){.community-grid{gap:14px}.post-card{width:calc((100% - 14px)/2)}.title{font-size:25px}.post-image{height:180px}}@media(max-width:560px){.community-head{align-items:flex-start;flex-direction:column}.post-card{width:100%}.publish{width:100%}}
</style>
