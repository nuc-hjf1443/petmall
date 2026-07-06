<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">个人资料</text><text class="page-subtitle">完善资料后，推荐与养宠建议会更贴合你</text></view></view>
		<view class="content-grid">
			<view class="card panel">
				<text class="panel-title">基础与偏好</text>
				<view v-if="loading" class="empty-inline">正在加载资料…</view>
				<view v-else class="form-grid">
					<label v-for="field in fields" :key="field.key" class="form-field" :class="{full:field.full}">
						<text>{{field.label}}</text>
						<textarea v-if="field.long" v-model="form[field.key]" :placeholder="field.placeholder"/>
						<input v-else v-model="form[field.key]" :placeholder="field.placeholder"/>
					</label>
				</view>
				<view class="button-row"><button class="action-button" :loading="saving" @click="save">保存资料</button></view>
			</view>
			<view class="card panel">
				<text class="panel-title">账号安全</text>
				<view class="form-grid">
					<label class="form-field full"><text>当前密码</text><input v-model="password.old_password" password/></label>
					<label class="form-field full"><text>新密码（至少 8 位）</text><input v-model="password.new_password" password/></label>
				</view>
				<view class="button-row"><button class="secondary-button" :loading="changing" @click="changePassword">修改密码</button><button class="danger-button" @click="logout">退出登录</button></view>
			</view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue'
import { authApi, userApi } from '../../api'
export default {
	components:{AppShell},
	data(){return{
		loading:true,saving:false,changing:false,
		form:{email:'',nickname:'',avatar:'',city:'',pet_experience:'',living_city:'',living_environment:'',budget_preference:'',preferred_categories:'',feeding_philosophy:'',allergy_notes:''},
		password:{old_password:'',new_password:''},
		fields:[
			{key:'nickname',label:'昵称'},{key:'email',label:'邮箱'},{key:'avatar',label:'头像 URL'},{key:'city',label:'所在城市'},
			{key:'pet_experience',label:'养宠经验'},{key:'living_city',label:'居住城市'},{key:'living_environment',label:'居住环境'},{key:'budget_preference',label:'预算偏好'},
			{key:'preferred_categories',label:'偏好品类',full:true},{key:'feeding_philosophy',label:'喂养理念',full:true,long:true},{key:'allergy_notes',label:'过敏说明',full:true,long:true}
		]
	}},
	onLoad(){this.load()},
	methods:{
		async load(){this.loading=true;try{const user=await userApi.me();Object.keys(this.form).forEach(k=>{this.form[k]=user[k]??user.profile?.[k]??''})}catch(e){}finally{this.loading=false}},
		async save(){this.saving=true;try{await userApi.updateProfile(this.form);uni.showToast({title:'资料已保存'})}catch(e){}finally{this.saving=false}},
		async changePassword(){if(this.password.new_password.length<8)return uni.showToast({title:'新密码至少 8 位',icon:'none'});this.changing=true;try{await userApi.changePassword(this.password);this.password={old_password:'',new_password:''};uni.showToast({title:'密码修改成功'})}catch(e){}finally{this.changing=false}},
		async logout(){await authApi.logout();uni.reLaunch({url:'/pages/home/index'})}
	}
}
</script>
