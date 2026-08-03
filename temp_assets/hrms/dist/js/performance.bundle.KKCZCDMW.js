(()=>{frappe.provide("hrms");hrms.PerformanceFeedback=class{constructor({frm:e,wrapper:a}){this.frm=e,this.wrapper=a}refresh(){this.prepare_dom(),this.setup_feedback_view()}prepare_dom(){this.wrapper.find(".feedback-section").remove()}setup_feedback_view(){frappe.run_serially([()=>this.get_feedback_history(),e=>this.render_feedback_history(e),()=>this.setup_actions()])}get_feedback_history(){let e=this;return new Promise(a=>{frappe.call({method:"hrms.hr.doctype.appraisal.appraisal.get_feedback_history",args:{employee:e.frm.doc.employee,appraisal:e.frm.doc.name}}).then(r=>a(r.message))})}async render_feedback_history(e){let{feedback_history:a,reviews_per_rating:r,avg_feedback_score:t}=e||{},i=await this.can_create(),s=frappe.render_template("performance_feedback",{feedback_history:a,average_feedback_score:t,reviews_per_rating:r,can_create:i});$(this.wrapper).empty(),$(s).appendTo(this.wrapper)}setup_actions(){let e=this;$(".new-feedback-btn").click(()=>{e.add_feedback()})}add_feedback(){frappe.run_serially([()=>this.get_feedback_criteria_data(),e=>this.show_add_feedback_dialog(e)])}get_feedback_criteria_data(){let e=this;return new Promise(a=>{frappe.db.get_doc("Appraisal Template",e.frm.doc.appraisal_template).then(({rating_criteria:r})=>{let t=[];r.forEach(i=>{t.push({criteria:i.criteria,per_weightage:i.per_weightage})}),a(t)})})}show_add_feedback_dialog(e){let a=this,r=new frappe.ui.Dialog({title:__("Add Feedback"),fields:a.get_feedback_dialog_fields(e),size:"large",minimizable:!0,primary_action_label:__("Submit"),primary_action:function(){let t=r.get_values();frappe.call({method:"add_feedback",doc:a.frm.doc,args:{feedback:t.feedback,feedback_ratings:t.feedback_ratings},freeze:!0,callback:function(i){var s,c;i.exc||(frappe.run_serially([()=>a.frm.refresh_fields(),()=>a.refresh()]),frappe.show_alert({message:__("Feedback {0} added successfully",[(c=(s=i.message)==null?void 0:s.name)==null?void 0:c.bold()]),indicator:"green"})),r.hide()}})}});r.show()}get_feedback_dialog_fields(e){return[{label:"Feedback",fieldname:"feedback",fieldtype:"Text Editor",reqd:1,enable_mentions:!0},{label:"Feedback Rating",fieldtype:"Table",fieldname:"feedback_ratings",cannot_add_rows:!0,data:e,fields:[{fieldname:"criteria",fieldtype:"Link",in_list_view:1,label:"Criteria",options:"Employee Feedback Criteria",reqd:1},{fieldname:"per_weightage",fieldtype:"Percent",in_list_view:1,label:"Weightage"},{fieldname:"rating",fieldtype:"Rating",in_list_view:1,label:"Rating"}]}]}async can_create(){var a,r;return(((r=(a=await frappe.db.get_value("Employee",{user_id:frappe.session.user},"name"))==null?void 0:a.message)==null?void 0:r.name)||!1)&&frappe.model.can_create("Employee Performance Feedback")}};frappe.templates.performance_feedback=`<div class="feedback-section col-xs-12">
	{% if (feedback_history.length) { %}
		<div class="feedback-summary mb-5 pb-2">
			{%=
				frappe.render_template(
					"feedback_summary",
					{
						number_of_stars: 5,
						average_rating: average_feedback_score,
						feedback_count: feedback_history.length,
						reviews_per_rating: reviews_per_rating
					}
				)
			%}
		</div>
	{% } %}

	{% if (can_create) { %}
		<div class="new-btn pb-3 text-right">
			<button
				class="new-feedback-btn btn btn-sm d-inline-flex align-items-center justify-content-center px-3 py-2 border"
			>
				<svg class="icon icon-sm">
					<use href="#icon-add"></use>
				</svg>
				{{ __("New Feedback") }}
			</button>
		</div>
	{% } %}

	{%=
		frappe.render_template(
			"feedback_history",
			{ feedback_history: feedback_history, feedback_doctype: "Employee Performance Feedback" }
		)
	%}
</div>
`;})();
//# sourceMappingURL=performance.bundle.KKCZCDMW.js.map
