<template>
	<AppShell active="profile"><view class="page-container">
		<view class="card result">
			<view v-if="loading">正在查询支付结果…</view>
			<template v-else-if="payment"><text class="icon">{{payment.status==='paid'?'✓':'…'}}</text><text class="page-title">{{payment.status==='paid'?'支付成功':'等待支付结果'}}</text><text class="page-subtitle">交易号 {{payment.out_trade_no}}</text><text class="amount">{{money(payment.amount)}}</text><view class="button-row"><button class="action-button" @click="query">刷新结果</button><button class="secondary-button" @click="next">{{payment.business_type==='wallet_recharge'?'返回钱包':'查看订单'}}</button></view></template>
			<StatePanel v-else icon="⚠" title="支付结果查询失败" action="重试" @action="load"/>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{paymentApi}from'../../api';import{formatMoney}from'../../utils/format'
export default{components:{AppShell,StatePanel},data(){return{outTradeNo:'',payment:null,loading:true}},onLoad(q){this.outTradeNo=q.out_trade_no;this.load()},methods:{money:formatMoney,async load(){this.loading=true;try{this.payment=await paymentApi.result(this.outTradeNo)}catch(e){this.payment=null}finally{this.loading=false}},async query(){this.loading=true;try{this.payment=await paymentApi.query(this.outTradeNo);uni.showToast({title:'结果已更新'})}catch(e){}finally{this.loading=false}},next(){if(this.payment.business_type==='wallet_recharge')return uni.redirectTo({url:'/pages/wallet/index'});uni.redirectTo({url:`/pages/order/detail?id=${this.payment.order_id}`})}}}
</script>
<style scoped>.result{display:flex;min-height:420px;flex-direction:column;align-items:center;justify-content:center;padding:30px;text-align:center}.icon{display:flex;width:70px;height:70px;align-items:center;justify-content:center;margin-bottom:18px;border-radius:50%;background:#e9f8ef;color:var(--color-success);font-size:38px}.amount{margin:20px;color:var(--color-primary);font-size:30px;font-weight:800}</style>
