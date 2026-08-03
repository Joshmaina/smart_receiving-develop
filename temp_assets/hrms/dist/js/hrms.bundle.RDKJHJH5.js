(()=>{frappe.templates.employees_with_unmarked_attendance=`{% if data.length %}

<div class="form-message yellow">
	<div>
		{{
			__(
				"Attendance is pending for these employees between the selected payroll dates. Mark attendance to proceed. Refer {0} for details.",
				["<a href='/app/query-report/Monthly%20Attendance%20Sheet'>Monthly Attendance Sheet</a>"]
			)
		}}
	</div>
</div>

<table class="table table-bordered small">
	<thead>
		<tr>
			<th style="width: 14%" class="text-left">{{ __("Employee") }}</th>
			<th style="width: 16%" class="text-left">{{ __("Employee Name") }}</th>
			<th style="width: 12%" class="text-left">{{ __("Unmarked Days") }}</th>
		</tr>
	</thead>
	<tbody>
		{% for item in data %}
			<tr>
				<td class="text-left"> {{ item.employee }} </td>
				<td class="text-left"> {{ item.employee_name }} </td>
				<td class="text-left"> {{ item.unmarked_days }} </td>
			</tr>
		{% } %}
	</tbody>
</table>

{% } else { %}

<div class="form-message green">
	<div>{{ __("Attendance has been marked for all the employees between the selected payroll dates.") }}</div>
</div>

{% } %}`;frappe.templates.feedback_summary=`<div class="feedback-summary-section my-4 d-flex">
	<!-- Ratings Summary -->
	<div class="rating-summary-numbers col-3">
		<div class="feedback-count mt-1 mb-2 text-secondary">
			{{ __("Average Rating") }}
		</div>
		<h2 class="average-rating mb-2">{{ average_rating }}</h2>

		{%=
			frappe.render_template("rating",
				{number_of_stars: 5, average_rating: average_rating, for_summary: true}
			)
		%}

		<div class="feedback-count text-secondary mt-2">
			{{ __("based on") }} {{ cstr(feedback_count) }} {{ feedback_count > 1 ? __("reviews") : __("review") }}
		</div>
	</div>

	<!-- Rating Progress Bars -->
	<div class="rating-progress-bar-section pb-0 col-4">
		{% for(let i=5; i>0; i--) { %}
		<div class="row {{ i!=1 && 'mb-3' }}">
			<div class="col-sm-3 text-nowrap flex align-items-center">
				<svg class="icon icon-sm mr-2">
					<use href="#icon-star" class="like-icon"></use>
				</svg>
				<span>{{ i }}</span>
			</div>
			<div class="col-md-7">
				<div
					class="progress rating-progress-bar"
					title="{{ reviews_per_rating[i-1] }} % of reviews are {{ i }} star"
				>
					<div
						class="progress-bar progress-bar-cosmetic"
						role="progressbar"
						aria-valuenow="{{ reviews_per_rating[i-1] }}"
						aria-valuemin="0"
						aria-valuemax="100"
						style="width: {{ reviews_per_rating[i-1] }}%;"
					></div>
				</div>
			</div>
			<div class="col-sm-1 small">{{ reviews_per_rating[i-1] }}%</div>
		</div>
		{% } %}
	</div>
</div>
`;frappe.templates.feedback_history=`<div class="feedback-history mb-3">
	{% if (feedback_history.length) { %}
		{% for (let i=0, l=feedback_history.length; i<l; i++) { %}
			<div class="feedback-content p-3 d-flex flex-row mt-3" data-name="{{ feedback_history[i].name }}">
				<!-- Reviewer Info -->
				<div class="reviewer-info mb-2 col-xs-3">
					<div class="row">
						<div class="col-xs-2">
							{{ frappe.avatar(feedback_history[i].user, "avatar-medium") }}
						</div>
						<div class="col-xs-10">
							<div class="ml-2">
								<div class="title font-weight-bold">
									{{ strip_html(feedback_history[i].reviewer_name || feedback_history[i].user) }}
								</div>
								{% if (feedback_history[i].reviewer_designation) { %}
									<div class="small text-muted">
										{{ strip_html(feedback_history[i].reviewer_designation) }}
									</div>
								{% } %}
							</div>
						</div>
					</div>
				</div>

				<!-- Feedback -->
				<div class="reviewer-feedback col-xs-6">
					<div class="rating">
						{%= frappe.render_template("rating",
								{number_of_stars: 5, average_rating: feedback_history[i].total_score, for_summary: false}
							)
						%}
					</div>
					<div class="feedback my-3">
						{{ feedback_history[i].feedback }}
					</div>
				</div>

				<!-- Feedback Date & Link -->
				<div class="feedback-info col-xs-3 d-flex flex-row justify-content-end align-items-baseline">
					<div class="time small text-muted mr-2">
						{{ frappe.datetime.comment_when(feedback_history[i].added_on) }}
					</div>
					<a href="{{ frappe.utils.get_form_link(feedback_doctype, feedback_history[i].name) }}" title="{{ __("Open Feedback") }}">
						<svg class="icon icon-sm">
							<use href="#icon-link-url"></use>
						</svg>
					</a>
				</div>
			</div>
		{% } %}

	{% } else { %}
		<div class="no-feedback d-flex flex-col justify-content-center align-items-center text-muted">
			<span>{{ __("No feedback has been received yet") }}</span>
		</div>
	{% } %}
</div>`;frappe.templates.rating=`<div class="d-flex flex-col">
	<div class="rating {{ for_summary ? 'ratings-pill' : ''}}">
		{% for (let i = 1; i <= number_of_stars; i++) { %}
			{% if (i <= average_rating) { %}
				{% right_class = 'star-click'; %}
			{% } else { %}
				{% right_class = ''; %}
			{% } %}

			{% if ((i <= average_rating) || ((i - 0.5) == average_rating)) { %}
				{% left_class = 'star-click'; %}
			{% } else { %}
				{% left_class = ''; %}
			{% } %}

			<svg class="icon icon-md" data-rating={{i}} viewBox="0 0 24 24" fill="none">
				<path class="right-half {{ right_class }}" d="M11.9987 3.00011C12.177 3.00011 12.3554 3.09303 12.4471 3.27888L14.8213 8.09112C14.8941 8.23872 15.0349 8.34102 15.1978 8.3647L20.5069 9.13641C20.917 9.19602 21.0807 9.69992 20.7841 9.9892L16.9421 13.7354C16.8243 13.8503 16.7706 14.0157 16.7984 14.1779L17.7053 19.4674C17.7753 19.8759 17.3466 20.1874 16.9798 19.9945L12.2314 17.4973C12.1586 17.459 12.0786 17.4398 11.9987 17.4398V3.00011Z" fill="var(--star-fill)" stroke="var(--star-fill)"/>
				<path class="left-half {{ left_class }}" d="M11.9987 3.00011C11.8207 3.00011 11.6428 3.09261 11.5509 3.27762L9.15562 8.09836C9.08253 8.24546 8.94185 8.34728 8.77927 8.37075L3.42887 9.14298C3.01771 9.20233 2.85405 9.70811 3.1525 9.99707L7.01978 13.7414C7.13858 13.8564 7.19283 14.0228 7.16469 14.1857L6.25116 19.4762C6.18071 19.8842 6.6083 20.1961 6.97531 20.0045L11.7672 17.5022C11.8397 17.4643 11.9192 17.4454 11.9987 17.4454V3.00011Z" fill="var(--star-fill)" stroke="var(--star-fill)"/>
			</svg>
		{% } %}
	</div>
	{% if (!for_summary) { %}
		<p class="ml-3" style="line-height: 2;">
			({{ flt(average_rating, 2) }})
		</p>
	{% } %}
</div>
`;frappe.provide("hrms");$.extend(hrms,{proceed_save_with_reminders_frequency_change:()=>{frappe.ui.hide_open_dialog(),frappe.call({method:"hrms.hr.doctype.hr_settings.hr_settings.set_proceed_with_frequency_change",callback:()=>{cur_frm.save()}})},set_payroll_frequency_to_null:e=>{cint(e.doc.salary_slip_based_on_timesheet)&&e.set_value("payroll_frequency","")},get_current_employee:async e=>{var a,r;return(r=(a=await frappe.db.get_value("Employee",{user_id:frappe.session.user},"name"))==null?void 0:a.message)==null?void 0:r.name},validate_mandatory_fields:(e,t,a="Employees")=>{let r=[];for(d in e.fields_dict)e.fields_dict[d].df.reqd&&!e.doc[d]&&d!=="__newname"&&r.push(e.fields_dict[d].df.label);if(r.length){let s=__("Mandatory fields required for this action:");s+="<br><br><ul><li>"+r.join("</li><li>")+"</ul>",frappe.throw({message:s,title:__("Missing Fields")})}t.length||frappe.throw({message:__("Please select at least one row to perform this action."),title:__("No {0} Selected",[__(a)])})},setup_employee_filter_group:e=>{let t=e.fields_dict.filter_list.$wrapper;t.empty(),frappe.model.with_doctype("Employee",()=>{e.filter_list=new frappe.ui.FilterGroup({parent:t,doctype:"Employee",on_change:()=>{e.advanced_filters=e.filter_list.get_filters().reduce((a,r)=>(r[3]&&a.push(r.slice(1,4)),a),[]),e.trigger("get_employees")}})})},render_employees_datatable:(e,t,a,r=__("No Data"),s=null,n={})=>{if(e.set_df_property("quick_filters_section","collapsible",0),e.set_df_property("advanced_filters_section","collapsible",0),e.employees_datatable){e.employees_datatable.rowmanager.checkMap=[],e.employees_datatable.options.noDataMessage=r,e.employees_datatable.refresh(a,t);return}let l=e.get_field("employees_html").$wrapper,i=$('<div class="employee_wrapper">').appendTo(l),o={columns:t,data:a,checkboxColumn:!0,checkedRowStatus:!1,serialNoColumn:!1,dynamicRowHeight:!0,inlineFilters:!0,layout:"fluid",cellHeight:35,noDataMessage:r,disableReorderColumn:!0,getEditor:s,events:n};e.employees_datatable=new frappe.DataTable(i.get(0),o)},handle_realtime_bulk_action_notification:(e,t,a)=>{frappe.realtime.off(t),frappe.realtime.on(t,r=>{hrms.notify_bulk_action_status(a,r.failure,r.success,r.for_processing),r.success&&e.refresh()})},notify_bulk_action_status:(e,t,a,r=!1)=>{let s=__("create/submit"),n=__("created");r&&(s=__("process"),n=__("processed"));let l="",i=__("Success"),o="green";if(t.length&&(l+=__("Failed to {0} {1} for employees:",[s,e]),l+=" "+frappe.utils.comma_and(t)+"<hr>",l+=__("Check <a href='/app/List/Error Log?reference_doctype={0}'>{1}</a> for more details",[e,__("Error Log")]),i=__("Failure"),o="red",a.length&&(l+="<hr>",i=__("Partial Success"),o="orange")),a.length){l+=__("Successfully {0} {1} for the following employees:",[n,e]),l+=__("<table class='table table-bordered'><tr><th>{0}</th><th>{1}</th></tr>",[__("Employee"),e]);for(let _ of a)l+=`<tr><td>${_.employee}</td><td>${_.doc}</td></tr>`;l+="</table>"}frappe.msgprint({message:l,title:i,indicator:o,is_minimizable:!0})},fetch_geolocation:async e=>{if(!navigator.geolocation){frappe.msgprint({message:__("Geolocation is not supported by your current browser"),title:__("Geolocation Error"),indicator:"red"}),hide_field(["geolocation"]);return}frappe.dom.freeze(__("Fetching your geolocation")+"..."),navigator.geolocation.getCurrentPosition(async t=>{frappe.run_serially([()=>e.set_value("latitude",t.coords.latitude),()=>e.set_value("longitude",t.coords.longitude),()=>e.call("set_geolocation"),()=>frappe.dom.unfreeze()])},t=>{frappe.dom.unfreeze();let a=__("Unable to retrieve your location")+"<br><br>";t&&(a+=__("ERROR({0}): {1}",[t.code,t.message])),frappe.msgprint({message:a,title:__("Geolocation Error"),indicator:"red"})})},get_doctype_fields_for_autocompletion:e=>{let t=frappe.get_meta(e).fields,a=[];return t.filter(r=>!frappe.model.no_value_type.includes(r.fieldtype)).map(r=>{a.push({value:r.fieldname,score:8,meta:__("{0} Field",[e])})}),a},add_shift_tools_button_to_list:(e,t="Assign Shift")=>{e.page.add_inner_button(__("Shift Assignment Tool"),()=>{let a=frappe.model.get_new_doc("Shift Assignment Tool");a.action=t,a.company=frappe.defaults.get_default("company"),a.status="Active",frappe.set_route("Form","Shift Assignment Tool",a.name)},__("Shift Tools")),e.page.add_inner_button(__("Roster"),()=>{window.location.href="/hr/roster"},__("Shift Tools"))},add_shift_tools_button_to_form:(e,t)=>{e.add_custom_button(__("Shift Assignment Tool"),()=>{let a=frappe.model.get_new_doc("Shift Assignment Tool");Object.assign(a,t),a.company=frappe.defaults.get_default("company"),a.status="Active",frappe.set_route("Form","Shift Assignment Tool",a.name)},__("Shift Tools")),e.add_custom_button(__("Roster"),()=>{window.location.href="/hr/roster"},__("Shift Tools"))}});hrms.payroll_utils={set_autocompletions_for_condition_and_formula:function(e,t=""){let a=[];frappe.run_serially([...["Employee","Salary Structure","Salary Structure Assignment","Salary Slip"].map(r=>frappe.model.with_doctype(r,()=>{a.push(...hrms.get_doctype_fields_for_autocompletion(r))})),()=>{frappe.db.get_list("Salary Component",{fields:["salary_component_abbr"]}).then(r=>{a.push(...r.map(s=>({value:s.salary_component_abbr,score:9,meta:__("Salary Component")}))),a.push(...["base","variable"].map(s=>({value:s,score:10,meta:__("Salary Structure Assignment field")}))),t?(["condition","formula"].forEach(s=>{e.set_df_property(t.parentfield,"autocompletions",a,e.doc.name,s,t.name)}),e.refresh_field(t.parentfield)):["condition","formula"].forEach(s=>{e.set_df_property(s,"autocompletions",a)})})}])}};hrms.leave_utils={add_view_ledger_button(e){e.doc.__islocal||e.doc.docstatus!=1||e.add_custom_button(__("View Ledger"),()=>{frappe.route_options={from_date:e.doc.from_date,to_date:e.doc.to_date,transaction_type:e.doc.doctype,transaction_name:e.doc.name},frappe.set_route("query-report","Leave Ledger")})}};frappe.provide("hrms.salary_slip_deductions_report_filters");hrms.salary_slip_deductions_report_filters={filters:[{fieldname:"company",label:__("Company"),fieldtype:"Link",options:"Company",reqd:1,default:frappe.defaults.get_user_default("Company")},{fieldname:"month",label:__("Month"),fieldtype:"Select",reqd:1,options:[{value:1,label:__("Jan")},{value:2,label:__("Feb")},{value:3,label:__("Mar")},{value:4,label:__("Apr")},{value:5,label:__("May")},{value:6,label:__("June")},{value:7,label:__("July")},{value:8,label:__("Aug")},{value:9,label:__("Sep")},{value:10,label:__("Oct")},{value:11,label:__("Nov")},{value:12,label:__("Dec")}],default:frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()+1},{fieldname:"year",label:__("Year"),fieldtype:"Select",reqd:1},{fieldname:"department",label:__("Department"),fieldtype:"Link",options:"Department"},{fieldname:"branch",label:__("Branch"),fieldtype:"Link",options:"Branch"}],onload:function(){return frappe.call({method:"hrms.payroll.report.provident_fund_deductions.provident_fund_deductions.get_years",callback:function(e){var t=frappe.query_report.get_filter("year");t.df.options=e.message,t.df.default=e.message.split(`
`)[0],t.refresh(),t.set_input(t.df.default)}})}};})();
//# sourceMappingURL=hrms.bundle.RDKJHJH5.js.map
