from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):

    _inherit = "ir.http"

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    def session_info(self):
        result = super(IrHttp, self).session_info()
        user = getattr(request.env, "user", None) if request.env else None
        if user and hasattr(user, "_is_internal") and user._is_internal():
            for company in user.company_ids.with_context(bin_size=True):
                result['user_companies']['allowed_companies'][company.id].update({
                    'has_appsbar_image': bool(company.appbar_image),
                })
        return result
