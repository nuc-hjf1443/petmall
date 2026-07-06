<template>
	<AppShell active="mall"><view class="page-container">
		<view v-if="loading" class="card empty-inline">正在加载商品详情…</view>
		<StatePanel v-else-if="error" icon="⚠" title="商品加载失败" :description="error" action="重试" @action="load"/>
		<template v-else-if="product">
			<view class="product-layout">
				<view class="card gallery"><image v-if="activeImage" :src="activeImage" mode="aspectFit"/><view v-else class="placeholder">📦</view></view>
				<view class="card panel">
					<text class="page-title">{{product.title}}</text><text class="description">{{product.description||'暂无商品介绍'}}</text>
					<text class="price">{{money(selectedSku?.price??product.price)}}</text>
					<text class="label">选择规格</text>
					<view class="sku-row"><view v-for="sku in product.skus" :key="sku.id" class="sku-chip" :class="{active:selectedSku?.id===sku.id}" @click="selectedSku=sku">{{sku.name}} · 库存 {{sku.stock}}</view></view>
					<view class="quantity"><button @click="quantity=Math.max(1,quantity-1)">−</button><text>{{quantity}}</text><button @click="quantity=Math.min(99,quantity+1)">＋</button></view>
					<view class="button-row"><button class="action-button" :loading="adding" @click="addCart">加入购物车</button><button class="secondary-button" @click="goCart">查看购物车</button></view>
				</view>
			</view>
			<view class="card panel reviews">
				<text class="panel-title">用户评价 {{reviewData.total||0}}</text>
				<view v-if="!reviewData.items?.length" class="empty-inline">暂时还没有评价</view>
				<view v-else class="data-list"><view v-for="item in reviewData.items" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{'★'.repeat(item.rating)}}　{{item.sku_name}}</text><text class="data-meta">{{item.content||'用户未填写文字评价'}}</text></view></view></view>
				<view class="review-form"><text class="panel-title">发表购买评价</text><view class="form-grid"><label class="form-field"><text>订单商品 ID</text><input v-model.number="reviewForm.order_item_id" type="number" placeholder="从已完成订单中获取"/></label><label class="form-field"><text>评分（1-5）</text><input v-model.number="reviewForm.rating" type="number"/></label><label class="form-field full"><text>评价内容</text><textarea v-model="reviewForm.content"/></label></view><view class="button-row"><button class="action-button" @click="createReview">提交评价</button></view></view>
			</view>
		</template>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{productApi,cartApi}from'../../api';import{formatMoney}from'../../utils/format'
export default{components:{AppShell,StatePanel},data(){return{id:null,product:null,selectedSku:null,quantity:1,reviewData:{items:[]},reviewForm:{order_item_id:null,rating:5,content:'',is_anonymous:false},loading:true,adding:false,error:''}},computed:{activeImage(){return this.product?.images?.find(v=>v.is_primary)?.image_url||this.product?.cover_image}},onLoad(q){this.id=q.id;this.load()},methods:{money:formatMoney,async load(){this.loading=true;this.error='';try{const [p,r]=await Promise.all([productApi.detail(this.id),productApi.reviews(this.id,{page:1,page_size:20})]);this.product=p;this.selectedSku=p.skus?.find(v=>v.stock>0&&v.is_enabled)||p.skus?.[0];this.reviewData=r}catch(e){this.error=e.message}finally{this.loading=false}},async addCart(){if(!this.selectedSku)return uni.showToast({title:'请选择规格',icon:'none'});this.adding=true;try{await cartApi.add({sku_id:this.selectedSku.id,quantity:this.quantity});uni.showToast({title:'已加入购物车'})}catch(e){}finally{this.adding=false}},async createReview(){if(!this.reviewForm.order_item_id)return uni.showToast({title:'请输入订单商品 ID',icon:'none'});try{await productApi.createReview(this.id,this.reviewForm);this.reviewForm={order_item_id:null,rating:5,content:'',is_anonymous:false};uni.showToast({title:'评价已发布'});this.load()}catch(e){}},goCart(){uni.navigateTo({url:'/pages/cart/index'})}}}
</script>
<style scoped lang="scss">
.product-layout{display:grid;grid-template-columns:minmax(300px,1fr) minmax(320px,1fr);gap:18px}.gallery{display:flex;min-height:480px;align-items:center;justify-content:center;overflow:hidden}.gallery image{width:100%;height:480px}.placeholder{font-size:100px}.description{display:block;margin:16px 0;color:var(--color-text-secondary);line-height:1.8}.price{display:block;margin:22px 0;color:var(--color-primary);font-size:30px;font-weight:800}.label{display:block;margin-bottom:10px;font-weight:700}.sku-row{display:flex;flex-wrap:wrap;gap:9px}.sku-chip{padding:9px 13px;border:1px solid var(--color-border);border-radius:10px;font-size:12px}.sku-chip.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary)}.quantity{display:flex;align-items:center;width:max-content;margin-top:18px;border:1px solid var(--color-border);border-radius:18px}.quantity button{width:36px;margin:0;background:#fff}.quantity text{width:38px;text-align:center}.reviews{margin-top:18px}@media(max-width:767px){.product-layout{grid-template-columns:1fr}.gallery,.gallery image{min-height:280px;height:280px}}
</style>
