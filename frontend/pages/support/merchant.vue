<template>
	<SupportChatWindow v-if="id" active="mall" :conversation-id="id" :role="role" scene="merchant" />
</template>

<script>
import SupportChatWindow from '../../components/SupportChatWindow.vue'

export default {
	components: { SupportChatWindow },
	data() {
		return {
			id: 0,
			role: 'user'
		}
	},
	onLoad(query) {
		this.id = Number(query.id)
		this.role = query.role || 'user'
	}
}
</script>
