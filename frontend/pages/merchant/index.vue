<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">商家中心</text><text class="page-subtitle">入驻审核、店铺资料与商品状态管理</text></view><button v-if="merchant?.status==='approved'" class="action-button" @click="newProduct">发布商品</button></view>
		<view v-if="loading" class="card empty-inline">正在加载商家资料…</view>
		<view v-else class="content-grid">
			<view class="card panel"><text class="panel-title">{{merchant?'店铺资料':'申请商家入驻'}}</text><view class="form-grid">
				<label v-for="f in fields" :key="f.key" class="form-field" :class="{full:f.full}"><text>{{f.label}}</text><textarea v-if="f.full" v-model="form[f.key]"/><input v-else v-model="form[f.key]"/></label>
			</view><view class="button-row"><button class="action-button" :loading="saving" @click="save">{{merchant?'保存店铺资料':'提交入驻申请'}}</button></view><text v-if="merchant" class="data-meta">状态：{{merchant.status}}　{{merchant.audit_reason||'暂无审核备注'}}</text></view>
			<view class="card panel"><text class="panel-title">经营概览</text>
				<template v-if="dashboard"><view class="stats"><view><text>{{dashboard.pending_product_count}}</text><text>待审核商品</text></view><view><text>{{dashboard.order_count}}</text><text>订单</text></view><view><text>{{products.length}}</text><text>商品总数</text></view></view></template>
				<StatePanel v-else icon="▣" title="通过审核后开放商品管理" :description="merchant?.audit_reason||'请先提交商家入驻申请'"/>
			</view>
		</view>
		<view v-if="merchant?.status==='approved'" class="card panel product-panel"><text class="panel-title">我的商品</text><view v-if="!products.length" class="empty-inline">还没有商品，先发布第一件商品</view><view v-else class="data-list"><view v-for="item in products" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.title}}</text><text class="data-meta">库存 {{item.stock}} · {{item.status}} · {{item.audit_reason||'无审核备注'}}</text></view><button class="secondary-button" @click="editProduct(item.id)">编辑</button><button v-if="['draft','rejected','off_shelf'].includes(item.status)" class="action-button" @click="submit(item.id)">提交审核</button><button v-if="item.status==='off_shelf'" class="secondary-button" @click="onSale(item.id)">上架</button><button v-if="item.status==='on_sale'" class="secondary-button" @click="offSale(item.id)">下架</button><button v-if="['on_sale','off_shelf'].includes(item.status)" class="secondary-button" @click="discount(item.id)">改价</button></view></view></view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{merchantApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{merchant:null,dashboard:null,products:[],loading:true,saving:false,form:{shop_name:'',contact_name:'',contact_phone:'',business_scope:'',city:'',address:'',description:''},fields:[{key:'shop_name',label:'店铺名称'},{key:'contact_name',label:'联系人'},{key:'contact_phone',label:'联系电话'},{key:'business_scope',label:'经营范围'},{key:'city',label:'城市'},{key:'address',label:'地址'},{key:'description',label:'店铺介绍',full:true}]}},onShow(){this.load()},methods:{
	async load(){this.loading=true;try{this.merchant=await merchantApi.me();Object.keys(this.form).forEach(k=>this.form[k]=this.merchant[k]||'')}catch(e){this.merchant=null}if(this.merchant?.status==='approved'){const r=await Promise.allSettled([merchantApi.dashboard(),merchantApi.products()]);if(r[0].status==='fulfilled')this.dashboard=r[0].value;if(r[1].status==='fulfilled')this.products=r[1].value||[]}this.loading=false},
	async save(){if(['shop_name','contact_name','contact_phone','business_scope'].some(k=>!this.form[k]))return uni.showToast({title:'请填写必填资料',icon:'none'});this.saving=true;try{if(this.merchant)await merchantApi.update(this.form);else await merchantApi.apply({...this.form,qualifications:[]});uni.showToast({title:this.merchant?'店铺资料已保存':'入驻申请已提交'});this.load()}catch(e){}finally{this.saving=false}},
	newProduct(){uni.navigateTo({url:'/pages/merchant/product-edit'})},editProduct(id){uni.navigateTo({url:`/pages/merchant/product-edit?id=${id}`})},
	async submit(id){try{await merchantApi.submitProduct(id,{});uni.showToast({title:'商品已提交审核'});this.load()}catch(e){}},
	async onSale(id){try{await merchantApi.putProductOnSale(id,{});uni.showToast({title:'商品已上架'});this.load()}catch(e){}},
	async offSale(id){try{await merchantApi.takeProductOffSale(id,{});uni.showToast({title:'商品已下架'});this.load()}catch(e){}},
	discount(id){uni.showModal({title:'设置 SKU 价格',editable:true,placeholderText:'JSON，例如 {\"12\":9900}',success:async r=>{if(!r.confirm)return;try{await merchantApi.setProductDiscount(id,{sku_prices:JSON.parse(r.content)});uni.showToast({title:'价格已更新'});this.load()}catch(e){if(e instanceof SyntaxError)uni.showToast({title:'JSON 格式错误',icon:'none'})}}})}
}}
</script>
<style scoped>.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.stats view{display:flex;flex-direction:column;gap:6px;padding:18px;border-radius:12px;background:var(--color-primary-soft);color:var(--color-text-secondary);font-size:11px}.stats text:first-child{color:var(--color-primary);font-size:25px;font-weight:800}.product-panel{margin-top:16px}</style>
