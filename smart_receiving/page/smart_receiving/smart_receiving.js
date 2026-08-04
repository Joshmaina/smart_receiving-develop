function init_smart_receiving_page(wrapper) {
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
        } else {
            // eslint-disable-next-line no-console
            console.error("Smart Receiving: window.smart_receiving_mount is not defined.");
        }
    }

    if (window.smart_receiving_mount) {
        boot();
    } else {
        const script = document.createElement("script");
        script.src = "/assets/smart_receiving/dist/js/smart_receiving.js?v=" + v;
        script.onload = boot;
        document.head.appendChild(script);
    }
}

function unload_smart_receiving_page(wrapper) {
    if (wrapper.smart_receiving_app) {
        if (window.smart_receiving_unmount) {
            window.smart_receiving_unmount();
        }
        wrapper.smart_receiving_app = null;
    }
}

frappe.pages['smart_receiving'] = frappe.pages['smart_receiving'] || {};
frappe.pages['smart-receiving'] = frappe.pages['smart-receiving'] || {};

frappe.pages['smart_receiving'].on_page_load = init_smart_receiving_page;
frappe.pages['smart-receiving'].on_page_load = init_smart_receiving_page;
frappe.pages['smart_receiving'].on_page_unload = unload_smart_receiving_page;
frappe.pages['smart-receiving'].on_page_unload = unload_smart_receiving_page;
