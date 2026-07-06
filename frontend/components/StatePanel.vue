<template>
	<view class="state-panel">
		<text class="state-icon">{{ icon }}</text>
		<text class="state-title">{{ title }}</text>
		<text v-if="description" class="state-description">{{ description }}</text>
		<button v-if="action" class="state-action" @click="$emit('action')">{{ action }}</button>
	</view>
</template>
<script>
export default {
	props: ['icon', 'title', 'description', 'action'],
	emits: ['action']
}
</script>
<style scoped>
.state-panel { display:flex; min-height:220px; flex-direction:column; align-items:center; justify-content:center; padding:30px; text-align:center; }
.state-icon { font-size:42px; }
.state-title { margin-top:12px; font-size:17px; font-weight:700; }
.state-description { margin-top:8px; color:#817972; font-size:13px; }
.state-action { margin-top:18px; padding:0 22px; border:1px solid #ff7417; border-radius:22px; background:#fff; color:#ff7417; font-size:13px; }
</style>
