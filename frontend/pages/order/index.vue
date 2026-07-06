<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">我的订单</text><text class="page-subtitle">查看支付、配送和完成状态</text></view></view>
		<view class="card panel">
			<view v-if="loading" class="empty-inline">正在加载订单…</view>
			<StatePanel v-else-if="!items.length" icon="▣" title="还没有订单" description="去商城挑选适合毛孩子的好物" action="逛商城" @action="goMall"/>
			<view v-else class="data-list"><view v-for="order in items" :key="order.id" class="data-row" @click="detail(order.id)">
				<view class="data-main"><text class="data-title">订单 {{order.order_no}}</text><text class="data-meta">{{order.items.length}} 件商品 · {{time(order.created_at)}} · {{money(order.pay_amount)}}</text></view><text class="status-chip">{{statusText(order.status)}}</text><text>›</text>
			</view></view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{orderApi}from'../../api';import{formatMoney}from'../../utils/format'
export default{components:{AppShell,StatePanel},data(){return{items:[],loading:true}},onShow(){this.load()},methods:{money:formatMoney,time(v){return v?new Date(v).toLocaleString():'--'},statusText(v){return({pending_payment:'待付款',paid:'已付款',shipped:'待收货',completed:'已完成',cancelled:'已取消'})[v]||v},async load(){this.loading=true;try{this.items=await orderApi.list()||[]}catch(e){}finally{this.loading=false}},detail(id){uni.navigateTo({url:`/pages/order/detail?id=${id}`})},goMall(){uni.reLaunch({url:'/pages/mall/index'})}}}
</script>
