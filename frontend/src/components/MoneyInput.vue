<template>
	<input
		:id="id"
		:name="name"
		:aria-label="ariaLabel || name || 'Amount input'"
		type="text"
		inputmode="decimal"
		:value="displayValue"
		@focus="focused = true"
		@blur="focused = false"
		@input="$emit('input', $event)"
		class="num"
	/>
</template>

<script setup>
import { ref, computed } from "vue";
import { money } from "../format";

// Shows comma-formatted text (e.g. "2,222,222.00") when not focused, and the
// plain unformatted value while actively typing - native number inputs can't
// display thousand separators without breaking editing.
const props = defineProps({
	value: { type: [Number, String], default: 0 },
	id: { type: String, default: undefined },
	name: { type: String, default: undefined },
	ariaLabel: { type: String, default: undefined },
});
defineEmits(["input"]);

const focused = ref(false);
const displayValue = computed(() => (focused.value ? props.value : money(props.value)));
</script>
