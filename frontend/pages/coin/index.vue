<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">宠物币中心</text><text class="page-subtitle">签到、任务与余额流水</text></view><button class="action-button" :loading="checking" @click="checkin">今日签到</button></view>
		<view class="coin-card card"><text>可用宠物币</text><text>{{account.balance||0}}</text><text>累计获得 {{account.total_earned||0}} · 已使用 {{account.total_spent||0}}</text></view>
		<view class="content-grid">
			<view class="card panel"><text class="panel-title">成长任务</text><view v-if="loading" class="empty-inline">正在加载…</view><view v-else-if="!tasks.length" class="empty-inline">暂无可用任务</view><view v-else class="data-list"><view v-for="item in tasks" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.name}} +{{item.reward_amount}}</text><text class="data-meta">{{item.description||item.task_type}}</text></view><button class="action-button" :disabled="item.claimed" @click="claim(item)">{{item.claimed?'已领取':'领取'}}</button></view></view></view>
			<view class="card panel"><text class="panel-title">宠物币流水</text><view v-if="!logs.length" class="empty-inline">暂无流水记录</view><view v-else class="data-list"><view v-for="item in logs" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.remark||item.source}}</text><text class="data-meta">{{item.created_at}}</text></view><text :class="item.change_amount>0?'plus':'minus'">{{item.change_amount>0?'+':''}}{{item.change_amount}}</text></view></view></view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import{coinApi}from'../../api'
export default{components:{AppShell},data(){return{account:{},tasks:[],logs:[],loading:true,checking:false}},onShow(){this.load()},methods:{async load(){this.loading=true;const r=await Promise.allSettled([coinApi.account(),coinApi.tasks(),coinApi.logs({page:1,page_size:50})]);if(r[0].status==='fulfilled')this.account=r[0].value;if(r[1].status==='fulfilled')this.tasks=r[1].value||[];if(r[2].status==='fulfilled')this.logs=r[2].value||[];this.loading=false},async checkin(){this.checking=true;try{await coinApi.checkin();uni.showToast({title:'签到成功'});this.load()}catch(e){}finally{this.checking=false}},async claim(item){try{await coinApi.claimTask(item.id);uni.showToast({title:'奖励已领取'});this.load()}catch(e){}}}}
</script>
<style scoped>.coin-card{display:flex;flex-direction:column;gap:9px;margin-bottom:16px;padding:28px;background:linear-gradient(135deg,#ff8f38,#ff6d14);color:#fff}.coin-card text:nth-child(2){font-size:38px;font-weight:800}.coin-card text:last-child{font-size:11px;opacity:.85}.plus{color:var(--color-success);font-weight:800}.minus{color:var(--color-danger);font-weight:800}</style>
