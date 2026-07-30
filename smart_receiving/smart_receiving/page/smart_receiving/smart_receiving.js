frappe.pages["smart-receiving"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Smart Receiving",
		single_column: true,
	});

	// Fixed filenames (no content hash) during Phase 1 dev, so cache-bust with
	// a timestamp to avoid stale bundles - swap for a real build hash later.
	const v = Date.now();

	const existingLink = document.getElementById("smart-receiving-css");
	if (existingLink) existingLink.remove();
	const link = document.createElement("link");
	link.id = "smart-receiving-css";
	link.rel = "stylesheet";
	link.href = "/assets/smart_receiving/dist/js/smart_receiving.css?v=" + v;
	document.head.appendChild(link);

	function boot() {
		wrapper.smart_receiving_app = window.smart_receiving_mount(page.body.get(0));
	}

	const script = document.createElement("script");
	script.type = "module";
	script.src = "/assets/smart_receiving/dist/js/smart_receiving.js?v=" + v;
	script.onload = boot;
	document.head.appendChild(script);
};

frappe.pages["smart-receiving"].on_page_unload = function (wrapper) {
	if (wrapper.smart_receiving_app) {
		window.smart_receiving_unmount();
		wrapper.smart_receiving_app = null;
	}
};
