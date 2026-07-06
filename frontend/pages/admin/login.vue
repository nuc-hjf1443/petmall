<template>
	<view class="admin-login"><view class="card login-card"><text class="page-title">PetMall 管理后台</text><text class="page-subtitle">仅管理员账号可进入审核与治理中心</text><view class="form-grid"><label class="form-field full"><text>账号</text><input v-model="form.account"/></label><label class="form-field full"><text>密码</text><input v-model="form.password" password/></label></view><button class="primary-button" :loading="loading" @click="login">管理员登录</button><button class="secondary-button back" @click="home">返回用户端</button></view></view>
</template>
<script>
import{adminApi,userApi,clearTokens}from'../../api'
export default{data(){return{form:{account:'',password:''},loading:false}},methods:{async login(){if(!this.form.account||!this.form.password)return uni.showToast({title:'请输入账号和密码',icon:'none'});this.loading=true;try{await adminApi.login(this.form);const user=await userApi.me();if(!user.is_admin){clearTokens();throw new Error('当前账号没有管理员权限')}uni.showToast({title:'登录成功'});setTimeout(()=>uni.reLaunch({url:'/pages/admin/index'}),300)}catch(e){uni.showToast({title:e.message,icon:'none'})}finally{this.loading=false}},home(){uni.reLaunch({url:'/pages/home/index'})}}}
</script>
<style scoped>.admin-login{display:flex;min-height:100vh;align-items:center;justify-content:center;padding:20px;background:linear-gradient(135deg,#fff6ed,#f4f7ff)}.login-card{width:430px;padding:34px}.form-grid{margin:25px 0}.back{width:100%;margin-top:12px}</style>
