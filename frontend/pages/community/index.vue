<template>
	<AppShell active="community"><view class="page-container community-page">
		<view class="community-head"><view><text class="title">宠友社区</text><text class="subtitle">分享毛孩子的每一个可爱瞬间</text></view><button class="publish" @click="publish">＋ 发布动态</button></view>
		<scroll-view scroll-x class="topic-scroll"><view class="topics"><view class="topic active">推荐</view><view v-for="topic in topics" :key="topic.id" class="topic"># {{topic.name}}</view></view></scroll-view>
		<StatePanel v-if="loading" icon="…" title="正在加载社区动态"/>
		<StatePanel v-else-if="error" icon="⚠" title="社区加载失败" :description="error" action="重试" @action="load"/>
		<StatePanel v-else-if="!posts.length" icon="◉" title="社区还没有动态" description="发布第一条与毛孩子有关的故事吧" action="发布动态" @action="publish"/>
		<view v-else class="post-grid">
			<view v-for="(post,index) in posts" :key="post.id||index" class="post card" @click="detail(post.id)">
				<image v-if="post.media?.[0]?.file_url" class="post-image" :src="post.media[0].file_url" mode="aspectFill"/><view v-else class="post-image post-placeholder">{{['🐕','🐈','🐾','🌿'][index%4]}}</view>
				<view class="post-body"><view class="author"><view class="avatar">🐾</view><text>宠友 {{post.user_id||index+1}}</text></view><text class="post-content">{{post.content}}</text><view class="post-footer"><text>♡ {{post.like_count||0}}</text><text>◌ {{post.comment_count||0}}</text><text>☆ {{post.favorite_count||0}}</text></view></view>
			</view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{communityApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{posts:[],topics:[],error:'',loading:true}},onLoad(){this.load()},methods:{async load(){this.loading=true;this.error='';const result=await Promise.allSettled([communityApi.list(),communityApi.topics()]);if(result[0].status==='fulfilled')this.posts=result[0].value||[];else this.error=result[0].reason.message;if(result[1].status==='fulfilled')this.topics=result[1].value||[];this.loading=false},publish(){uni.navigateTo({url:uni.getStorageSync('access_token')?'/pages/community/publish':'/pages/auth/login'})},detail(id){uni.navigateTo({url:`/pages/community/detail?id=${id}`})}}}
</script>
<style scoped lang="scss">
.community-head{display:flex;align-items:center;justify-content:space-between;margin:12px 0 22px}.title,.subtitle{display:block}.title{font-size:30px;font-weight:800}.subtitle{margin-top:7px;color:var(--color-text-secondary);font-size:14px}.publish{margin:0;padding:0 22px;border-radius:22px;background:var(--color-primary);color:#fff;font-size:13px}.topic-scroll{white-space:nowrap}.topics{display:flex;gap:10px;padding-bottom:18px}.topic{padding:8px 18px;border-radius:18px;background:#fff;color:#817972;font-size:12px}.topic.active{background:var(--color-primary-soft);color:var(--color-primary);font-weight:700}.post-grid{columns:4 260px;column-gap:18px}.post{display:inline-block;width:100%;margin-bottom:18px;overflow:hidden;break-inside:avoid}.post-image{width:100%;height:210px;background:#f4ebe2}.post:nth-child(3n+1) .post-image{height:280px}.post-placeholder{display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#f8eee4,#fff9f2);font-size:80px}.post-body{padding:15px}.author{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700}.avatar{display:flex;width:30px;height:30px;align-items:center;justify-content:center;border-radius:50%;background:#fff0df}.post-content{display:block;margin-top:12px;font-size:14px;line-height:1.65}.post-footer{display:flex;justify-content:space-between;margin-top:14px;color:var(--color-text-secondary);font-size:12px}
@media(max-width:900px){.community-head{margin:5px 0 14px}.title{font-size:23px}.subtitle{font-size:11px}.publish{height:36px;padding:0 15px;line-height:36px}.post-grid{columns:2 150px;column-gap:10px}.post{margin-bottom:10px}.post-image,.post:nth-child(3n+1) .post-image{height:160px}.post:nth-child(3n+1) .post-image{height:210px}.post-placeholder{font-size:52px}.post-body{padding:11px}.post-content{font-size:12px}.post-footer{font-size:10px}}
</style>
