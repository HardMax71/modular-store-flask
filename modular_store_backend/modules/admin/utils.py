# /modular_store_backend/modules/admin/utils.py
import csv
import json
from io import StringIO, BytesIO

from flask import send_file, current_app
from flask.typing import ResponseValue
from openpyxl import Workbook


def generate_csv(data: dict[str, list[dict[str, any]]]) -> ResponseValue:
    try:
        output = StringIO()
        for table, rows in data.items():
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                output.write('\n')
        output.seek(0)
        return send_file(
            BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name='data.csv'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating CSV: {e}")
        raise


def generate_excel(data: dict[str, list[dict[str, any]]]) -> ResponseValue:
    try:
        wb = Workbook()
        wb.remove(wb.active)  # type: ignore
        for table, rows in data.items():
            ws = wb.create_sheet(title=table)
            if rows:
                headers = list(rows[0].keys())
                ws.append(headers)
                for row in rows:
                    ws.append([row[header] for header in headers])
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='data.xlsx'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating Excel: {e}")
        raise


def generate_json(data: dict[str, list[dict[str, any]]]) -> ResponseValue:
    try:
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj: any) -> any:
                if isinstance(obj, bytes):
                    return obj.decode('utf-8')
                return super().default(obj)

        output = json.dumps(data, ensure_ascii=False, indent=2, cls=CustomEncoder)
        return send_file(
            BytesIO(output.encode('utf-8')),
            mimetype='application/json; charset=utf-8',
            as_attachment=True,
            download_name='data.json'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating JSON: {e}")
        raise
