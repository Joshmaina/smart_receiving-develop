import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
	plugins: [vue()],
	base: "/assets/smart_receiving/dist/js/",
	build: {
		target: "esnext",
		outDir: "../smart_receiving/public/dist/js",
		emptyOutDir: true,
		cssCodeSplit: false,
		rollupOptions: {
			input: "src/main.js",
			output: {
				entryFileNames: "smart_receiving.js",
				assetFileNames: "smart_receiving.[ext]",
			},
		},
	},
});
