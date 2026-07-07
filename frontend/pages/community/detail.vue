<template>
	<AppShell active="community">
		<view class="page-container">
			<view v-if="loading" class="card empty-inline">正在加载动态...</view>
			<StatePanel v-else-if="!post" icon="-" title="动态不存在" action="返回社区" @action="back" />
			<template v-else>
				<view class="content-grid">
					<view class="card panel">
						<view class="author">
							<text class="avatar">P</text>
							<view>
								<text class="data-title">宠友 {{ post.user_id }}</text>
								<text class="data-meta">{{ post.created_at }}</text>
							</view>
							<button v-if="!post.can_delete" class="secondary-button" @click="toggleFollow">
								{{ post.following_author ? '取消关注' : '关注' }}
							</button>
						</view>
						<text class="content">{{ post.content || '分享了一组宠物照片' }}</text>
						<view class="media">
							<video v-for="m in videos" :key="m.id" :src="assetUrl(m.file_url)" class="post-video" controls />
							<image v-for="m in images" :key="m.id" :src="assetUrl(m.file_url)" mode="aspectFill" />
						</view>
						<view class="button-row">
							<button class="secondary-button" @click="toggleLike">
								{{ post.liked_by_me ? '取消点赞' : '点赞' }} {{ post.like_count }}
							</button>
							<button class="secondary-button" @click="toggleFavorite">
								{{ post.favorited_by_me ? '取消收藏' : '收藏' }} {{ post.favorite_count }}
							</button>
							<button v-if="post.can_delete" class="danger-button" @click="removePost">删除</button>
							<button v-else class="danger-button" @click="report">举报</button>
						</view>
					</view>

					<view class="card panel">
						<text class="panel-title">评论 {{ post.comment_count }}</text>
						<view v-if="!comments.length" class="empty-inline">还没有评论，来聊两句吧</view>
						<view v-else class="data-list">
							<view v-for="item in comments" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">用户 {{ item.user_id }}</text>
									<text class="data-meta">{{ item.content }}</text>
								</view>
								<button class="danger-button" @click="deleteComment(item.id)">删除</button>
							</view>
						</view>
						<view class="form-field">
							<textarea v-model="comment" placeholder="友善交流，分享真实经验" />
						</view>
						<view class="button-row">
							<button class="action-button" @click="sendComment">发表评论</button>
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
import { assetUrl, communityApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			id: null,
			post: null,
			comments: [],
			comment: '',
			loading: true
		}
	},
	onLoad(query) {
		this.id = query.id
		this.load()
	},
	computed: {
		images() {
			return (this.post?.media || []).filter(item => item.media_type !== 'video')
		},
		videos() {
			return (this.post?.media || []).filter(item => item.media_type === 'video')
		}
	},
	methods: {
		assetUrl,
		async load() {
			this.loading = true
			const result = await Promise.allSettled([
				communityApi.detail(this.id),
				communityApi.comments(this.id)
			])
			this.post = result[0].status === 'fulfilled' ? result[0].value : null
			this.comments = result[1].status === 'fulfilled' ? result[1].value : []
			this.loading = false
		},
		async toggleLike() {
			if (!this.post) return
			await (this.post.liked_by_me ? communityApi.unlike(this.id) : communityApi.like(this.id))
			uni.showToast({ title: this.post.liked_by_me ? '已取消点赞' : '已点赞' })
			this.load()
		},
		async toggleFavorite() {
			if (!this.post) return
			await (this.post.favorited_by_me ? communityApi.unfavorite(this.id) : communityApi.favorite(this.id))
			uni.showToast({ title: this.post.favorited_by_me ? '已取消收藏' : '已收藏' })
			this.load()
		},
		async toggleFollow() {
			if (!this.post) return
			await (this.post.following_author ? communityApi.unfollow(this.post.user_id) : communityApi.follow(this.post.user_id))
			uni.showToast({ title: this.post.following_author ? '已取消关注' : '已关注' })
			this.load()
		},
		removePost() {
			uni.showModal({
				title: '删除动态',
				content: '确认删除这条动态吗？',
				success: async result => {
					if (!result.confirm) return
					await communityApi.remove(this.id)
					uni.showToast({ title: '动态已删除' })
					setTimeout(() => this.back(), 300)
				}
			})
		},
		async sendComment() {
			if (!this.comment.trim()) return
			await communityApi.createComment(this.id, { content: this.comment })
			this.comment = ''
			uni.showToast({ title: '评论已发布' })
			this.load()
		},
		async deleteComment(id) {
			await communityApi.deleteComment(this.id, id)
			uni.showToast({ title: '评论已删除' })
			this.load()
		},
		report() {
			uni.showModal({
				title: '举报动态',
				editable: true,
				placeholderText: '请输入举报原因',
				success: async result => {
					if (!result.confirm || !result.content) return
					await communityApi.report(this.id, {
						target_type: 'post',
						target_id: Number(this.id),
						reason: result.content
					})
					uni.showToast({ title: '举报已提交' })
				}
			})
		},
		back() {
			uni.navigateBack()
		}
	}
}
</script>

<style scoped>
.author{display:flex;align-items:center;gap:12px}.author button{margin-left:auto}.avatar{display:flex;width:44px;height:44px;align-items:center;justify-content:center;border-radius:50%;background:var(--color-primary-soft);font-weight:800}.content{display:block;margin:24px 0;font-size:16px;line-height:1.9}.media{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.media image,.post-video{width:100%;height:190px;border-radius:10px;background:#f7f3ef}.post-video{grid-column:1/-1;height:360px}@media(max-width:767px){.media image{height:110px}.post-video{height:210px}}
</style>
