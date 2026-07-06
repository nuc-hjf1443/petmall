<template>
	<AppShell active="adoption"><view class="page-container">
		<view v-if="loading" class="card empty-inline">正在加载领养信息…</view>
		<StatePanel v-else-if="!pet" icon="⚠" title="领养信息不存在" action="返回" @action="back"/>
		<template v-else><view class="content-grid">
			<view class="card pet-card"><image v-if="pet.cover_image" :src="pet.cover_image" mode="aspectFill"/><view v-else class="placeholder">🐾</view><view class="panel"><text class="page-title">{{pet.name}}</text><text class="page-subtitle">{{pet.species}} · {{pet.breed||'品种待补充'}} · {{pet.city}}</text><text class="description">{{pet.description}}</text><text class="data-meta">健康情况：{{pet.health_status||'未说明'}}</text><text class="data-meta">领养要求：{{pet.requirements||'请与发布者沟通'}}</text></view></view>
			<view class="card panel"><text class="panel-title">提交领养申请</text><view class="form-grid"><label v-for="f in fields" :key="f.key" class="form-field" :class="{full:f.full}"><text>{{f.label}}</text><textarea v-if="f.full" v-model="form[f.key]"/><input v-else v-model="form[f.key]"/></label></view><view class="button-row"><button class="action-button" :loading="submitting" @click="apply">提交申请</button><button class="secondary-button" @click="my">我的申请</button></view></view>
		</view></template>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{adoptionApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{id:null,pet:null,loading:true,submitting:false,form:{contact_name:'',contact_phone:'',living_city:'',living_condition:'',experience:'',reason:''},fields:[{key:'contact_name',label:'联系人'},{key:'contact_phone',label:'联系电话'},{key:'living_city',label:'居住城市'},{key:'living_condition',label:'居住条件'},{key:'experience',label:'养宠经验',full:true},{key:'reason',label:'申请理由',full:true}]}},onLoad(q){this.id=q.id;this.load()},methods:{async load(){this.loading=true;try{this.pet=await adoptionApi.detail(this.id)}catch(e){this.pet=null}finally{this.loading=false}},async apply(){if(['contact_name','contact_phone','living_city','living_condition','reason'].some(k=>!this.form[k]))return uni.showToast({title:'请完整填写申请',icon:'none'});this.submitting=true;try{await adoptionApi.apply(this.id,this.form);uni.showToast({title:'领养申请已提交'});setTimeout(()=>this.my(),400)}catch(e){}finally{this.submitting=false}},my(){uni.navigateTo({url:'/pages/adoption/my'})},back(){uni.navigateBack()}}}
</script>
<style scoped>.pet-card{overflow:hidden}.pet-card>image,.placeholder{width:100%;height:360px}.placeholder{display:flex;align-items:center;justify-content:center;background:#fff0df;font-size:100px}.description{display:block;margin:18px 0;line-height:1.8}</style>
