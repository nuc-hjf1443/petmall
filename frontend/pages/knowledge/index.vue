<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">私人知识库</text><text class="page-subtitle">文件、宠物档案与 AI 问答按用户隔离</text></view></view>
		<view class="content-grid">
			<view class="card panel"><text class="panel-title">知识库</text>
				<view class="form-grid"><label class="form-field full"><text>新知识库名称</text><input v-model="name" placeholder="例如：团子的健康资料"/></label></view><view class="button-row"><button class="action-button" @click="create">创建</button></view>
				<view v-if="loading" class="empty-inline">正在加载知识库…</view><view v-else-if="!bases.length" class="empty-inline">还没有知识库</view>
				<view v-else class="data-list"><view v-for="item in bases" :key="item.id" class="data-row" @click="select(item)"><view class="data-main"><text class="data-title">{{item.name}}</text><text class="data-meta">{{item.scope}} · {{item.created_at}}</text></view><text v-if="current?.id===item.id" class="status-chip">当前</text><button class="danger-button" @click.stop="removeBase(item.id)">删除</button></view></view>
			</view>
			<view class="card panel"><text class="panel-title">{{current?current.name:'文档管理'}}</text>
				<StatePanel v-if="!current" icon="▤" title="请选择一个知识库"/>
				<template v-else>
					<view class="button-row"><button class="action-button" @click="chooseDocument">上传文件</button><button class="secondary-button" @click="loadPets">从宠物档案生成</button></view>
					<view v-if="showPets" class="pet-picker"><view v-for="pet in pets" :key="pet.id" @click="generate(pet.id)">{{pet.name}} · 生成档案文档</view></view>
					<view v-if="!documents.length" class="empty-inline">当前知识库还没有文档</view><view v-else class="data-list"><view v-for="doc in documents" :key="doc.id" class="data-row"><view class="data-main"><text class="data-title">{{doc.file_name}}</text><text class="data-meta">{{doc.source_type}} · {{doc.parse_status}} · {{doc.chunk_count}} 个分块</text></view><button class="secondary-button" @click="reindex(doc.id)">重建索引</button><button class="danger-button" @click="removeDocument(doc.id)">删除</button></view></view>
				</template>
			</view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{knowledgeApi,petApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{name:'',bases:[],current:null,documents:[],pets:[],loading:true,showPets:false}},onShow(){this.load()},methods:{
	async load(){this.loading=true;try{this.bases=await knowledgeApi.list()||[];if(this.current){this.current=this.bases.find(v=>v.id===this.current.id)||null;if(this.current)await this.loadDocuments()}}catch(e){}finally{this.loading=false}},
	async create(){if(!this.name.trim())return uni.showToast({title:'请输入知识库名称',icon:'none'});try{const item=await knowledgeApi.create({name:this.name.trim()});this.name='';uni.showToast({title:'知识库已创建'});await this.load();this.select(item)}catch(e){}},
	async select(item){this.current=item;this.showPets=false;await this.loadDocuments()},
	async loadDocuments(){try{this.documents=await knowledgeApi.documents(this.current.id)||[]}catch(e){this.documents=[]}},
	chooseDocument(){const done=async res=>{const path=res.tempFiles?.[0]?.path||res.tempFilePaths?.[0];if(!path)return;try{await knowledgeApi.uploadDocument(this.current.id,path);uni.showToast({title:'文档已提交解析'});this.loadDocuments()}catch(e){}};if(uni.chooseFile)uni.chooseFile({count:1,success:done});else uni.chooseMessageFile({count:1,type:'file',success:done})},
	async loadPets(){try{this.pets=await petApi.list()||[];this.showPets=true;if(!this.pets.length)uni.showToast({title:'请先创建宠物档案',icon:'none'})}catch(e){}},
	async generate(petId){try{await knowledgeApi.previewGeneratedDocument(this.current.id,petId);await knowledgeApi.generateFromPet(this.current.id,petId);uni.showToast({title:'宠物档案文档已生成'});this.showPets=false;this.loadDocuments()}catch(e){}},
	async reindex(id){try{await knowledgeApi.reindexDocument(this.current.id,id);uni.showToast({title:'已提交重建索引'});this.loadDocuments()}catch(e){}},
	async removeDocument(id){try{await knowledgeApi.deleteDocument(this.current.id,id);uni.showToast({title:'文档删除任务已提交'});this.loadDocuments()}catch(e){}},
	async removeBase(id){try{await knowledgeApi.remove(id);if(this.current?.id===id){this.current=null;this.documents=[]}uni.showToast({title:'知识库删除任务已提交'});this.load()}catch(e){}}
}}
</script>
<style scoped>.pet-picker{margin-top:12px;padding:10px;border-radius:10px;background:var(--color-primary-soft)}.pet-picker view{padding:10px;color:var(--color-primary);font-size:12px}</style>
