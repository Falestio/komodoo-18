import requests
import re
from datetime import datetime, timedelta
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FetchHolidayWizard(models.TransientModel):
    _name = 'fetch.holiday.wizard'
    _description = 'Fetch Indonesian Public Holiday Wizard'

    year = fields.Integer(string='Tahun', required=True, default=lambda self: datetime.now().year)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Bulan (Optional)')
    include_cuti_bersama = fields.Boolean(string='Ambil Libur Cuti', default=True, 
                                         help="Jika di centang libur 'Cuti Bersama' akan diambil juga.")
    
    def fetch_holidays(self):
        self.ensure_one()
        
        base_url = "https://dayoffapi.vercel.app/api"
        params = {}
        
        if self.year:
            params['year'] = self.year
        
        if self.month:
            params['month'] = self.month
            
        try:
            query_string = '?' + '&'.join([f"{k}={v}" for k, v in params.items()]) if params else ''
            url = base_url + query_string
            response = requests.get(url)
            response.raise_for_status()
            holidays = response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Gagal mengambil data libur: %s") % str(e))
            
        if not holidays:
            raise UserError(_("Tidak ada data libur yang ditemukan untuk periode yang dipilih."))
            
        calendar_leaves_obj = self.env['resource.calendar.leaves']
        created_count = 0
        skipped_count = 0
        
        if not self.include_cuti_bersama:
            holidays = [holiday for holiday in holidays if not holiday.get('is_cuti', False)]
            
        grouped_by_keterangan = defaultdict(list)
        
        for holiday in holidays:
            date_str = holiday['tanggal']
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
                date_parts = date_str.split('-')
                date_str = f"{date_parts[0]}-{int(date_parts[1]):02d}-{int(date_parts[2]):02d}"
            
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            keterangan = holiday['keterangan']
            
            grouped_by_keterangan[keterangan].append({
                'date': date_obj,
                'date_str': date_str,
                'is_cuti': holiday.get('is_cuti', False)
            })
            
        year = self.year
        first_day = datetime(year, 1, 1) if not self.month else datetime(year, int(self.month), 1)
        last_day = datetime(year, 12, 31, 23, 59, 59) if not self.month else datetime(
            year, int(self.month), 31, 23, 59, 59) if int(self.month) in [1,3,5,7,8,10,12] else datetime(
            year, int(self.month), 30, 23, 59, 59) if int(self.month) in [4,6,9,11] else datetime(
            year, int(self.month), 29, 23, 59, 59) if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else datetime(
            year, int(self.month), 28, 23, 59, 59)
            
        existing_holidays = calendar_leaves_obj.search([
            ('resource_id', '=', False),
            ('date_from', '>=', first_day),
            ('date_to', '<=', last_day),
        ])
        
        existing_holiday_names = {holiday.name for holiday in existing_holidays}
        
        for keterangan, holiday_dates in grouped_by_keterangan.items():
            if keterangan in existing_holiday_names:
                skipped_count += 1
                continue
                
            holiday_dates.sort(key=lambda x: x['date'])
            
            first_date = holiday_dates[0]['date']
            last_date = holiday_dates[-1]['date']
            
            calendar_leaves_obj.create({
                'name': keterangan,
                'date_from': first_date,
                'date_to': last_date,
                'resource_id': False,
                'calendar_id': False,
                'is_public_holiday': True,
                'holiday_source': 'Libur Nasional Indonesia'
            })
            created_count += 1
        
        if skipped_count > 0:
            message = _("%(created)s libur berhasil dibuat, %(skipped)s dilewati (sudah ada)") % {
                'created': created_count, 
                'skipped': skipped_count
            }
        else:
            message = _("%(created)s libur berhasil dibuat") % {'created': created_count}
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hasil Import Libur'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                    'followed_by': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }
        }
