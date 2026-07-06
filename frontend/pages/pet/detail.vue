<template>
	<AppShell active="profile"><view class="page-container">
		<view v-if="loading" class="card empty-inline">正在加载宠物档案…</view>
		<StatePanel v-else-if="!pet" icon="⚠" title="档案加载失败" action="重试" @action="load"/>
		<template v-else>
			<view class="page-heading"><view><text class="page-title">{{pet.name}} 的档案</text><text class="page-subtitle">资料完整度 {{completeness.completeness||0}}%</text></view><button class="danger-button" @click="removePet">删除档案</button></view>
			<view class="content-grid">
				<view class="card panel"><text class="panel-title">基础资料</text><view class="form-grid">
					<label v-for="f in baseFields" :key="f.key" class="form-field"><text>{{f.label}}</text><input v-model="base[f.key]" :type="f.type||'text'"/></label>
				</view><view class="button-row"><button class="action-button" @click="saveBase">保存基础资料</button></view></view>
				<view class="card panel"><text class="panel-title">健康与偏好</text><view class="form-grid">
					<label v-for="f in detailFields" :key="f.key" class="form-field" :class="{full:f.full}"><text>{{f.label}}</text><textarea v-if="f.full" v-model="detail[f.key]"/><input v-else v-model="detail[f.key]"/></label>
				</view><view class="button-row"><button class="action-button" @click="saveDetail">保存详细资料</button><button class="secondary-button" @click="previewDocument">预览知识文档</button></view></view>
				<view class="card panel"><text class="panel-title">成长记录</text>
					<view v-if="!growth.length" class="empty-inline">还没有成长记录</view><view v-else class="data-list"><view v-for="item in growth" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.title||item.record_type}}</text><text class="data-meta">{{item.content||'无补充内容'}}</text></view><button class="danger-button" @click="deleteGrowth(item.id)">删除</button></view></view>
					<view class="form-grid"><label class="form-field"><text>记录类型</text><input v-model="growthForm.record_type"/></label><label class="form-field"><text>标题</text><input v-model="growthForm.title"/></label><label class="form-field full"><text>内容</text><textarea v-model="growthForm.content"/></label></view><view class="button-row"><button class="action-button" @click="addGrowth">添加记录</button></view>
				</view>
				<view class="card panel"><text class="panel-title">健康提醒</text>
					<view v-if="!reminders.length" class="empty-inline">还没有健康提醒</view><view v-else class="data-list"><view v-for="item in reminders" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.title}}</text><text class="data-meta">{{item.due_at}} · {{item.status}}</text></view><button class="secondary-button" @click="completeReminder(item)">完成</button><button class="danger-button" @click="deleteReminder(item.id)">删除</button></view></view>
					<view class="form-grid"><label class="form-field"><text>提醒类型</text><input v-model="reminderForm.reminder_type"/></label><label class="form-field"><text>标题</text><input v-model="reminderForm.title"/></label><label class="form-field full"><text>时间（ISO 格式）</text><input v-model="reminderForm.due_at" placeholder="2026-07-30T09:00:00"/></label></view><view class="button-row"><button class="action-button" @click="addReminder">添加提醒</button></view>
				</view>
			</view>
		</template>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{petApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{id:null,pet:null,base:{},detail:{},growth:[],reminders:[],completeness:{},loading:true,growthForm:{record_type:'note',title:'',content:''},reminderForm:{reminder_type:'health',title:'',due_at:''},baseFields:[{key:'name',label:'名字'},{key:'pet_type',label:'类型'},{key:'breed',label:'品种'},{key:'gender',label:'性别'},{key:'weight',label:'体重',type:'number'},{key:'vaccine_status',label:'疫苗状态'},{key:'deworm_status',label:'驱虫状态'},{key:'avatar',label:'头像 URL'}],detailFields:[{key:'body_size',label:'体型'},{key:'health_notes',label:'健康说明',full:true},{key:'allergy_notes',label:'过敏说明',full:true},{key:'diet_preference',label:'饮食偏好',full:true},{key:'product_preference',label:'用品偏好',full:true},{key:'behavior_notes',label:'行为特点',full:true},{key:'care_notes',label:'照护说明',full:true}]}},onLoad(q){this.id=q.id;this.load()},methods:{
	async load(){this.loading=true;const r=await Promise.allSettled([petApi.detail(this.id),petApi.detailProfile(this.id),petApi.listGrowthRecords(this.id),petApi.listReminders(this.id),petApi.profileCompleteness(this.id)]);if(r[0].status==='fulfilled'){this.pet=r[0].value;this.base={...r[0].value}}if(r[1].status==='fulfilled')this.detail={...r[1].value};if(r[2].status==='fulfilled')this.growth=r[2].value||[];if(r[3].status==='fulfilled')this.reminders=r[3].value||[];if(r[4].status==='fulfilled')this.completeness=r[4].value||{};this.loading=false},
	async saveBase(){try{const keys=this.baseFields.map(v=>v.key);const data={};keys.forEach(k=>data[k]=this.base[k]||null);if(data.weight)data.weight=Number(data.weight);this.pet=await petApi.update(this.id,data);uni.showToast({title:'基础资料已保存'});this.load()}catch(e){}},
	async saveDetail(){try{await petApi.updateDetailProfile(this.id,this.detail);uni.showToast({title:'详细资料已保存'});this.load()}catch(e){}},
	async addGrowth(){if(!this.growthForm.record_type)return uni.showToast({title:'请填写记录类型',icon:'none'});try{await petApi.createGrowthRecord(this.id,this.growthForm);this.growthForm={record_type:'note',title:'',content:''};uni.showToast({title:'成长记录已添加'});this.load()}catch(e){}},
	async deleteGrowth(id){try{await petApi.deleteGrowthRecord(this.id,id);uni.showToast({title:'记录已删除'});this.load()}catch(e){}},
	async addReminder(){if(!this.reminderForm.title||!this.reminderForm.due_at)return uni.showToast({title:'请填写提醒标题和时间',icon:'none'});try{await petApi.createReminder(this.id,this.reminderForm);this.reminderForm={reminder_type:'health',title:'',due_at:''};uni.showToast({title:'提醒已添加'});this.load()}catch(e){}},
	async completeReminder(item){try{await petApi.updateReminder(this.id,item.id,{status:'completed'});uni.showToast({title:'提醒已完成'});this.load()}catch(e){}},
	async deleteReminder(id){try{await petApi.deleteReminder(this.id,id);uni.showToast({title:'提醒已删除'});this.load()}catch(e){}},
	async previewDocument(){try{const r=await petApi.previewProfileDocument(this.id);uni.showModal({title:'档案文档预览',content:r.content,showCancel:false})}catch(e){}},
	async removePet(){uni.showModal({title:'删除宠物档案',content:'删除后相关资料也会受到影响，确认继续吗？',success:async r=>{if(!r.confirm)return;try{await petApi.remove(this.id);uni.showToast({title:'档案已删除'});setTimeout(()=>uni.navigateBack(),400)}catch(e){}}})}
}}
</script>
