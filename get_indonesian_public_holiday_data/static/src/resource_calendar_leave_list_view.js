import { registry } from "@web/core/registry"
import { listView } from "@web/views/list/list_view"
import { ListController } from "@web/views/list/list_controller"
import { useService } from "@web/core/utils/hooks"

class ResourceCalendarLeaveListController extends ListController {
    setup(){
        super.setup()
        this.action = useService("action")
    }

    openFetchHolidayWizard(){
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fetch.holiday.wizard",
            views: [[false, "form"]],
            target: "new",
        })
    }
}

export const resourceCalendarLeaveListView = {
    ...listView,
    Controller: ResourceCalendarLeaveListController,
    buttonTemplate: "ResourceCalendarLeaveListView.Buttons",
}

registry.category("views").add("resource_calendar_leaves_list_view", resourceCalendarLeaveListView)