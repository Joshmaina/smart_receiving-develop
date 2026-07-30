import { createApp } from "vue";
import App from "./App.vue";

let app = null;

export function mount(el) {
	app = createApp(App);
	app.mount(el);
	return app;
}

export function unmount() {
	if (app) {
		app.unmount();
		app = null;
	}
}

window.smart_receiving_mount = mount;
window.smart_receiving_unmount = unmount;
