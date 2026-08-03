// Ensure wrapper object exists regardless of hyphenation vs underscore
if (!frappe.pages['smart-receiving'] && !frappe.pages['smart_receiving']) {
    frappe.pages['smart-receiving'] = {};
}

const page_key = frappe.pages['smart-receiving'] ? 'smart-receiving' : 'smart_receiving';

frappe.pages[page_key].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Smart Receiving",
        single_column: true,
    });

    const v = Date.now();

    const existingLink = document.getElementById("smart-receiving-css");
    if (existingLink) existingLink.remove();
    const link = document.createElement("link");
    link.id = "smart-receiving-css";
    link.rel = "stylesheet";
    link.href = "/assets/smart_receiving/dist/js/smart_receiving.css?v=" + v;
    document.head.appendChild(link);

    function boot() {
        if (window.smart_receiving_mount) {
            wrapper.smart_receiving_app = window.smart_receiving_mount(page.body.get(0));
        }
    }

    const script = document.createElement("script");
    script.type = "module";
    script.src = "/assets/smart_receiving/dist/js/smart_receiving.js?v=" + v;
    script.onload = boot;
    document.head.appendChild(script);
};

frappe.pages[page_key].on_page_unload = function (wrapper) {
    if (wrapper.smart_receiving_app) {
        if (window.smart_receiving_unmount) {
            window.smart_receiving_unmount();
        }
        wrapper.smart_receiving_app = null;
    }
};
